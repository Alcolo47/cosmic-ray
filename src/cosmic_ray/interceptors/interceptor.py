from parso.tree import Node

from cosmic_ray.operators.operator import Operator
from cosmic_ray.db.work_db import WorkDB
from cosmic_ray.db.work_item import WorkItem, WorkerOutcome, WorkResult


class Interceptor:
    """
    Base class for all interceptors.

    """
    def pre_scan_module_path(self, module_path) -> bool:
        """Called when we start exploring a new file.
        Can be useful to handle some caches.
        :return True to allow this file exploration.
        """
        return True

    def post_scan_module_path(self, module_path):
        """Called when we end exploring a file.
        """
        pass

    def new_mutation(self,
                     operator: Operator,
                     node: Node):
        return True

    def new_work_item(self,
                      work_db: WorkDB,
                      operator: Operator,
                      node: Node,
                      work_item: WorkItem):
        """Called when a work_item id inserted in db.
        Here, you can add a skipped result for this work item.
        """
        return True

    @staticmethod
    def _add_work_result(work_db: WorkDB, work_item: WorkItem,
                         output, worker_outcome: WorkerOutcome):
        work_db.set_result(
            work_item.job_id,
            WorkResult(output=output, worker_outcome=worker_outcome),
        )
