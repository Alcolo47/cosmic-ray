"""This is the body of the low-level worker tool.
"""
import glob
import os
import sys
import asyncio
import traceback
from contextlib import contextmanager
from subprocess import check_call, Popen, PIPE, STDOUT
from typing import Dict, Tuple
from typing import Union

from cosmic_ray.execution_engines import execution_engine_config
from cosmic_ray.execution_engines.execution_engine import ExecutionData
from cosmic_ray.db.work_item import Outcome, WorkerOutcome, WorkResult
from cosmic_ray.utils.config import Config, Entry

execution_engine_worker_config = Config(
    execution_engine_config,
    'worker',
    valid_entries= {
        'test-command': Entry(required=True),
        'timeout': 10,
        'custom_commands_if_change_in': {
            '*/models.py': {
                'before': 'rm -f */migrations/[0-9]* && manage.py makemigrations',
                'after': 'git checkout -f */migrations/*',
            },
        },
    },
)


class CustomCommandError(Exception):
    def __init__(self, cmd, outputs):
        self.cmd = cmd
        self.outputs = outputs


class Worker:

    def __init__(self):
        self.test_command = execution_engine_worker_config['test-command']
        self.timeout = execution_engine_worker_config['timeout']

        self._files_with_custom_commands = {
            filename: (data['before'], data['after'])
            for gl, data in execution_engine_worker_config['custom_commands_if_change_in'].items()
            for filename in glob.iglob(gl, recursive=True)
        }  # type: Dict[str, Tuple[str]]

    # pylint: disable=R0913
    def worker(self, data: Union[ExecutionData, None]):
        """Mutate the OCCURRENCE-th site for OPERATOR_NAME in MODULE_PATH, run the
        tests, and report the results.

        This is fundamentally the single-mutation-and-test-run process
        implementation.

        There are three high-level ways that a worker can finish. First, it could
        fail exceptionally, meaning that some uncaught exception made its way from
        some part of the operation to terminate the function. This function will
        intercept all exceptions and return it in a non-exceptional structure.

        Second, the mutation testing machinery may determine that there is no
        OCCURRENCE-th instance for OPERATOR_NAME in the module under test. In this
        case there is no way to report a test result (i.e. killed, survived, or
        incompetent) so a special value is returned indicating that no mutation is
        possible.

        Finally, and hopefully normally, the worker will find that it can run a
        test. It will do so and report back the result - killed, survived, or
        incompetent - in a structured way.

        Returns: A WorkResult

        Raises: This will generally not raise any exceptions. Rather, exceptions
            will be reported using the 'exception' result-type in the return value.

        """
        try:
            with self.use_mutation(data):
                outcome, output = self._run_tests(data)
                return WorkResult(output=output,
                                  outcome=outcome,
                                  worker_outcome=WorkerOutcome.NORMAL)

        except CustomCommandError as ex:
            return WorkResult(output=ex.outputs,
                              outcome=Outcome.KILLED,
                              worker_outcome=WorkerOutcome.NORMAL)

        except Exception as ex:  # noqaq # pylint: disable=broad-except
            return WorkResult(output=traceback.format_exc(),
                              outcome=Outcome.INCOMPETENT,
                              worker_outcome=WorkerOutcome.EXCEPTION)

    @contextmanager
    def use_mutation(self, data: Union[ExecutionData, None]):
        """A context manager that applies a mutation for the duration of a with-block.

        This applies a mutation to a file on disk, and after the with-block it put the unmutated code
        back in place.

        Yields: A `(unmutated-code, mutated-code)` tuple to the with-block. If there was
            no mutation performed, the `mutated-code` is `None`.
        """
        if data is None:
            yield
            return

        filename = str(data.filename)
        tmp_filename = filename + '.TMP'
        os.replace(filename, tmp_filename)

        try:
            with data.filename.open(mode='wt', encoding='utf-8') as handle:
                handle.write(data.new_code)
            yield

        finally:
            os.replace(tmp_filename, filename)
            basename = os.path.basename(filename)
            basename = os.path.splitext(basename)[0]
            pyc = os.path.join(
                os.path.dirname(filename), '__pycache__', basename + '.*.pyc'
            )
            for n in glob.iglob(pyc):
                os.unlink(n)


    @contextmanager
    def custom_commands(self, data: Union[ExecutionData, None]):
        commands = data and self._files_with_custom_commands.get(str(data.filename))
        if commands:
            try:
                cmd = commands[0]
                p = Popen(cmd, shell=isinstance(cmd, str), stdout= PIPE, stderr=STDOUT)
                outputs = p.stdout.read()
                if p.wait() != 0:
                    raise CustomCommandError(cmd, outputs.decode('utf-8'))

                yield

            finally:
                cmd = commands[1]
                check_call(cmd, shell=isinstance(cmd, str))

        else:
            yield

    async def _async_run_tests(self):
        # We want to avoid writing pyc files in case our changes happen too fast for Python to
        # notice them. If the timestamps between two changes are too small, Python won't recompile
        # the source.
        try:
            if isinstance(self.test_command, str):
                proc = await asyncio.create_subprocess_shell(
                    self.test_command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                )
            else:
                proc = await asyncio.create_subprocess_exec(
                    *self.test_command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                )

        except Exception:  # pylint: disable=W0703
            return Outcome.INCOMPETENT, traceback.format_exc()

        try:
            outs, errs = await asyncio.wait_for(proc.communicate(), self.timeout)

            assert proc.returncode is not None

            if proc.returncode == 0:
                return Outcome.SURVIVED, outs.decode('utf-8')
            else:
                return Outcome.KILLED, outs.decode('utf-8')

        except asyncio.TimeoutError:
            proc.terminate()
            return Outcome.KILLED, 'timeout'

        except Exception:  # pylint: disable=W0703
            proc.terminate()
            return Outcome.INCOMPETENT, traceback.format_exc()

        finally:
            await proc.wait()

    def _run_tests(self, data: Union[ExecutionData, None]):
        """Run test command in a subprocess.

        If the command exits with status 0, then we assume that all tests passed. If
        it exits with any other code, we assume a test failed. If the call to launch
        the subprocess throws an exception, we consider the test 'incompetent'.

        Tests which time out are considered 'killed' as well.

        Return: A tuple `(TestOutcome, output)` where the `output` is a string
            containing the output of the command.
        """

        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

        with self.custom_commands(data):
            result = asyncio.get_event_loop().run_until_complete(
                self._async_run_tests()
            )
        return result
