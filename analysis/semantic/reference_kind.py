from tree_sitter import Node

from models.entities.reference_kind import ReferenceKind


def determine_reference_kind(node: Node) -> ReferenceKind:

    parent = node.parent

    if parent is None:
        return ReferenceKind.IDENTIFIER

    if (
        parent is not None
        and parent.type == "call_expression"
        and parent.child_by_field_name("function") == node
    ):
        return ReferenceKind.CALL

    return ReferenceKind.IDENTIFIER
