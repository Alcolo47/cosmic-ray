"""Tests for the various mutation operators.
"""
import asyncio
from typing import Dict

import pytest

import parso
from parso.tree import Node

from cosmic_ray.commands.run import RunVisitor
from cosmic_ray.interceptors import Interceptors
from cosmic_ray.operators import Operator, operators
from cosmic_ray.db.work_item import WorkResult, WorkItem

from cosmic_ray.operators.replace_unary_operators import ReplaceUnaryOperator_USub_UAdd
from cosmic_ray.operators.replace_binary_operators import ReplaceBinaryOperator_Add_Mul


class DummyDb:
    def __init__(self):
        self.results = {}  # type: Dict[str, WorkResult]
        self.work_items = {}  # type: Dict[str, WorkItem]

    def add_work_item(self, work_item: WorkItem):
        self.work_items[work_item.job_id] = work_item

    def set_result(self, job_id, work_result: WorkResult):
        self.results[job_id] = work_result


class Sample:
    def __init__(self, operator: Operator, from_code, to_codes, config=None):
        self.operator = operator
        self.from_code = from_code
        self.to_codes = to_codes if isinstance(to_codes, (list, tuple)) else (to_codes,)
        self.config = config

    def __repr__(self):
        return "%s: %s" % (type(self.operator).__name__, self.from_code)


OPERATOR_PROVIDED_SAMPLES = tuple(
    Sample(operator, *example)
    for operator in operators.values()  # type: Operator
    for example in operator.examples()
)

EXTRA_SAMPLES = tuple(
    Sample(*args) for args in (
        # Make sure unary and binary op mutators don't pick up the wrong kinds of operators
        (ReplaceUnaryOperator_USub_UAdd(), 'x + 1', ()),
        (ReplaceBinaryOperator_Add_Mul(), '+1', ()),
    ))

OPERATOR_SAMPLES = OPERATOR_PROVIDED_SAMPLES + EXTRA_SAMPLES


@pytest.mark.parametrize('sample', OPERATOR_SAMPLES)
def test_mutation_changes_ast(sample: Sample, dummy_execution_engine):
    try:
        db = DummyDb()
        execution_engine = dummy_execution_engine
        interceptors = Interceptors([])
        node: Node = parso.parse(sample.from_code)

        sample.operator.set_config(sample.config)

        visitor = RunVisitor(module_path="a.py",
                             work_db=db,
                             execution_engine=execution_engine,
                             operator=sample.operator,
                             interceptors=interceptors,
                             )

        asyncio.get_event_loop().run_until_complete(visitor.walk(node))

        assert execution_engine.new_codes == list(sample.to_codes)
        assert node.get_code() == sample.from_code

    except Exception as ex:
        raise
