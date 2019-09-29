"""Operator-provider plugin for all core cosmic ray operators.
"""

import itertools
from typing import Dict
from typing import Type

from cosmic_ray.operators.operator import Operator
from . import (binary_operator_replacement, boolean_replacer, break_continue,
               comparison_operator_replacement, exception_replacer,
               number_replacer, remove_decorator, unary_operator_replacement,
               zero_iteration_for_loop, string_replacer)

_OPERATORS = {
    op.__name__: op
    for op in itertools.chain(binary_operator_replacement.operators(
    ), comparison_operator_replacement.operators(
    ), unary_operator_replacement.operators(), (
        boolean_replacer.AddNot, boolean_replacer.ReplaceTrueWithFalse,
        boolean_replacer.ReplaceFalseWithTrue,
        boolean_replacer.ReplaceAndWithOr, boolean_replacer.ReplaceOrWithAnd,
        break_continue.ReplaceBreakWithContinue,
        break_continue.ReplaceContinueWithBreak,
        exception_replacer.ExceptionReplacer,
        number_replacer.NumberReplacer,
        remove_decorator.RemoveDecorator,
        zero_iteration_for_loop.ZeroIterationForLoop,
        string_replacer.StringReplacer,
    ))
}  # type: Dict[str, Type[Operator]]


class OperatorProvider:
    """Provider for all of the core Cosmic Ray operators."""

    def __iter__(self):
        return iter(_OPERATORS)

    def __getitem__(self, name) -> Type[Operator]:
        return _OPERATORS[name]
