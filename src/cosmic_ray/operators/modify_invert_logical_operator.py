from parso.python.tree import PythonNode, Operator as tree_Operator, Keyword

from cosmic_ray.operators import Operator


class ModifyInvertLogicalOperator(Operator):

    python_node_types = (
        'and_test', 'or_test', 'not_test', 'comparison'
    )

    def mutation_positions(self, node):
        if isinstance(node, PythonNode) and node.type in self.python_node_types:
            yield node.start_pos, node.end_pos

    def mutate(self, node, index):
        # parents are useless to use get_code()
        return PythonNode('not_test', children=[
            Keyword('not', node.start_pos),
            tree_Operator('(', node.start_pos, prefix=' '),
            node,
            tree_Operator(')', node.end_pos),
        ])

    def examples(cls):
        return (
            ('a and b', 'not (a and b)'),
            ('a or b', 'not (a or b)'),
            ('not a', 'not (not a)'),
            ('a < b', 'not (a < b)'),
            ('(a and b) or (a < b)', (
                'not ((a and b) or (a < b))',
                '(not (a and b)) or (a < b)',
                '(a and b) or (not (a < b))',
              ),
             ),
        )
