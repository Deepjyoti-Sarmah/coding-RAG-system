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

    if node.type not in ("identifier", "property_identifier"):
        return None

    if is_declaration_name(node):
        return None

    kind = determine_reference_kind(node)

    return build_reference(
        node=node,
        kind=kind,
        owner_symbol=owner_symbol,
    )
