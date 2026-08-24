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

    if in_extends_clause(node):
        return ReferenceKind.EXTENDS

    if in_implements_clause(node):
        return ReferenceKind.IMPLEMENTS

    return ReferenceKind.IDENTIFIER


def in_extends_clause(node: Node) -> bool:
    parent = node.parent

    # `class X extends Y` is an extends_clause; `interface X extends Y`
    # is an extends_type_clause.
    return parent is not None and parent.type in (
        "extends_clause",
        "extends_type_clause",
    )


def in_implements_clause(node: Node) -> bool:
    parent = node.parent

    return parent is not None and parent.type == "implements_clause"


def is_call_target(node: Node) -> bool:
    parent = node.parent

    return (
        parent is not None
        and parent.type == "call_expression"
        and parent.child_by_field_name("function") == node
    )
