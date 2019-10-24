import asyncio
import difflib
import logging
import signal
import uuid
from asyncio import Future, CancelledError
from asyncio import Task
from contextlib import contextmanager

import sys
from typing import List, Iterable

from parso.tree import NodeOrLeaf, BaseNode

from cosmic_ray.db.work_item import WorkResult, Outcome
from cosmic_ray.execution_engines import execution_engines
from cosmic_ray.execution_engines.execution_engine import ExecutionEngine, \
    ExecutionData, execution_engine_config
from cosmic_ray.interceptors import interceptors
from cosmic_ray.utils.ast import get_ast, Visitor
from cosmic_ray.utils.config import root_config
from cosmic_ray.interceptors import Interceptors
from cosmic_ray.operators import operators
from cosmic_ray.operators.operator import Operator
from cosmic_ray.db.work_item import WorkItem
from cosmic_ray.db.work_db import WorkDB
from cosmic_ray.utils.progress import update_progress

log = logging.getLogger(__name__)


class RunVisitor(Visitor):
    """An AST visitor that initializes a WorkDB for a specific module and operator.

    The idea is to walk the AST looking for nodes that the operator can mutate.
    As they're found, `activate` is called and this core adds new
    WorkItems to the WorkDB. Use this core to populate a WorkDB by creating one
    for each operator-module pair and running it over the module's AST.
    """

    def __init__(self, module_path, work_db, operator,
                 interceptors: Interceptors,
                 execution_engine: ExecutionEngine,
                 tasks: List[Task]):
        self.operator = operator  # type: Operator
        self.module_path = module_path  # type: str
        self.tasks = tasks
        self.work_db = work_db  # type: WorkDB
        self.occurrence = 0
        self._interceptors = interceptors
        self.execution_engine = execution_engine  # type: ExecutionEngine
        self.original_code = None

    async def walk(self, node: BaseNode):
        self.original_code = node.get_code()
        await super().walk(node)

    async def visit(self, node: NodeOrLeaf, child_pos):
        for index, start_stop in enumerate(self.operator.mutation_positions(node)):
            if len(start_stop) == 2:
                (start, stop), target_node = start_stop, node
            elif len(start_stop) == 3:
                start, stop, target_node = start_stop
            else:
                start, stop, target_node, index = start_stop

            if self._interceptors.new_mutation(self.operator, target_node):
                work_item = WorkItem(
                    job_id=uuid.uuid4().hex,
                    module_path=self.module_path,
                    operator_name=self.operator.name,
                    occurrence=self.occurrence,
                    start_pos=start,
                    end_pos=stop,
                )

                new_node = self.operator.mutate(node, index)

                with self._apply_new_node(node.parent, node, new_node, child_pos):
                    new_code = self.root_node.get_code()

                diff = self._make_diff(self.original_code, new_code, self.module_path)
                work_item.diff = '\n'.join(diff)
                self.work_db.add_work_item(work_item)
                self.occurrence += 1

                if self._interceptors.new_work_item(self.work_db, self.operator, target_node, work_item):
                    execution_data = ExecutionData(job_id=work_item.job_id,
                                                   filename=self.module_path,
                                                   new_code=new_code)
                    future = asyncio.ensure_future(self.execution_engine.execute(execution_data))
                    future.add_done_callback(self._on_task_complete)
                    self.tasks.append(future)
                    await asyncio.sleep(0)

    @staticmethod
    @contextmanager
    def _apply_new_node(parent, old_node, new_node, node_pos):
        if new_node:
            parent.children[node_pos] = new_node
            try:
                yield
            finally:
                parent.children[node_pos] = old_node

        else:
            del parent.children[node_pos]
            try:
                yield
            finally:
                parent.children[node_pos:node_pos] = [old_node]

    def _on_task_complete(self, future: Future):
        if future.cancelled():
            return
        job_id, work_result = future.result()
        self.work_db.set_result(job_id, work_result)
        update_progress(self.work_db)
        log.debug("Job %s complete", job_id)

    @staticmethod
    def _make_diff(original_source, mutated_source, module_path):
        module_diff = ["--- mutation diff ---"]
        for line in difflib.unified_diff(
                original_source.split('\n'),
                mutated_source.split('\n'),
                fromfile="a" + module_path,
                tofile="b" + module_path,
                lineterm=""):
            module_diff.append(line)
        return module_diff


@contextmanager
def on_signal(sig, callable):
    old = signal.signal(sig, callable)
    yield
    signal.signal(sig, old)


class Run:
    def __init__(self, work_db: WorkDB):
        """Clear and initialize a work-db with work items.

        Any existing data in the work-db will be cleared and replaced with entirely
        new work orders. In particular, this means that any results in the db are
        removed.

        Args:
          work_db: A `WorkDB` instance into which the work orders will be saved.
        """
        self.work_db = work_db
        self.execution_engine = execution_engines[execution_engine_config['type']]  # type: ExecutionEngine
        self.operators = operators.values()
        self.interceptors = interceptors
        self.tasks = []  # type: List[Task]
        self.exit_code = 0

    def run(self, module_paths: Iterable[str]):
        self.work_db.set_config(config=root_config.get_config())
        self.work_db.clear()

        loop = asyncio.new_event_loop()
        try:
            with on_signal(signal.SIGINT, self.on_break):
                loop.run_until_complete(self.run_async(module_paths))
        except CancelledError:
            pass

        return self.exit_code

    async def run_async(self, module_paths):

        await self.execution_engine.init()

        try:
            if execution_engine_config['run-with-no-mutation']:
                future = asyncio.ensure_future(self.execution_engine.execute(None))
                future.add_done_callback(self._on_no_mutation_task_complete)

            for module_path in module_paths:
                module_ast = get_ast(module_path, python_version=root_config['python-version'])
                await self.visit_module(module_path, module_ast)

            await asyncio.gather(*self.tasks)
            await self.execution_engine.no_more_jobs()

        finally:
            self.execution_engine.close()

    async def visit_module(self, module_path, module_ast):
        if self.interceptors.pre_scan_module_path(module_path):
            for operator in self.operators:
                visitor = RunVisitor(
                    work_db=self.work_db,
                    module_path=module_path,
                    interceptors=self.interceptors,
                    operator=operator,
                    execution_engine=self.execution_engine,
                    tasks=self.tasks,
                )
                await visitor.walk(module_ast)

            interceptors.post_scan_module_path(module_path)

    def _on_no_mutation_task_complete(self, future: Future):
        if future.cancelled():
            return
        _, work_result = future.result()  # type: None, WorkResult
        if work_result.outcome != Outcome.SURVIVED:
            print("Running without mutation fails:", file=sys.stderr)
            for line in work_result.output.split('\n'):
                print("  >>>", line, file=sys.stderr)
            self.cancel_all()

    def cancel_all(self):
        log.info("Cancelling all runs")
        for t in asyncio.all_tasks():
            if t is not asyncio.current_task():
                t.cancel()
        self.exit_code = 1

    def on_break(self, *args):
        print("Break requested: cancelling all runs")
        self.cancel_all()
        raise CancelledError()
