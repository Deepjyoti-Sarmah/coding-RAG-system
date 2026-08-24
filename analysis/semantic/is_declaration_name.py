from tree_sitter import Node

from analysis.registry import NODE_HANDLERS

# Interface members are not extracted as child symbols, so they are not in
# NODE_HANDLERS — but their names are still declarations, not references.
_TYPE_MEMBER_DECLARATIONS = {
    "property_signature",
    "method_signature",
}


def is_declaration_name(node: Node) -> bool:
    parent = node.parent

    if parent is None:
        return False

    if parent.type not in NODE_HANDLERS.keys() | _TYPE_MEMBER_DECLARATIONS:
        return False

    name_node = parent.child_by_field_name("name")

    if name_node is None:
        return False

    return name_node == node
