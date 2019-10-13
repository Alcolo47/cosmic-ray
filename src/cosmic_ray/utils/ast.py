"""Tools for working with parso ASTs."""
from abc import ABC, abstractmethod

import parso.python.tree
import parso.tree
from parso.tree import Leaf, NodeOrLeaf, BaseNode


class Visitor(ABC):
    """AST visitor for parso trees.
    """

    async def walk(self, node: BaseNode):
        self.root_node: BaseNode = node
        await self.sub_walk(node, -1)

    async def sub_walk(self, node, child_pos):
        """Walk a parse tree, calling visit for each node."""
        await self.visit(node, child_pos)
        if isinstance(node, BaseNode):
            for child_pos, child in enumerate(node.children):
                await self.sub_walk(child, child_pos)

    @abstractmethod
    async def visit(self, node: NodeOrLeaf, child_pos):
        """Called for each node in the walk."""


def get_ast(module_path, python_version):
    """Get the AST for the code in a file.

    Args:
        module_path: pathlib.Path to the file containing the code.
        python_version: Python version as a "MAJ.MIN" string.

    Returns: The parso parse tree for the code in `module_path`.
    """
    with module_path.open(mode='rt', encoding='utf-8') as handle:
        source = handle.read()

    return parso.parse(source, version=python_version)


def get_comment_on_node_line(node) -> str or None:
    """
    From a parso node, get the comment on the node line
    and return the comment
    """

    while not isinstance(node, Leaf):
        node = node.children[0]

    # Now we are looking for any non empty prefix before next '\n'
    while node is not None:
        node = node.get_next_leaf()
        if node:
            # don't strip '\n'
            prefix = node.prefix.strip(" \t")
            if prefix:
                return prefix

        if isinstance(node, parso.python.tree.Newline):
            return node.prefix


def is_none(node):
    "Determine if a node is the `None` keyword."
    return isinstance(node, parso.python.tree.Keyword) and node.value == 'None'


def is_number(node):
    "Determine if a node is a number."
    return isinstance(node, parso.python.tree.Number)


def is_string(node):
    "Determine if a node is a string."
    return isinstance(node, (parso.python.tree.String)) or \
           (isinstance(node, parso.python.tree.PythonNode) and node.type == 'fstring')
