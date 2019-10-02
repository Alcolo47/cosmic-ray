# An interceptor is an object called during the "init" command.
#
# Interceptors are passed the initialized WorkDB, and they are able to do
# things like mark certain mutations as skipped (i.e. so that they are never
# performed).
import re
from typing import List

from parso.tree import Node

from cosmic_ray.interceptors.base import Interceptor
from cosmic_ray.operators.operator import Operator
from cosmic_ray.work_item import WorkItem


class Interceptors(list):
    def __init__(self, interceptors: List[Interceptor], config):
        super().__init__(interceptors)

        re_camel_to_kebab = re.compile(r'([0-9a-z])([A-Z])')
        for interceptor in self:
            name = type(interceptor).__name__
            if name.endswith('Interceptor'):
                name = name[:-len('Interceptor')]

            name = re_camel_to_kebab.sub(r'\1-\2', name).lower()
            interceptor_config = config.get(name, {})
            interceptor.config = interceptor_config

    def pre_scan_module_path(self, module_path):
        for interceptor in self:
            r = interceptor.pre_scan_module_path(module_path)
            if not r:
                return False
        return True

    def post_scan_module_path(self, module_path):
        for interceptor in self:
            interceptor.post_scan_module_path(module_path)

    def pre_add_work_item(self,
                          operator: Operator,
                          node: Node,
                          new_work_item: WorkItem):
        for interceptor in self:
            r = interceptor.pre_add_work_item(operator, node, new_work_item)
            if r is False:
                return False
        return True

    def post_add_work_item(self,
                           operator: Operator,
                           node: Node,
                           new_work_item: WorkItem):
        for interceptor in self:
            interceptor.post_add_work_item(operator, node, new_work_item)

    def post_init(self):
        for interceptor in self:
            interceptor.post_init()
