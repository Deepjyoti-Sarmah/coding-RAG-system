from tree_sitter import Node


def resolve_call_target(
    node: Node,
) -> str | None:

    if node.type == "identifier":
        return node.text.decode("utf-8")

    elif node.type == "member_expression":
        property_node = node.child_by_field_name("property")

        if property_node is None:
            return None

        return property_node.text.decode("utf-8")

    return None
