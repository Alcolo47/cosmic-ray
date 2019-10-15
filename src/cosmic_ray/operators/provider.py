"""Operator-provider plugin for all core cosmic ray operators.
"""

import itertools

from . import (
    modify_for_loop_zero_iteration_operator,
    modify_invert_logical_operator,
    modify_number_opperator,
    modify_string_operator,
    remove_decorator_operator,
    remove_field_of_specific_variables_operator,
    remove_named_argument_operator,
    remove_statement_operator,
    replace_binary_operators,
    replace_boolean_operators,
    replace_break_continue_operators,
    replace_comparison_operators,
    replace_exception_operator,
    replace_logical_operators,
    replace_none_to_values_operator,
    replace_unary_operators,
    replace_value_to_none_operator,
)

# NB: The no_op operator gets special handling. We don't include it in iteration of the
# available operators. However, you can request it from the provider by name. This lets us
# use it in a special way: to request that a worker perform a no-op test run while preventing
# it from being used in normal mutations testing runs.

_OPERATORS = {
    op.__name__: op
    for op in itertools.chain(
        replace_binary_operators.operators(),
        replace_comparison_operators.operators(),
        replace_unary_operators.operators(),
        (
            modify_for_loop_zero_iteration_operator.ModifyForLoopZeroIterationOperator,
            modify_invert_logical_operator.ModifyInvertLogicalOperator,
            modify_number_opperator.ModifyNumberOperator,
            modify_string_operator.ModifyStringOperator,
            remove_decorator_operator.RemoveDecoratorOperator,
            remove_field_of_specific_variables_operator.RemoveFieldOfSpecificVariablesOperator,
            remove_named_argument_operator.RemoveNamedArgumentOperator,
            remove_statement_operator.RemoveStatementOperator,
            replace_boolean_operators.ReplaceBooleanOperatorFalseWithTrue,
            replace_boolean_operators.ReplaceBooleanOperatorTrueWithFalse,
            replace_break_continue_operators.ReplaceBreakWithContinueOperator,
            replace_break_continue_operators.ReplaceContinueWithBreakOperator,
            replace_exception_operator.ReplaceExceptionoperator,
            replace_logical_operators.ReplaceLogicalOperatorAddNot,
            replace_logical_operators.ReplaceLogicalOperatorAndWithOr,
            replace_logical_operators.ReplaceLogicalOperatorOrWithAnd,
            replace_none_to_values_operator.ReplaceNoneToValuesOperator,
            replace_value_to_none_operator.ReplaceValueToNoneOperator,
        ),
    )
}


class OperatorProvider:
    """Provider for all of the core Cosmic Ray operators."""

    def __iter__(self):
        return iter(_OPERATORS)

    def __getitem__(self, name):
        return _OPERATORS[name]
