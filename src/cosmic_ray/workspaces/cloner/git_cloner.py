from logging import getLogger

import git

from cosmic_ray.workspaces.cloner import Cloner


log = getLogger(__name__)


class GitCloner(Cloner):
    def __init__(self):
        from cosmic_ray.execution_engines.local_execution_engine import \
            execution_engines_cloning_config
        self.repo_uri = execution_engines_cloning_config['repo-uri']

    def clone(self, dest_path):
        log.info('Cloning git repo %s to %s', self.repo_uri, dest_path)
        git.Repo.clone_from(self.repo_uri, dest_path, depth=1)
