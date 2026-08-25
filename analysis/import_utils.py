from tree_sitter import Node
from parsing.node_text import node_text


def get_module_path(node: Node) -> str | None:
    current = node

    while current.parent is not None:
        current = current.parent

        if current.type == "import_statement":
            break

    if current.type != "import_statement":
        return None

    string_node = current.child_by_field_name("source")

    if string_node is None:
        return None

    fragment = string_node.child_by_field_name("fragment")

    if fragment is not None:
        return node_text(fragment)

    for child in string_node.children:
        if child.type == "string_fragment":
            return node_text(child)

    return None
