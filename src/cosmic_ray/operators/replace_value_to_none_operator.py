from parso.python.tree import ExprStmt, Operator as tree_Operator, PythonNode, \
    Keyword

from cosmic_ray.operators import Operator


class ReplaceValueToNoneOperator(Operator):

    def mutation_positions(self, node):
        if isinstance(node, ExprStmt) and len(node.children) == 3:
            child = node.children[1]
            if isinstance(child, tree_Operator) and child.value == '=':
                child = node.children[2]
                if isinstance(child, PythonNode) and child.type == 'testlist_star_expr':
                    for i, child2 in enumerate(child.children[::2]):
                        if not isinstance(child2, Keyword) or child2.value != 'None':
                            yield child2.start_pos, child2.end_pos, child2, (child, i*2)
                else:
                    if not isinstance(child, Keyword) or child.value != 'None':
                        yield child.start_pos, child.end_pos, child, (node, 2)

    def mutate(self, node, parent_pos):
        parent, pos = parent_pos
        correlation_dict = {}
        node = self.clone_node(node, 3, correlation_dict)
        parent = correlation_dict[parent]
        old_child = parent.children[pos]
        parent.children[pos] = Keyword('None', old_child.start_pos, prefix=' ')
        return node


    def examples(cls):
        return (
            ('a = 1', 'a = None'),
            ('a = None', ()),
            ('a, b = 1, 2', (
                'a, b = None, 2',
                'a, b = 1, None',
            )),
            ('a, b = None, None', ()),
        )
