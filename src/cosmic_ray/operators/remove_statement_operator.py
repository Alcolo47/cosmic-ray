from parso.python.tree import PythonNode, Function, Class, ExprStmt
from parso.tree import Node

from cosmic_ray.operators import Operator


class RemoveStatementOperator(Operator):
    python_node_types = (
        'async_stmt',
        'simple_stmt',
    )

    def mutation_positions(self, node: Node):
        if (isinstance(node, PythonNode) and node.type in self.python_node_types) or \
                isinstance(node, (Function, Class, ExprStmt)):
            yield node.start_pos, node.end_pos

    def mutate(self, node, index):
        return None

    @classmethod
    def examples(cls):
        return (
            ('class A: pass', ''),
            ('def f(): pass', ''),
            ('async def f(): pass', ('', 'async')),
            ('a = 3', ''),
        )
