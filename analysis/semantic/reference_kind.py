from tree_sitter import Node

from analysis.languages import LanguageProfile
from models.entities.reference_kind import ReferenceKind


def determine_reference_kind(node: Node, profile: LanguageProfile) -> ReferenceKind:

    if node.type == profile.member_node:
        if is_call_target(node, profile):
            return ReferenceKind.CALL

        return ReferenceKind.MEMBER_ACCESS

    parent = node.parent

    if parent is None:
        return ReferenceKind.IDENTIFIER

    if is_call_target(node, profile):
        return ReferenceKind.CALL

    if in_extends_clause(node, profile):
        return ReferenceKind.EXTENDS

    if in_implements_clause(node, profile):
        return ReferenceKind.IMPLEMENTS

    return ReferenceKind.IDENTIFIER


def in_extends_clause(node: Node, profile: LanguageProfile) -> bool:
    if profile.superclass_field is not None:
        return _in_superclass_chain(node, profile.superclass_field)

    parent = _skip_type_list(node.parent)

    # `class X extends Y` is an extends_clause; `interface X extends Y`
    # is an extends_type_clause.
    return parent is not None and parent.type in profile.extends_parents


def _in_superclass_chain(node: Node, superclass_field: str) -> bool:
    """True when `node` sits inside the base-class list of a class.

    Climbs parents until either the field chain proves it (identifier ->
    argument_list -> class_definition with matching superclasses field)
    or a class body boundary rules it out.
    """
    current = node

    while current.parent is not None:
        parent = current.parent

        if parent.child_by_field_name(superclass_field) == current:
            return True

        if parent.type == "class_definition":
            return False

        current = parent

    return False


def in_implements_clause(node: Node, profile: LanguageProfile) -> bool:
    parent = _skip_type_list(node.parent)

    return parent is not None and parent.type in profile.implements_parents


def _skip_type_list(node: Node | None) -> Node | None:
    """Java wraps multi-name heritage lists (`implements A, B`) in an
    intermediate `type_list` node; climb past it to reach the clause."""
    if node is not None and node.type == "type_list":
        return node.parent

    return node


def is_call_target(node: Node, profile: LanguageProfile) -> bool:
    parent = node.parent

    return (
        parent is not None
        and parent.type == profile.call_parent
        and parent.child_by_field_name(profile.call_function_field) == node
    )
