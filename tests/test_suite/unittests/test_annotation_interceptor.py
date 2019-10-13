import asyncio
from typing import Dict

import parso
import sys

from cosmic_ray.commands.run import Run
from cosmic_ray.interceptors import Interceptors
from cosmic_ray.interceptors.annotation_interceptor import \
    AnnotationInterceptor
from cosmic_ray.operators.boolean_replacer import ReplaceOrWithAnd
from cosmic_ray.operators.string_replacer import StringReplacer
from cosmic_ray.db.work_item import WorkResult, WorkItem, WorkerOutcome


class Data:
    def __init__(self):
        self.results = {}  # type: Dict[str, WorkResult]
        self.work_items = {}  # type: Dict[str, WorkItem]

    def add_work_item(self, work_item: WorkItem):
        self.work_items[work_item.job_id] = work_item

    def set_result(self, job_id, work_result: WorkResult):
        self.results[job_id] = work_result

    @property
    def merged_results(self):
        results = ((w, self.results.get(job_id))
                   for job_id, w in self.work_items.items())

        return {
            (w.operator_name, w.occurrence):
                (w.start_pos, w.end_pos,
                 (r.outcome, r.worker_outcome) if r else (None, None))
            for w, r in results  # type: WorkItem, WorkResult
        }

    operators = [ReplaceOrWithAnd(), StringReplacer()]

    if sys.version_info < (3, 6):
        content = """
        a = 1 or 2
        def f(a: int or float) -> str or float:
            return a or True
        def f(a):
            a or False
        """

        expected = {
            ('core/ReplaceOrWithAnd', 0): ((2, 14), (2, 16), (None, None)),
            ('core/ReplaceOrWithAnd', 1): ((3, 21), (3, 23), (None, WorkerOutcome.SKIPPED)),
            ('core/ReplaceOrWithAnd', 2): ((3, 38), (3, 40), (None, WorkerOutcome.SKIPPED)),
            ('core/ReplaceOrWithAnd', 3): ((4, 21), (4, 23), (None, None)),
            ('core/ReplaceOrWithAnd', 4): ((6, 14), (6, 16), (None, None)),
        }

    else:
        content = """
        a: int or str = 1 or 2
        a = 1 or 2
        b: " annotation " = 2
        def f(a: int or float) -> str or float:
            return a or True
        def f(a):
            a or False
        """

        expected = {
            ('ReplaceOrWithAnd', 0): ((2, 26), (2, 28), (None, None)),
            ('ReplaceOrWithAnd', 1): ((3, 14), (3, 16), (None, None)),
            ('ReplaceOrWithAnd', 2): ((6, 21), (6, 23), (None, None)),
            ('ReplaceOrWithAnd', 3): ((8, 14), (8, 16), (None, None)),
        }


def test_interceptor(dummy_execution_engine):
    data = Data()

    run = Run(data)

    run.interceptors = Interceptors([AnnotationInterceptor()])
    run.operators = data.operators
    run.execution_engine = dummy_execution_engine

    asyncio.get_event_loop().run_until_complete(
        run.visit_module(
            module_path='a.py',
            module_ast=parso.parse(data.content),
        )
    )

    assert data.merged_results == data.expected
