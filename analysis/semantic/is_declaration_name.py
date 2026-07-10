from tree_sitter import Node

from analysis.registry import NODE_HANDLERS


def is_declaration_name(node: Node) -> bool:
    parent = node.parent

    if parent is None:
        return False

    if parent.type not in NODE_HANDLERS:
        return False

    name_node = parent.child_by_field_name("name")

    if name_node is None:
        return False

    return name_node == node
