from tree_sitter import Node

from analysis.languages import LanguageProfile
from analysis.reference_builder import build_reference
from analysis.semantic.create_symbol import creates_symbol
from analysis.semantic.is_declaration_name import is_declaration_name
from analysis.semantic.reference_kind import (
    determine_reference_kind,
    in_extends_clause,
    in_implements_clause,
)
from models.entities.references import Reference
from models.entities.symbols import Symbol
from parsing.node_text import node_text


def extract_references(
    *,
    owner_symbol: Symbol,
    owner_node: Node,
    profile: LanguageProfile,
) -> list[Reference]:
    results: list[Reference] = []

    walk(
        node=owner_node,
        root_node=owner_node,
        owner_symbol=owner_symbol,
        results=results,
        profile=profile,
    )

    return results


def walk(
    *,
    node: Node,
    root_node: Node,
    owner_symbol: Symbol,
    results: list[Reference],
    profile: LanguageProfile,
):
    # Entered another symbol's ownership boundary
    if node != root_node and creates_symbol(node, profile.symbol_handlers):
        return

    # Volume guard for type refs before visiting
    if node.type in profile.heritage_only_nodes:
        from analysis.semantic.reference_kind import _in_return_type, _in_type_annotation
        from models.entities.reference_kind import ReferenceKind

        # quick check to avoid creating 100s of type refs
        if not in_heritage_clause(node, profile) and not (_in_type_annotation(node) or _in_return_type(node)):
            # not in any allowed position -> skip quickly, but still walk children
            pass
        elif not in_heritage_clause(node, profile):
            type_count = sum(1 for r in results if getattr(r, "kind", None) in (ReferenceKind.HAS_TYPE, ReferenceKind.RETURNS, "has_type", "returns"))
            if type_count >= 20:
                return

    reference = visit(
        node=node,
        owner_symbol=owner_symbol,
        profile=profile,
    )

    if reference is not None:
        # second guard after kind determined
        from models.entities.reference_kind import ReferenceKind as RK

        if getattr(reference, "kind", None) in (RK.HAS_TYPE, RK.RETURNS):
            existing = sum(1 for r in results if getattr(r, "kind", None) in (RK.HAS_TYPE, RK.RETURNS))
            if existing >= 20:
                return
        results.append(reference)

    # A member expression is represented atomically by its access path;
    # the object and property parts are not separate references.
    if node.type == profile.member_node:
        return

    for child in node.children:
        walk(
            node=child,
            root_node=root_node,
            owner_symbol=owner_symbol,
            results=results,
            profile=profile,
        )


def visit(
    *,
    node: Node,
    owner_symbol: Symbol,
    profile: LanguageProfile,
) -> Reference | None:

    if node.type == profile.member_node:
        path = build_member_path(node, profile)
        kind = determine_reference_kind(node, profile)

        return build_reference(
            node=node,
            path=path,
            kind=kind,
            owner_symbol=owner_symbol,
        )

    # type_identifier extraction policy moved to walk() guard above; here just check identifier set
    if node.type in profile.heritage_only_nodes:
        if not in_heritage_clause(node, profile):
            from analysis.semantic.reference_kind import _in_return_type, _in_type_annotation

            if not (_in_type_annotation(node) or _in_return_type(node)):
                return None

    elif node.type not in profile.identifier_nodes:
        return None

    # Object/property parts of member expressions are covered by the
    # enclosing member_expression reference.
    if (
        node.parent is not None
        and node.parent.type == profile.member_node
    ):
        return None

    if is_declaration_name(node, profile):
        return None

    name = node_text(node)

    kind = determine_reference_kind(node, profile)

    return build_reference(
        node=node,
        path=call_target_path(node, name),
        kind=kind,
        owner_symbol=owner_symbol,
    )


def call_target_path(node: Node, name: str) -> tuple[str, ...]:
    """Java's `method_invocation` has no member-expression wrapper: a
    qualified call's object and method name are sibling fields on the
    call node itself, unlike JS/Go where the call's function field is a
    member/selector node. Recover the qualifier here so qualified calls
    resolve the same way member accesses do elsewhere.
    """
    parent = node.parent

    if parent is None:
        return (name,)

    object_node = parent.child_by_field_name("object")

    if object_node is None or object_node == node:
        return (name,)

    return (node_text(object_node), name)


def in_heritage_clause(node: Node, profile: LanguageProfile) -> bool:
    return in_extends_clause(node, profile) or in_implements_clause(
        node, profile
    )


def build_member_path(
    node: Node,
    profile: LanguageProfile,
) -> tuple[str, ...]:
    if node.type != profile.member_node:
        return (node_text(node),)

    object_node = node.child_by_field_name(profile.member_object_field)
    property_node = node.child_by_field_name(profile.member_property_field)

    if object_node is None or property_node is None:
        return (node_text(node),)

    if object_node.type == profile.member_node:
        return build_member_path(object_node, profile) + (
            node_text(property_node),
        )

    return (
        node_text(object_node),
        node_text(property_node),
    )
