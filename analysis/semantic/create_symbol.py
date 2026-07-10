from tree_sitter import Node

from analysis.registry import NODE_HANDLERS


def creates_symbol(node: Node) -> bool:
    return node.type in NODE_HANDLERS
