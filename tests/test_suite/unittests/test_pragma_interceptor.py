import asyncio
from typing import Dict

import parso

from cosmic_ray.commands.run import Run
from cosmic_ray.interceptors import Interceptors
from cosmic_ray.interceptors.pragma_interceptor import get_pragma_list, \
    PragmaInterceptor, pragma_interceptor_config
from cosmic_ray.operators.replace_boolean_operators import ReplaceBooleanOperatorTrueWithFalse, \
    ReplaceBooleanOperatorFalseWithTrue
from cosmic_ray.operators.remove_decorator_operator import RemoveDecoratorOperator
from cosmic_ray.operators.remove_named_argument_operator import RemoveNamedArgumentOperator
from cosmic_ray.db.work_item import WorkResult, WorkItem, WorkerOutcome


def test_pragma():
    r = get_pragma_list("# comment")
    assert r is None
    r = get_pragma_list("# comment pragma:")
    assert r == {}
    r = get_pragma_list("# comment pragma: x y  z")
    assert r == {'x y': True, 'z': True}
    r = get_pragma_list("# comment pragma: x:")
    assert r == {'x': []}
    r = get_pragma_list("# comment pragma: x:  y")
    assert r == {'x': [], 'y': True}
    r = get_pragma_list("# comment pragma: x y  z: d, e")
    assert r == {'x y': True, 'z': ['d', 'e']}
    r = get_pragma_list("# comment pragma: x: a, b, c  y z: d, e")
    assert r == {'x': ['a', 'b', 'c'], 'y z': ['d', 'e']}
    r = get_pragma_list("comment pragma: x: a, b, c y  z: d, e")
    assert r == {'x': ['a', 'b', 'c y'], 'z': ['d', 'e']}


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
        results = ((r, self.work_items[job_id])
                   for job_id, r in self.results.items())
        return {
            (w.start_pos, w.end_pos, w.occurrence):
                (w.operator_name, r.worker_outcome)
            for r, w in results
        }

    config = {'filter-no-coverage': True}

    operator_names = [
        ReplaceBooleanOperatorTrueWithFalse(),
        ReplaceBooleanOperatorFalseWithTrue(),
        RemoveDecoratorOperator(),
        RemoveNamedArgumentOperator(),
    ]

    content = """
a = True  # pragma: no mutate
b1, b2 = True, False  # pragma: no mutate: replace-boolean-true-with-false, replace-boolean-false-with-true, other
c = True  # pragma: no mutate: other      

@decorator  # pragma: no mutate: decorator
d = 0  
e = True  # pragma: no coverage

f = f(a=1,
      b=2,  # pragma: no mutate: named-argument
      c=3) 
    """

    expected = {
        # skip a
        ((2, 4), (2, 8), 0): ('ReplaceBooleanOperatorTrueWithFalse', WorkerOutcome.SKIPPED),
        # skip b1
        ((3, 9), (3, 13), 1): ('ReplaceBooleanOperatorTrueWithFalse', WorkerOutcome.SKIPPED),
        # skip b2
        ((3, 15), (3, 20), 0): ('ReplaceBooleanOperatorFalseWithTrue', WorkerOutcome.SKIPPED),
        # skip @decorator
        ((6, 0), (7, 0), 0): ('RemoveDecoratorOperator', WorkerOutcome.SKIPPED),
        # skip pragma no coverage
        ((8, 4), (8, 8), 3): ('ReplaceBooleanOperatorTrueWithFalse', WorkerOutcome.SKIPPED),
        # skip named-argument using target_node
        ((11, 6), (11, 9), 1): ('RemoveNamedArgumentOperator', WorkerOutcome.SKIPPED),
    }


def test_interceptor(dummy_execution_engine):
    data = Data()

    pragma_interceptor_config.set_config(data.config)

    run = Run(data)
    run.operators = data.operator_names
    run.interceptors = Interceptors([PragmaInterceptor()])
    run.execution_engine = dummy_execution_engine

    asyncio.get_event_loop().run_until_complete(
        run.visit_module(
            module_path="a.py",
            module_ast=parso.parse(data.content),
        )
    )

    assert data.merged_results == data.expected
