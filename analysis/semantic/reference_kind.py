from tree_sitter import Node

from models.entities.reference_kind import ReferenceKind


def determine_reference_kind(node: Node) -> ReferenceKind:

    if node.type == "member_expression":
        if is_call_target(node):
            return ReferenceKind.CALL

        return ReferenceKind.MEMBER_ACCESS

    parent = node.parent

    if parent is None:
        return ReferenceKind.IDENTIFIER

    if is_call_target(node):
        return ReferenceKind.CALL

    return ReferenceKind.IDENTIFIER


def is_call_target(node: Node) -> bool:
    parent = node.parent

    return (
        parent is not None
        and parent.type == "call_expression"
        and parent.child_by_field_name("function") == node
    )
