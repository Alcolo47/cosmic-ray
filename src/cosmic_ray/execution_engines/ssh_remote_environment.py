from cosmic_ray.execution_engines.remote_environment import RemoteEnvironment
from cosmic_ray.execution_engines.cloner.tar_cloner import TarCloner


class SshRemoteEnvironment(RemoteEnvironment):
    @classmethod
    def _get_cloner_class(cls):
        return TarCloner
