"""Implementation of the zero-iteration-loop operator.
"""

import parso
from parso.python.tree import ForStmt

from .operator import Operator


class ModifyForLoopZeroIterationOperator(Operator):
    """An operator that modified for-loops to have zero iterations."""

    def mutation_positions(self, node):
        if isinstance(node, ForStmt):
            expr = node.children[3]
            yield (expr.start_pos, expr.end_pos)

    def mutate(self, node, index):
        """Modify the For loop to evaluate to None"""
        assert index == 0
        assert isinstance(node, ForStmt)

        empty_list = parso.parse(' []')
        node = self.clone_node(node)
        node.children[3] = empty_list
        return node

    @classmethod
    def examples(cls):
        return (
            ('for i in range(1,2): pass', 'for i in []: pass'),
        )
