import re

from parso.python.tree import ExprStmt, Operator as tree_Operator, PythonNode, \
    Name

from cosmic_ray.operators import Operator, operators_config
from cosmic_ray.utils.config import Config, Entry


remove_field_of_specific_variables_operator_config = Config(
    operators_config,
    'remove_field_of_specific_variables',
    valid_entries={
        'variables': Entry(default=['unique_together']),
    },
)


class RemoveFieldOfSpecificVariablesOperator(Operator):

    def __init__(self, name=None):
        super().__init__(name)
        self._re_var_names = None
        self._load_config()

    def set_config(self, config):
        remove_field_of_specific_variables_operator_config.set_config(config)
        self._load_config()

    def _load_config(self):
        var_names = remove_field_of_specific_variables_operator_config['variables']
        s = '|'.join('(?:%s)' % n for n in var_names)
        self._re_var_names = re.compile(s)

    def _is_name_match(self, name):
        return self._re_var_names.match(name)

    def mutation_positions(self, node):
        if isinstance(node, ExprStmt):
            if isinstance(node, ExprStmt) and len(node.children) == 3:
                child1 = node.children[1]
                if isinstance(child1, tree_Operator) and child1.value == '=':

                    child_name = node.children[0]
                    if isinstance(child_name, Name):

                        name = node.children[0].value
                        if self._is_name_match(name):

                            child1 = node.children[2]
                            if isinstance(child1, PythonNode) and child1.type == 'testlist_star_expr':
                                for i, child2 in enumerate(child1.children[::2]):
                                    yield child2.start_pos, child2.end_pos, child2, (child1, i * 2)

                            elif isinstance(child1, PythonNode) and child1.type == 'atom':
                                child2 = child1.children[1]
                                if isinstance(child2, PythonNode) and child2.type == 'testlist_comp':
                                    for i, child3 in enumerate(child2.children[::2]):
                                        yield child3.start_pos, child3.end_pos, child3, (child2, i * 2)
                                else:
                                    yield child2.start_pos, child2.end_pos, child2, (child1, 1)

    def mutate(self, node, parent_pos):
        parent, pos = parent_pos
        correlation_dict = {}
        node = self.clone_node(node, 4, correlation_dict)
        parent = correlation_dict[parent]
        children = parent.children

        if isinstance(parent, PythonNode) and parent.type == 'testlist_comp':
            if pos + 1 < len(children):
                del children[pos + 1]
            del children[pos]

            if len(children) == 1 and parent.parent.children[0].value == '(':
                children.append(tree_Operator(',', node.start_pos))

        elif isinstance(parent, PythonNode) and parent.type == 'atom':
            del children[pos]

        else:
            if pos + 1 < len(children):
                del children[pos + 1]
            del children[pos]

            if len(children) == 0:
                children[:] = [tree_Operator('()', node.start_pos, prefix=' ')]
            elif len(children) == 1:
                children.append(tree_Operator(',', node.start_pos))

        return node

    def examples(cls):
        config = {
            'variables': ['ab', 'cd'],
        }

        return (
            ('ab = (1, 2)', ('ab = ( 2,)','ab = (1,)'), config),
            ('ab = 1, 2', ('ab = 2,','ab = 1,'), config),
            ('cd = [1, 2]', ('cd = [ 2]','cd = [1,]'), config),
            ('cd = 1,', ('cd = ()',), config),
            ('cd = (1,)', ('cd = ()',), config),
            ('cd = [1,]', ('cd = []',), config),
            ('cd = [1]', ('cd = []',), config),
            ('ef = [1, 2]', (), config),
            ('self.x = None', (), config),
        )
