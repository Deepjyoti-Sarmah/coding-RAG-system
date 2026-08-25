"""Safe access to tree-sitter node source text.

`Node.text` is typed `bytes | None` in tree-sitter >= 0.25; every call
site used to repeat a None guard plus `.decode("utf-8")`. This helper
centralizes both.
"""

from tree_sitter import Node


def node_text(node: Node) -> str:
    text = node.text

    if text is None:
        return ""

    return text.decode("utf-8")
