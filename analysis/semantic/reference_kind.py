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

    if _in_type_annotation(node):
        return ReferenceKind.HAS_TYPE

    if _in_return_type(node):
        return ReferenceKind.RETURNS

    return ReferenceKind.IDENTIFIER


def _in_type_annotation(node: Node) -> bool:
    """True if node is inside a type_annotation / type field (e.g. `x: Type`)."""
    p = node.parent
    while p is not None:
        if p.type in ("type_annotation", "type_alias", "type", "typed_parameter"):
            return True
        if p.child_by_field_name("type") == node:
            return True
        # e.g. variable_declarator with type: `const x: MyType`
        if p.type in ("variable_declarator", "lexical_declaration", "formal_parameters"):
            # check if any descendant is this node via type field
            pass
        p = p.parent
    # direct parent field check for common TS patterns
    parent = node.parent
    if parent is not None and parent.child_by_field_name("type") == node:
        return True
    return False


def _in_return_type(node: Node) -> bool:
    p = node.parent
    while p is not None:
        if p.type == "return_type" or p.child_by_field_name("return_type") == p:
            return True
        # function_declaration -> return_type field
        if p.child_by_field_name("return_type") is not None:
            # check if node's ancestor is that return_type
            rt = p.child_by_field_name("return_type")
            cur: Node | None = node
            while cur is not None and cur != p:
                if cur == rt or (rt is not None and _is_descendant(cur, rt)):
                    return True
                cur = cur.parent
        p = p.parent
    return False


def _is_descendant(node: Node, ancestor: Node) -> bool:
    cur: Node | None = node
    while cur is not None:
        if cur == ancestor:
            return True
        cur = cur.parent
    return False


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
