"""Implementation of the unary-operator-replacement operator.
"""

from enum import Enum
from itertools import permutations

from parso.python.tree import Keyword, Operator, PythonNode

from cosmic_ray.operators.util import ASTQuery
from . import operator
from .util import extend_name


class UnaryOperators(Enum):
    """All unary operators that we mutate.
    """
    UAdd = '+'
    USub = '-'
    Invert = '~'
    Not = 'not'
    Nothing = None


class ReplaceUnaryOperatorBase(operator.Operator):
    """An operator that replaces unary {} with unary {}.
    """

    from_op: UnaryOperators = None
    to_op: UnaryOperators = None

    def mutation_positions(self, node):
        if self._is_unary_operator(node):
            op = node.children[0]
            if op.value.strip() == self.from_op.value:
                yield op.start_pos, op.end_pos

    def mutate(self, node, index):
        assert index == 0
        assert self._is_unary_operator(node)

        node = self.clone_node(node, 1)
        if self.to_op.value is None:
            # This is a bit goofy since it can result in "return not x"
            # becoming "return  x" (i.e. with two spaces). But it's correct
            # enough.
            node.children[0].value = ''
        else:
            node.children[0].value = self.to_op.value
        return node

    @classmethod
    def examples(cls):
        from_code = '{} 1'.format(cls.from_op.value)
        to_code = ' 1'

        if cls.to_op is not UnaryOperators.Nothing:
            to_code = cls.to_op.value + to_code

        return (
            (from_code, to_code),
        )

    @staticmethod
    def _is_factor(node):
        return ASTQuery(node).match(PythonNode, type__in=('factor', 'not_test')) \
               .children[0].match(Operator).ok

    @staticmethod
    def _is_not_test(node):
        return ASTQuery(node).match (PythonNode, type='not_test') \
            .children[0].match(Keyword, value='not').ok

    @classmethod
    def _is_unary_operator(cls, node):
        return cls._is_factor(node) or cls._is_not_test(node)


def _prohibited(from_op, to_op):
    """Determines if from_op is allowed to be mutated to to_op.
    """

    # 'not' can only be removed but not replaced with
    # '+', '-' or '~' b/c that may lead to strange results
    if from_op is UnaryOperators.Not:
        if to_op is not UnaryOperators.Nothing:
            return True

    # '+1' => '1' yields equivalent mutations
    if from_op is UnaryOperators.UAdd:
        if to_op is UnaryOperators.Nothing:
            return True

    return False


def _create_replace_unary_operators(_from_op, _to_op):
    if _to_op.value is None:
        suffix = '_Delete_{}'.format(_from_op.name)
    else:
        suffix = '_{}_{}'.format(_from_op.name, _to_op.name)

    @extend_name(suffix)
    class ReplaceUnaryOperator(ReplaceUnaryOperatorBase):
        ReplaceUnaryOperatorBase.__doc__.format(_from_op.name, _to_op.name)
        from_op = _from_op
        to_op = _to_op

    return ReplaceUnaryOperator


_MUTATION_OPERATORS = tuple(
    _create_replace_unary_operators(from_op, to_op)
    for (from_op, to_op) in permutations(UnaryOperators, 2)
    if from_op.value is not None if not _prohibited(from_op, to_op))

for op_cls in _MUTATION_OPERATORS:
    globals()[op_cls.__name__] = op_cls


def operators():
    """Iterable of unary operator mutation operators.
    """
    return _MUTATION_OPERATORS
