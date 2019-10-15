from parso.python.tree import Keyword, String

from cosmic_ray.operators import Operator


class ReplaceNoneToValuesOperator(Operator):

    def mutation_positions(self, node):
        if isinstance(node, Keyword) and node.value == 'None':
            yield node.start_pos, node.end_pos, node, '55'
            yield node.start_pos, node.end_pos, node, '"abc"'
            yield node.start_pos, node.end_pos, node, 'True'

    def mutate(self, node, value):
        return String(value, node.start_pos, prefix=' ')

    def examples(cls):
        return (
            ('a = None', (
                'a = 55',
                'a = "abc"',
                'a = True',
            )),
        )
