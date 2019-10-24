from cosmic_ray.utils.util import LazyDict
from cosmic_ray.execution_engines.execution_engine import ExecutionEngine


class ExecutionEngines(LazyDict):

    def _load(self):
        from cosmic_ray.utils.plugins import get_execution_engines
        return dict(get_execution_engines())

    def __getitem__(self, item):
        """
        :param item:
        :return: ExecutionEngine
        """
        return super().__getitem__(item)()


execution_engines = ExecutionEngines()
