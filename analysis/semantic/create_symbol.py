from collections.abc import Callable

from tree_sitter import Node

Handler = Callable[..., object]


def creates_symbol(node: Node, handlers: dict[str, Handler]) -> bool:
    return node.type in handlers
