from cosmic_ray.execution_engines.remote_environment import RemoteEnvironment
from cosmic_ray.workspaces.cloner.tar_cloner import TarCloner
from cosmic_ray.workspaces.workspace import Workspace


class SshRemoteEnvironment(RemoteEnvironment):
    def __init__(self, config, prepared_data, workspace_class_name):
        self.workspace_class_name = workspace_class_name
        super().__init__(config, prepared_data)

    def _build_workspace(self, cloner) -> Workspace:
        import importlib
        module = importlib.import_module(self.workspace_class_name[0])
        workspace_class = getattr(module, self.workspace_class_name[1])
        return workspace_class(cloner)

    @classmethod
    def _get_cloner_class(cls):
        return TarCloner
