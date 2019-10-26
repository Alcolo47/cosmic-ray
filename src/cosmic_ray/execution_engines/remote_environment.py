import os
import signal
import subprocess
import tempfile
from _signal import SIG_DFL
from logging import getLogger
from subprocess import run
from typing import Union, Tuple, Type

from cosmic_ray.db.work_item import WorkResult
from cosmic_ray.execution_engines.execution_engine import ExecutionData, \
    execution_engine_config
from cosmic_ray.execution_engines.worker import Worker
from cosmic_ray.execution_engines.cloner import Cloner
from cosmic_ray.execution_engines.cloner.copy_cloner import CopyCloner
from cosmic_ray.execution_engines.cloner.git_cloner import GitCloner
from cosmic_ray.utils.config import Config, Entry

log = getLogger(__name__)


execution_engine_cloning_config = Config(
    execution_engine_config,
    'cloning',
    valid_entries={
        'src-dir': os.getcwd(),
        'method': Entry(default='copy', choices=('copy', 'git')),
        'init-commands': Entry(required=True),
        'repo-uri': None,
        'ignore-files': [],
        'python-load': None,
    },
)


class RemoteEnvironment:
    _instance = None  # type: RemoteEnvironment

    def __init__(self, config, prepared_data):
        type(self)._instance = self

        signal.signal(signal.SIGINT, SIG_DFL)

        execution_engine_config.set_config(config)

        self._tempdir = tempfile.TemporaryDirectory()
        self.clone_dir = os.path.join(self._tempdir.name, 'repo')
        log.debug('New project clone in %s', self._tempdir.name)

        log.debug('Initialize remote environment')
        cloner = self._get_cloner_class()()
        cloner.load_prepared_data(prepared_data)
        cloner.clone(self.clone_dir)

        os.environ['PYTHONPATH'] = '%s:%s' % (self.clone_dir, os.environ.get('PYTHONPATH', ''))

        self._run_initialisation_commands()

        python_load = execution_engine_cloning_config['python-load']
        if python_load:
            python_load = os.path.join(self.clone_dir, python_load)
            exec(open(python_load).read(), {'__file__': python_load})

        self._worker = Worker(self.clone_dir)

    def __del__(self):
        self.cleanup()

    @classmethod
    def cleanup(cls):
        if cls._instance:
            try:
                cls._instance._tempdir.cleanup()
            except OSError:
                # Ignore all rmdir problems ...
                pass

    @classmethod
    def prepare_local_side(cls):
        return cls._get_cloner_class().prepare_local_side()

    @classmethod
    def _get_cloner_class(cls) -> Type[Cloner]:

        method = execution_engine_cloning_config['method']
        if method == 'copy':
            return CopyCloner
        if method == 'git':
            return GitCloner
        raise Exception("Clone method '%s' unknown" % method)

    @classmethod
    def execute(cls, data: Union[ExecutionData, None]):
        return cls._instance._execute(data)

    def _execute(self, data: Union[ExecutionData, None]) -> Tuple[str, WorkResult]:
        log.debug('execute_work_item (%s): %s', os.getpid(), data)
        result = self._worker.worker(data)
        return (data and data.job_id), result

    def _run_initialisation_commands(self):
        """Run a set of commands in the workspace's virtual environment.
        """
        commands = execution_engine_cloning_config['init-commands']
        for command in commands:
            try:
                log.debug('Running installation command: %s', command)
                r = run(command, shell=isinstance(command, str),
                        cwd=self.clone_dir,
                        encoding='utf-8',
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        check=True)

                log.debug('Command results: %s', r.stdout)

            except subprocess.CalledProcessError as ex:
                log.exception("Error running command: %s\n%s", command, ex.stdout)
                raise
