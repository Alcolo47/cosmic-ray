import parso.python
from parso.python.tree import IfStmt, WhileStmt, AssertStmt

from cosmic_ray.operators import Operator
from cosmic_ray.operators.replace_keyword_operator import ReplaceKeywordOperator


class ReplaceLogicalOperatorAndWithOr(ReplaceKeywordOperator):
    """An operator that swaps 'and' with 'or'."""
    from_keyword = 'and'
    to_keyword = 'or'

    @classmethod
    def examples(cls):
        return (
            ('x and y', 'x or y'),
        )


class ReplaceLogicalOperatorOrWithAnd(ReplaceKeywordOperator):
    """An operator that swaps 'or' with 'and'."""
    from_keyword = 'or'
    to_keyword = 'and'

    @classmethod
    def examples(cls):
        return (
            ('x or y', 'x and y'),
        )


class ReplaceLogicalOperatorAddNot(Operator):
    """
        An operator that adds the 'not' keyword to boolean expressions.

        NOTE: 'not' as unary operator is mutated in
         `unary_operator_replacement.py`, including deletion of the same
         operator.
    """
    NODE_TYPES = (IfStmt, WhileStmt, AssertStmt)

    def mutation_positions(self, node):
        if isinstance(node, self.NODE_TYPES):
            expr = node.children[1]
            yield (expr.start_pos, expr.end_pos)
        elif isinstance(node,
                        parso.python.tree.PythonNode) and node.type == 'test':
            # ternary conditional
            expr = node.children[2]
            yield (expr.start_pos, expr.end_pos)

    def mutate(self, node, index):
        assert index == 0

        if isinstance(node, self.NODE_TYPES):
            expr_node = node.children[1]
            mutated_code = ' not{}'.format(expr_node.get_code())
            mutated_node = parso.parse(mutated_code)
            node = self.clone_node(node)
            node.children[1] = mutated_node

        else:
            assert node.type == 'test'
            expr_node = node.children[2]
            mutated_code = ' not{}'.format(expr_node.get_code())
            mutated_node = parso.parse(mutated_code)
            node = self.clone_node(node)
            node.children[2] = mutated_node

        return node

    @classmethod
    def examples(cls):
        return (
            ('if True or False: pass', 'if not True or False: pass'),
            ('A if B else C', 'A if not B else C'),
            ('assert isinstance(node, ast.Break)', 'assert not isinstance(node, ast.Break)'),
            ('while True: pass', 'while not True: pass'),
        )
