"""Implementation of the exception-replacement operator.
"""

from parso.python.tree import Name, PythonNode

from cosmic_ray.operators.util import ASTQuery
from .operator import Operator

from cosmic_ray.utils.exceptions import CosmicRayTestingException


class ReplaceExceptionoperator(Operator):
    """An operator that modifies exception handlers.
    """

    def mutation_positions(self, node):
        if ASTQuery(node).match(Name).parent \
                .IF.match(PythonNode, type='testlist_comp').parent \
                   .match(PythonNode, type='atom').parent.FI \
                .match(PythonNode, type='except_clause') \
                .ok:
            yield node.start_pos, node.end_pos

    def mutate(self, node, index):
        node = self.clone_node(node)
        node.value = CosmicRayTestingException.__name__
        return node

    @classmethod
    def examples(cls):
        return (
            ('try: raise OSError\nexcept OSError: pass',
             'try: raise OSError\nexcept {}: pass'.format(CosmicRayTestingException.__name__)),

            ('try: raise OSError\nexcept (OSError, ValueError): pass', (
             'try: raise OSError\nexcept ({}, ValueError): pass'.format(CosmicRayTestingException.__name__),
             'try: raise OSError\nexcept (OSError, {}): pass'.format(CosmicRayTestingException.__name__),
            )),

            ('try: raise OSError\nexcept (OSError, ValueError, KeyError): pass', (
             'try: raise OSError\nexcept ({}, ValueError, KeyError): pass'.format(CosmicRayTestingException.__name__),
             'try: raise OSError\nexcept (OSError, {}, KeyError): pass'.format(CosmicRayTestingException.__name__),
             'try: raise OSError\nexcept (OSError, ValueError, {}): pass'.format(CosmicRayTestingException.__name__),
            )),

            ('try: pass\nexcept: pass', ()),
        )
