"""Implementation of the boolean replacement operators.
"""

from .replace_keyword_operator import ReplaceKeywordOperator


class ReplaceBooleanOperatorTrueWithFalse(ReplaceKeywordOperator):
    """An that replaces True with False."""
    from_keyword = 'True'
    to_keyword = 'False'


class ReplaceBooleanOperatorFalseWithTrue(ReplaceKeywordOperator):
    """An that replaces False with True."""
    from_keyword = 'False'
    to_keyword = 'True'
