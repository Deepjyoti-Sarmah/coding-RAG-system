from tree_sitter import Node

from analysis.reference_builder import build_reference
from analysis.semantic.create_symbol import creates_symbol
from analysis.semantic.is_declaration_name import is_declaration_name
from analysis.semantic.reference_kind import determine_reference_kind
from models.entities.references import Reference
from models.entities.symbols import Symbol


def extract_references(
    *,
    owner_symbol: Symbol,
    owner_node: Node,
) -> list[Reference]:
    results: list[Reference] = []

    walk(
        node=owner_node,
        root_node=owner_node,
        owner_symbol=owner_symbol,
        results=results,
    )

    return results


def walk(
    *,
    node: Node,
    root_node: Node,
    owner_symbol: Symbol,
    results: list[Reference],
):
    # Entered another symbol's ownership boundary
    if node != root_node and creates_symbol(node):
        return

    reference = visit(
        node=node,
        owner_symbol=owner_symbol,
    )

    if reference is not None:
        results.append(reference)

    # A member expression is represented atomically by its access path;
    # the object and property parts are not separate references.
    if node.type == "member_expression":
        return

    for child in node.children:
        walk(
            node=child,
            root_node=root_node,
            owner_symbol=owner_symbol,
            results=results,
        )


def visit(
    *,
    node: Node,
    owner_symbol: Symbol,
) -> Reference | None:

    if node.type == "member_expression":
        path = build_member_path(node)
        kind = determine_reference_kind(node)

        return build_reference(
            node=node,
            path=path,
            kind=kind,
            owner_symbol=owner_symbol,
        )

    if node.type not in ("identifier", "property_identifier"):
        return None

    # Object/property parts of member expressions are covered by the
    # enclosing member_expression reference.
    if node.parent is not None and node.parent.type == "member_expression":
        return None

    if is_declaration_name(node):
        return None

    name = node.text.decode("utf-8")

    kind = determine_reference_kind(node)

    return build_reference(
        node=node,
        path=(name,),
        kind=kind,
        owner_symbol=owner_symbol,
    )


def build_member_path(node: Node) -> tuple[str, ...]:
    if node.type != "member_expression":
        return (node.text.decode("utf-8"),)

    object_node = node.child_by_field_name("object")
    property_node = node.child_by_field_name("property")

    if object_node is None or property_node is None:
        return (node.text.decode("utf-8"),)

    if object_node.type == "member_expression":
        return build_member_path(object_node) + (
            property_node.text.decode("utf-8"),
        )

    return (
        object_node.text.decode("utf-8"),
        property_node.text.decode("utf-8"),
    )
