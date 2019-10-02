from typing import Dict

import parso

from cosmic_ray.commands.init import visit_module
from cosmic_ray.config import ConfigDict
from cosmic_ray.interceptors import Interceptors
from cosmic_ray.interceptors.pragma_interceptor import get_pragma_list, \
    PragmaInterceptor
from cosmic_ray.work_item import WorkResult, WorkItem, WorkerOutcome


def test_pragma():
    r = get_pragma_list("# comment")
    assert r is None
    r = get_pragma_list("# comment pragma:")
    assert r == {}
    r = get_pragma_list("# comment pragma: x y  z")
    assert r == {'x y': None, 'z': None}
    r = get_pragma_list("# comment pragma: x:")
    assert r == {'x': []}
    r = get_pragma_list("# comment pragma: x:  y")
    assert r == {'x': [], 'y': None}
    r = get_pragma_list("# comment pragma: x y  z: d, e")
    assert r == {'x y': None, 'z': ['d', 'e']}
    r = get_pragma_list("# comment pragma: x: a, b, c  y z: d, e")
    assert r == {'x': ['a', 'b', 'c'], 'y z': ['d', 'e']}
    r = get_pragma_list("comment pragma: x: a, b, c y  z: d, e")
    assert r == {'x': ['a', 'b', 'c y'], 'z': ['d', 'e']}


class Data:
    def __init__(self):
        self.results: Dict[str, WorkResult] = {}
        self.work_items: Dict[str, WorkItem] = {}

    def add_work_item(self, work_item: WorkItem):
        self.work_items[work_item.job_id] = work_item

    def set_result(self, job_id, work_result: WorkResult):
        self.results[job_id] = work_result

    operator_names = [
        'core/ReplaceTrueWithFalse',
        'core/ReplaceFalseWithTrue',
        'core/RemoveDecorator',
    ]

    content = """
a = True  # pragma: no mutate
b1, b2 = True, False  # pragma: no mutate: replace-true-with-false, replace-false-with-true, other
c = True  # pragma: no mutate: other      

@decorator  # pragma: no mutate: decorator
d = 0  

    """

    @property
    def merged_results(self):
        results = ((r, self.work_items[job_id])
                   for job_id, r in self.results.items())
        return {
            (w.start_pos, w.end_pos, w.occurrence):
                (w.operator_name, r.worker_outcome)
            for r, w in results
        }


    expected = {
        # skip a
        ((2, 4), (2, 8), 0): ('core/ReplaceTrueWithFalse', WorkerOutcome.SKIPPED),
        # skip b1
        ((3, 9), (3, 13), 1): ('core/ReplaceTrueWithFalse', WorkerOutcome.SKIPPED),
        # skip b2
        ((3, 15), (3, 20), 0): ('core/ReplaceFalseWithTrue', WorkerOutcome.SKIPPED),
        # skip @decorator
        ((6, 0), (7, 0), 0): ('core/RemoveDecorator', WorkerOutcome.SKIPPED),
    }


def test_interceptor():
    data = Data()
    interceptor = PragmaInterceptor(data)

    visit_module(
        module_path="a.py",
        module_ast=parso.parse(data.content),
        work_db=data,
        interceptors=Interceptors([interceptor]),
        operator_names=data.operator_names,
        config=ConfigDict(),
    )

    assert data.merged_results == data.expected
