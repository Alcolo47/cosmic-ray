import re
import shutil
from logging import getLogger

from cosmic_ray.execution_engines.cloner import Cloner

log = getLogger(__name__)


class CopyCloner(Cloner):

    def __init__(self):
        from cosmic_ray.execution_engines.remote_environment import \
            execution_engine_cloning_config
        self.src_path = execution_engine_cloning_config['src-dir']
        ignore_files = execution_engine_cloning_config['ignore-files']
        self.ignore_files = ignore_files

    def clone(self, dest_path):
        """Clone a directory try by copying it.

        Args:
            dest_path: The location to copy the directory to.
        """
        log.debug('Cloning directory tree %s to %s', self.src_path, dest_path)

        if self.ignore_files:
            s = '|'.join('(?:%s)' % f for f in self.ignore_files)
            re_ignore_files = re.compile(s)
            ignore = lambda src, names: set(name for name in names if re_ignore_files.match(name))
        else:
            ignore = None

        shutil.copytree(self.src_path, dest_path, ignore=ignore)
