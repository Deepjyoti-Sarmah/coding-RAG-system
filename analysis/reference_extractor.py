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

    reference = visit(
        node=node,
        owner_symbol=owner_symbol,
        profile=profile,
    )

    if reference is not None:
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

    # A type_identifier is extracted only in a heritage clause. Type
    # positions elsewhere (annotations, generics) have no resolvable
    # target yet, and extracting them would flood the resolver with
    # references it can only mark unresolved.
    if node.type in profile.heritage_only_nodes:
        if not in_heritage_clause(node, profile):
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
        path=(name,),
        kind=kind,
        owner_symbol=owner_symbol,
    )


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
