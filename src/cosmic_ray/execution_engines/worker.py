"""This is the body of the low-level worker tool.
"""
import glob
import logging
import os
import sys
import asyncio
import traceback
from contextlib import contextmanager
from subprocess import run, CalledProcessError
from typing import Dict, Tuple, List
from typing import Union

from cosmic_ray.execution_engines.execution_engine import ExecutionData, \
    execution_engine_config
from cosmic_ray.db.work_item import Outcome, WorkerOutcome, WorkResult
from cosmic_ray.utils.config import Config, Entry
from cosmic_ray.utils.util import excursion


log = logging.getLogger(__name__)

execution_engine_worker_config = Config(
    execution_engine_config,
    'worker',
    valid_entries= {
        'test-command': Entry(required=True),
        'envs': {},
        'timeout': 10,
        'custom-commands-if-change-in': {
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

    def __init__(self, work_dir):
        self._work_dir = work_dir
        self._test_command = execution_engine_worker_config['test-command']
        self._envs = execution_engine_worker_config['envs']
        self._timeout = execution_engine_worker_config['timeout']

        with excursion(work_dir):
            self._files_with_custom_commands = {
                filename: (data['before'], data['after'])
                for gl, data in execution_engine_worker_config['custom-commands-if-change-in'].items()
                for filename in glob.iglob(gl, recursive=True)
            }  # type: Dict[str, Tuple[Union[str, List[str]]]]

        self._envs = {
            **os.environ,
            **self._envs,
        }

        self._hz = os.sysconf(os.sysconf_names['SC_CLK_TCK'])

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
        with excursion(self._work_dir):
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

        filename = data.filename
        tmp_filename = filename + '.TMP'
        os.replace(filename, tmp_filename)

        try:
            with open(filename, 'wt', encoding='utf-8') as handle:
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
        commands = data and self._files_with_custom_commands.get(data.filename)
        if commands:
            try:
                self._run_cmd(commands[0], data.filename)
                yield

            except CalledProcessError as ex:
                raise CustomCommandError(commands[0], ex.stdout) from ex

            finally:
                self._run_cmd(commands[1], data.filename)
        else:
            yield

    @staticmethod
    def _run_cmd(cmd: Union[str, List[str]], filename):
        if isinstance(cmd, str):
            log.debug("Running %s  (for file %s)", cmd, filename)
            shell = True
        else:
            cmd = cmd + [filename]
            if log.isEnabledFor(logging.DEBUG):
                log.debug("Running %s", ' ' .join(cmd))
            shell = False

        return run(cmd, shell=shell, check=True, capture_output=True)

    async def _async_run_tests(self):
        # We want to avoid writing pyc files in case our changes happen too fast for Python to
        # notice them. If the timestamps between two changes are too small, Python won't recompile
        # the source.
        proc = None
        try:
            if isinstance(self._test_command, str):
                proc = await asyncio.create_subprocess_shell(
                    self._test_command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                    env=self._envs,
                )
            else:
                proc = await asyncio.create_subprocess_exec(
                    *self._test_command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                    env=self._envs,
                )

        except Exception:  # pylint: disable=W0703
            return Outcome.INCOMPETENT, traceback.format_exc()

        else:
            timeout = self._timeout
            waited = 0
            soft_kill = None
            while True:
                try:
                    outs, errs = await asyncio.wait_for(proc.communicate(), timeout)

                    assert proc.returncode is not None

                    if soft_kill is False:
                        return Outcome.KILLED, 'timeout: kill -9'

                    elif soft_kill is True:
                        return Outcome.KILLED, 'timeout'

                    elif proc.returncode == 0:
                        return Outcome.SURVIVED, outs.decode('utf-8')

                    else:
                        return Outcome.KILLED, outs.decode('utf-8')

                except asyncio.TimeoutError:
                    waited += timeout
                    cutime = self._get_cutime(proc.pid)
                    # timeout in user-time, but if process is locked, wait for 3 * timeout in real time
                    if soft_kill is None and cutime < self._timeout and waited < 3 * timeout:
                        # Wait again
                        if waited > 0:
                            # Recompute timeout
                            timeout = (self._timeout * waited / cutime) - waited
                            # Add 10% of extra time to avoid asymptotic convergence
                            timeout *= 1.1

                    else:
                        if soft_kill is None:
                            proc.terminate()
                            # Wait 2s user-time more (or 2*3 s in real-time)
                            timeout = 2
                            soft_kill = True
                        else:
                            proc.send_signal(9)
                            soft_kill = False

                except Exception:  # pylint: disable=W0703
                    proc.terminate()
                    return Outcome.INCOMPETENT, traceback.format_exc()

        finally:
            if proc:
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
            result = asyncio.get_event_loop().run_until_complete(self._async_run_tests())
        return result

    def _get_cutime(self, pid):
        with open("/proc/%d/stat" % pid) as f:
            # [13:17] == utime, stime, cutime, cstime
            val = f.read().split(' ')[15]
            cutime = (float(val) / self._hz)
            return cutime
