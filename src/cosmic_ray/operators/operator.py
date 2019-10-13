"Implementation of operator base class."

from abc import ABC, abstractmethod
from copy import copy

from parso.tree import BaseNode, NodeOrLeaf


class Operator(ABC):
    """The mutation operator base class.

    Args:
        python_version: The version of Python to use when interpreting the code in `module_path`.
            A string of the form "MAJOR.MINOR", e.g. "3.6" for Python 3.6.x.
    """

    def __init__(self, name=None):
        self.name = name or type(self).__name__

    def set_config(self, config):
        """Force configuration: useful for tests
        """
        pass


    @abstractmethod
    def mutation_positions(self, node):
        """All positions where this operator can mutate `node`.

        An operator might be able to mutate a node in multiple ways, and this
        function should produce a position description for each of these
        mutations. Critically, if an operator can make multiple mutations to the
        same position, this should produce a position for each of these
        mutations (i.e. multiple identical positions).

        Returns: An iterable of `((start-line, start-col), (stop-line,
            stop-col))` tuples describing the locations where this operator will
            mutate `node`
        """

    @abstractmethod
    def mutate(self, node, index):
        """Mutate a node in an operator-specific manner.

        Return the new, mutated node. Return `None` if the node has
        been deleted. Return `node` if there is no mutation at all for
        some reason.
        """

    @classmethod
    def clone_node(cls, node: NodeOrLeaf, level=0):
        if isinstance(node, BaseNode) and level > 0:
            children = [cls.clone_node(n, level-1) for n in node.children]
        else:
            children = None

        node = copy(node)

        if isinstance(node, BaseNode):
            node.children = copy(node.children)
            if children is not None:
                node.children[:] = children
        return node

    @classmethod
    @abstractmethod
    def examples(cls):
        """Examples of the mutations that this operator can make.

        This is primarily for testing purposes, but it could also be used for
        documentation.

        Each example is a tuple of the form `(from-code, to-code, index)`. The
        `index` is optional and will be assumed to be 0 if it's not included.
        The `from-code` is a string containing some Python code prior to
        mutation. The `to-code` is a string describing the code after mutation.
        `index` indicates the occurrence of the application of the operator to
        the code (i.e. for when an operator can perform multiple mutation to a
        piece of code).

        Returns: An iterable of example tuples.
        """
