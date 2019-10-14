import parso
import sys
from parso.python.tree import PythonNode, Name, String, Module, Function
from parso.tree import Node

from cosmic_ray.utils.ast import is_string
from cosmic_ray.utils.config import Config
from cosmic_ray.operators import operators_config
from cosmic_ray.operators.operator import Operator
from cosmic_ray.operators.util import ASTQuery


string_replacer_config = Config(
    operators_config,
    'string-replacer',
    valid_entries={
        'filter-if-called-by': (),
        'replace-with': "COSMIC %s RAY",
    },
)


class StringReplacer(Operator):
    """An operator that modifies numeric constants."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filtered_functions = None
        self.replace_with = None
        self.read_config()

    def read_config(self):
        self.filtered_functions = set(string_replacer_config['filter-if-called-by'])
        self.replace_with = string_replacer_config['replace-with']

    def set_config(self, config):
        string_replacer_config.set_config(config)
        self.read_config()

    def mutation_positions(self, node: Node):
        # _("abc"):
        # gives
        # [
        #     Name('_'),
        #     PythonNode('trailer', [
        #         Operator('('),
        #         Name('abc'),  <-- node
        #         Operator(')'),
        #     ]),
        # ]

        # self.tr("abc") gives:
        # [
        #     PythonNode('atom_expr', [
        #         Name('self'),
        #         PythonNode('trailer', [
        #             Operator('.'),
        #             Name('tr')
        #         ]),
        #         PythonNode('trailer', [
        #             Operator('('),
        #             Name('abc'),  <-- node
        #             Operator(')'),
        #         ]),
        #     ]),
        # ]

        if is_string(node) and not self._is_docstring(node):
            if self.filtered_functions:
                if ASTQuery(node). \
                        IF.match(PythonNode, type='fstring').parent.FI. \
                        IF.parent.match(PythonNode, type='trailer').FI. \
                        match(PythonNode, type='trailer'). \
                        get_previous_sibling(). \
                        IF.match(PythonNode, type='trailer').children[-1].FI. \
                        match(Name, value__in=self.filtered_functions).ok:
                    return

            yield node.start_pos, node.end_pos

    @classmethod
    def _is_docstring(cls, node):
        return cls._is_module_docstring(node) or \
               cls. _is_function_docstring(node)

    @staticmethod
    def _is_module_docstring(node):
        """
        Module(file_input, [
            PythonNode(simple_stmt, [  <-- or not
                String(string, '"Doc string"'),
            ]),
        ])
        """
        return ASTQuery(node).match(String). \
            IF.parent.match(PythonNode, type='simple_stmt').FI. \
            parent.match(Module).ok

    @staticmethod
    def _is_function_docstring(node):
        """
        Function(funcdef, [
            Keyword(keyword, 'def'),
            Name(name, 'f'),
            PythonNode(parameters, [...]),
            Operator(operator, ':'),
            PythonNode(suite, [
                Newline(newline, '\n'),
                PythonNode(simple_stmt, [  <-- or not
                    String(string, '"doc"'),  <-- node
                    Newline(newline, '\n'),
                ]),
            ]),
        ]),
        """
        return ASTQuery(node).match(String). \
            IF.parent.match(PythonNode, type='simple_stmt').FI. \
            parent.match(PythonNode, type='suite'). \
            parent.match(Function).ok

    def mutate(self, node, index):
        """Modify the numeric value on `node`."""
        if isinstance(node, String):
            s = node.value
            if s.endswith(("'''", '"""')):
                enclose_end = 3
            else:
                enclose_end = 1
            enclose_start = enclose_end
            if s.startswith(('r', 'b', 'u')):
                enclose_start += 1

            new_s = self.replace_with % s[enclose_start:-enclose_end]
            node = self.clone_node(node)
            node.value = '%s%s%s' % (s[:enclose_start], new_s, s[-enclose_end:])
            return node

        elif isinstance(node, PythonNode):
            s = ''.join(n.get_code() for n in node.children[1:-1])
            s = self.replace_with % s
            s = '%s%s%s' % (node.children[0].value, s, node.children[-1].value)
            node = self.clone_node(node)
            node.children[:] = parso.parse(s).children[0].children
            return node

        else:
            raise ValueError("Node can't be of type {}".format(type(node).__name__))

    @classmethod
    def examples(cls):
        config = {
            'replace-with': 'XX %s',
            'filter-if-called-by': ['_', 'tr'],
        }
        data = [
            ('s = "abc"', 's = "XX abc"', config),
            ('s = """abc"""', 's = """XX abc"""', config),
            ("s = '''abc'''", "s = '''XX abc'''", config),

            ('s = r"abc"', 's = r"XX abc"', config),
            ('s = r"""abc"""', 's = r"""XX abc"""', config),
            ("s = r'''abc'''", "s = r'''XX abc'''", config),

            ('s = b"abc"', 's = b"XX abc"', config),
            ('s = b"""abc"""', 's = b"""XX abc"""', config),
            ("s = b'''abc'''", "s = b'''XX abc'''", config),

            ('s = u"abc"', 's = u"XX abc"', config),
            ('s = u"""abc"""', 's = u"""XX abc"""', config),
            ("s = u'''abc'''", "s = u'''XX abc'''", config),

            ('f("abc")', 'f("XX abc")', config),
            ('_("abc")', (), config),
            ('self.tr("abc")', (), config),
            ('"Module doc string"', (), config),
            ('def f():\n    "Function doc string"', (), config),
        ]

        if sys.version_info >= (3, 6):
            # Adding fstring
            data += [
                ('s = f"abc"', 's =f"XX abc"', config),
                ('s = f"abc {1} def"', 's =f"XX abc {1} def"', config),
                ('s = _(f"abc {1} def")', (), config),
            ]

        return data
