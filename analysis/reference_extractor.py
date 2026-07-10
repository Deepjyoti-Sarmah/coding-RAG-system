from tree_sitter import Node

from analysis.reference_builder import build_reference
from analysis.semantic.is_declaration_name import is_declaration_name
from models.entities.reference import Reference
from models.entities.symbol import Symbol


def extract_references(
    *,
    owner_symbol: Symbol,
    owner_node: Node,
) -> list[Reference]:
    results: list[Reference] = []

    walk(
        node=owner_node,
        owner_symbol=owner_symbol,
        results=results,
    )

    return results


def walk(
    *,
    node: Node,
    owner_symbol: Symbol,
    results: list[Reference],
):

    reference = visit(
        node=node,
        owner_symbol=owner_symbol,
    )

    if reference is not None:
        results.append(reference)

    for child in node.children:
        walk(
            node=child,
            results=results,
            owner_symbol=owner_symbol,
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

    return build_reference(
        node=node,
        owner_symbol=owner_symbol,
    )
