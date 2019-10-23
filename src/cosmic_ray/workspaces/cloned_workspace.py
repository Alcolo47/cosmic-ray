import os
from logging import getLogger
from pathlib import Path
import subprocess
import tempfile

from cosmic_ray.execution_engines.local_execution_engine import \
    execution_engines_cloning_config
from cosmic_ray.workspaces.workspace import Workspace

log = getLogger(__name__)


class ClonedWorkspace(Workspace):
    """Clone a project into a temporary directory.
    """

    def __init__(self, cloner):
        super(ClonedWorkspace, self).__init__(cloner)
        self._tempdir = tempfile.TemporaryDirectory()
        log.debug('tempdir: %s', self._tempdir)
        self._prepare_directory()
        self._load_environment()
        self._run_commands()

    def _prepare_directory(self):
        log.info('New project clone in %s', self._tempdir.name)
        self._clone_dir = str(Path(self._tempdir.name) / 'repo')
        self.cloner.clone(self._clone_dir)
        self.cloner = None

    def _load_environment(self):
        os.environ['PYTHONPATH'] = '%s:%s' % (self.clone_dir, os.environ.get('PYTHONPATH', ''))

    @property
    def clone_dir(self):
        """The root of the cloned project.
        """
        return self._clone_dir

    # def cleanup(self):
    #     """Remove the directory containin the clone and virtual environment.
    #     """
    #     log.info('Removing temp dir %s', self._tempdir.name)
    #     self._tempdir.cleanup()

    def _run_commands(self):
        """Run a set of commands in the workspace's virtual environment.
        """
        commands = execution_engines_cloning_config['commands']
        for command in commands:
            log.info('Running installation command: %s', command)
            try:
                r = subprocess.run(command,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT,
                                   cwd=str(self._clone_dir),
                                   check=True,
                                   shell=True)

                log.debug('Command results: %s', r.stdout)

            except subprocess.CalledProcessError as exc:
                log.error("Error running command\n"
                          "command: %s\n"
                          "error: %s",
                          command, exc.output)
