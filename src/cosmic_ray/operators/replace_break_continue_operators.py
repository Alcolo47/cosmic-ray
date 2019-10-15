"""Implementation of the replace-break-with-continue and
replace-continue-with-break operators.
"""

from .replace_keyword_operator import ReplaceKeywordOperator


class ReplaceBreakWithContinueOperator(ReplaceKeywordOperator):
    """Operator which replaces 'break' with 'continue'.
    """
    from_keyword = 'break'
    to_keyword = 'continue'


class ReplaceContinueWithBreakOperator(ReplaceKeywordOperator):
    """Operator which replaces 'continue' with 'break'.
    """
    from_keyword = 'continue'
    to_keyword = 'break'
