# An interceptor is an object called during the "init" command.
#
# Interceptors are passed the initialized WorkDB, and they are able to do
# things like mark certain mutations as skipped (i.e. so that they are never
# performed).
from parso.tree import Node

from cosmic_ray.utils.config import Config, root_config, Entry
from cosmic_ray.interceptors.interceptor import Interceptor
from cosmic_ray.operators.operator import Operator
from cosmic_ray.utils.plugins import get_interceptors
from cosmic_ray.utils.util import dict_filter, LazyDict
from cosmic_ray.db.work_db import WorkDB
from cosmic_ray.db.work_item import WorkItem


interceptors_config = Config(
    root_config,
    'interceptors',
    valid_entries={
        'load': Entry(default=['.*'], choices=lambda : interceptors.keys()),
    },
)


class Interceptors(LazyDict):

    def _load(self):
        available_interceptors = dict(get_interceptors())
        load_patterns = interceptors_config['load']
        d = dict_filter(available_interceptors, load_patterns)
        return {name: c() for name, c in d.items()}

    def pre_scan_module_path(self, module_path):
        for interceptor in self.values():  # type: Interceptor
            if not interceptor.pre_scan_module_path(module_path):
                return False
        return True

    def post_scan_module_path(self, module_path):
        for interceptor in self.values():    # type: Interceptor
            interceptor.post_scan_module_path(module_path)

    def new_mutation(self,
                     operator: Operator,
                     node: Node):
        for interceptor in self.values():  # type: Interceptor
            if not interceptor.new_mutation(operator, node):
                return False
        return True

    def new_work_item(self,
                      work_db: WorkDB,
                      operator: Operator,
                      node: Node,
                      work_item: WorkItem):
        for interceptor in self.values():  # type: Interceptor
            if not interceptor.new_work_item(work_db, operator, node, work_item):
                return False
        return True


interceptors = Interceptors()
