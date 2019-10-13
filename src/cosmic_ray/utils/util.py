import abc
import re
from abc import ABC

_re_camel_to_kebab_case = re.compile(r'([0-9a-z])([A-Z])')


def to_kebab_case(s: str) -> str:
    """
    Convert from CamelCase or snake_case (or mixed) to kebab-case.

    >>> to_kebab_case('AbcDefGhi')
    'abc-def-ghi'
    >>> to_kebab_case('abcDefGhi')
    'abc-def-ghi'
    >>> to_kebab_case('abc_def_ghi')
    'abc-def-ghi'
    >>> to_kebab_case('abcDef_ghi')
    'abc-def-ghi'
    """
    s = s.replace('_', '-')
    return _re_camel_to_kebab_case.sub(r'\1-\2', s).lower()


def dict_filter(base_dict, filters):
    result = {}
    for i, filter in enumerate(filters):  # type: int, str
        if filter.startswith(('+', '-')):
            exclude = filter.startswith('-')
            filter = filter[1:].lstrip()
        else:
            exclude = False

        if exclude and i == 0:
            result = base_dict

        if exclude:
            result = {k: v for k, v in result.items() if not re.match(filter, k)}
        else:
            result.update({k: v for k, v in base_dict.items() if re.match(filter, k)})

    return result


class LazyDict():
    def __init__(self, elts=None):
        if isinstance(elts, (tuple, list, set)):
            elts = dict(enumerate(elts))
        self._elts = elts

    @abc.abstractmethod
    def _load(self):
        pass

    @property
    def elts(self):
        if self._elts is None:
            self._elts = self._load()
        return self._elts

    def __getitem__(self, item):
        return self.elts[item]

    def __iter__(self):
        return iter(self.elts)

    def __bool__(self):
        return bool(self.elts)

    def __len__(self):
        return len(self.elts)

    def items(self):
        return self.elts.items()

    def keys(self):
        return self.elts.keys()

    def values(self):
        return self.elts.values()
