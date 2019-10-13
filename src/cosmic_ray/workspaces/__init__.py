from cosmic_ray.utils.config import Config, Entry
from cosmic_ray.execution_engines import execution_engine_config
from cosmic_ray.utils.plugins import get_execution_workspace
from cosmic_ray.utils.util import LazyDict


execution_engines_workspace_config = Config(
    execution_engine_config,
    'workspace',
    valid_entries={
        'type': Entry(default='cloned_with_virtualenv', choices=('cloned', 'cloned_with_virtualenv')),
    },
)


class Workspaces(LazyDict):

    def _load(self):
        return dict(get_execution_workspace())

    def __getitem__(self, item):
        return super().__getitem__(item)()


workspaces = Workspaces()
