import os
import re
from logging import getLogger
from pathlib import Path
import shutil
import subprocess
import tempfile
import git

from cosmic_ray.execution_engines.local_execution_engine import \
    execution_engines_local_cloning_config
from cosmic_ray.workspaces.workspace import Workspace

log = getLogger(__name__)


class ClonedWorkspace(Workspace):
    """Clone a project into a temporary directory.
    """

    def __init__(self):
        self._tempdir = tempfile.TemporaryDirectory()
        self._prepare_directory()
        self._load_environment()
        self._run_commands(execution_engines_local_cloning_config['commands'])

    def _prepare_directory(self):
        log.info('New project clone in %s', self._tempdir.name)
        self._clone_dir = str(Path(self._tempdir.name) / 'repo')

        method = execution_engines_local_cloning_config['method']
        if method == 'git':
            self._clone_with_git(execution_engines_local_cloning_config['repo-uri'], self._clone_dir)

        elif method == 'copy':
            ignore_files = execution_engines_local_cloning_config['ignore-files']
            self._clone_with_copy(os.getcwd(), self._clone_dir, ignore_files)

        else:
            raise Exception("Clone method '%s' unknown" % method)

    def _load_environment(self):
        os.environ['PYTHONPATH'] = '%s:%s' % (self.clone_dir, os.environ.get('PYTHONPATH', ''))

    @property
    def clone_dir(self):
        "The root of the cloned project."
        return self._clone_dir

    def cleanup(self):
        "Remove the directory containin the clone and virtual environment."
        log.info('Removing temp dir %s', self._tempdir.name)
        self._tempdir.cleanup()

    def _run_commands(self, commands):
        """Run a set of commands in the workspace's virtual environment.

        Args:
            commands: An iterable of strings each representing a command to be executed.
        """
        for command in commands:
            log.info('Running installation command: %s', command)
            try:
                r = subprocess.run(command,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT,
                                   shell=True,
                                   cwd=str(self._clone_dir),
                                   check=True)

                log.debug('Command results: %s', r.stdout)
            except subprocess.CalledProcessError as exc:
                log.error("Error running command in virtual environment\n"
                          "command: %s\n"
                          "error: %s",
                          command, exc.output)

    @staticmethod
    def _clone_with_git(repo_uri, dest_path):
        """Create a clone by cloning a git repository.

        Args:
            repo_uri: The URI of the git repository to clone.
            dest_path: The location to clone to.
        """
        log.info('Cloning git repo %s to %s', repo_uri, dest_path)
        git.Repo.clone_from(repo_uri, dest_path, depth=1)

    @staticmethod
    def _clone_with_copy(src_path, dest_path, ignore_files=None):
        """Clone a directory try by copying it.

        Args:
            src_path: The directory to be copied.
            dest_path: The location to copy the directory to.
        """
        log.info('Cloning directory tree %s to %s', src_path, dest_path)

        if ignore_files:
            s = '|'.join('(?:%s)' % f for f in ignore_files)
            re_ignore_files = re.compile(s)
            ignore = lambda src, names: set(name for name in names if re_ignore_files.match(name))
        else:
            ignore = None

        shutil.copytree(src_path, dest_path, ignore=ignore)
