import re
from typing import Dict, List

from parso.tree import Node

from cosmic_ray.ast import get_comment_on_node_line
from cosmic_ray.interceptors.base import Interceptor
from cosmic_ray.operators.operator import Operator
from cosmic_ray.work_item import WorkItem, WorkResult, WorkerOutcome


class PragmaInterceptor(Interceptor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pragma_cache = None

    def pre_scan_module_path(self, module_path):
        self._pragma_cache = {}
        return True

    def post_add_work_item(self,
                           operator: Operator,
                           node: Node,
                           new_work_item: WorkItem):
        if self._have_excluding_pragma(node, operator):
            self._record_skipped_result_item(new_work_item.job_id)

    def _record_skipped_result_item(self, job_id):
        self.work_db.set_result(
            job_id,
            WorkResult(
                worker_outcome=WorkerOutcome.SKIPPED,
                output="Skipped: pragma found",
            )
        )

    def _have_excluding_pragma(self, node, operator: Operator) -> bool:
        """
        Return true if node have à pragma declaration that exclude
        self.operator. For this it's look for 'no mutation' pragma en analyse
        sub category of this pragma declaration.

        It use cache mechanism of pragma information across visitors.
        """

        pragma_categories = self._pragma_cache.get(node, True)
        # pragma_categories can be (None, False, list):
        #   use True as guard

        if pragma_categories is True:
            pragma = get_node_pragma_categories(node)
            if pragma:
                pragma_categories = pragma.get('no mutate', False)
            else:
                pragma_categories = False
            # pragma_categories is None: Exclude all operator
            # pragma_categories is list: Exclude operators in the list
            # pragma_categories is False:
            #    guard indicate no pragma: no filter
            self._pragma_cache[node] = pragma_categories

        if pragma_categories is False:
            return False

        if pragma_categories is None:
            return True

        return operator.pragma_category_name in pragma_categories


def get_node_pragma_categories(node) -> None or Dict[str, None or List[str]]:
    """
    Get pragma dictionary `see get_pragma_list` declared on the line
    of the node
    """
    comment = get_comment_on_node_line(node)
    if comment:
        return get_pragma_list(comment)
    else:
        return None


_re_pragma = re.compile(r'([-A-Za-z0-9](?: (?! )|[-A-Za-z0-9])*)(:?)(,?)')


def get_pragma_list(line: str) -> None or Dict[str, None or List[str]]:
    """
    Pragma syntax:
    - Any comment can be present before 'pragma:' declaration
    - You can have multiple pragma family separated with double space
        (allowing family name having multiple words)
    - You can declare sections of pragma if the pragma name is followed
        directly with ':'
    - Pragma family can have an empty section set if no section is declared
        after ':'  ex "fam:" or "fam1:  fam2
    - Section names can have a space (two spaces indicate the end
        of section list)
    - Sections are separated with ',', comma directly present after the
        previous section (no space)

    :return Dictionary of list of sections per pragma family.
        If a pragma family have no section, the dictionary will returns None

    >>> get_pragma_list("# comment")
    None
    >>> get_pragma_list("# comment pragma:")
    {}
    >>> get_pragma_list("# comment pragma: x y  z")
    {'x y': None, 'z': None}
    >>> get_pragma_list("# comment pragma: x:")
    {'x': []}
    >>> get_pragma_list("# comment pragma: x:  y")
    {'x': [], 'y': None}
    >>> get_pragma_list("# comment pragma: x y  z: d, e")
    {'x y': None, 'z': ['d', 'e']}
    >>> get_pragma_list("# comment pragma: x: a, b, c  y z: d, e")
    {'x': ['a', 'b', 'c'], 'y z': ['d', 'e']}
    >>> get_pragma_list("comment pragma: x: a, b, c y  z: d, e")
    {'x': ['a', 'b', 'c y'], 'z': ['d', 'e']}
    """
    split = line.split('pragma:', maxsplit=1)
    if len(split) == 1:
        return None
    pragma_list = split[1]

    pragma = {}
    family_name = None
    last_section_pos = None
    for m in _re_pragma.finditer(pragma_list):
        elt = m.group(1)

        if family_name and m.start() > last_section_pos + 1:
            # The element is too far away, a new family is starting
            family_name = None

        if family_name:
            # If family_name in progress, add elt as section
            pragma[family_name].append(elt)
            if not m.group(3):
                # If no comma, next will be a key
                family_name = None
                last_section_pos = None
            else:
                last_section_pos = m.end()
        else:
            # No family_name in progress, elt is the family_name
            if m.group(2):
                # Followed by ':', next will be a section
                family_name = elt
                pragma[family_name] = []
                last_section_pos = m.end()
            else:
                # No ':', this family_name have no section,
                # next is another family_name
                pragma[elt] = None
    return pragma
