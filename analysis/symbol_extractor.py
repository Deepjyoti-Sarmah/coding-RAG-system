from tree_sitter import Node, Tree

from analysis.registry import NODE_HANDLERS
from models.entities.documents import Document
from models.entities.symbols import Symbol
from models.extracted_symbol import ExtractedSymbol


def extract_symbols(
    *,
    tree: Tree,
    document: Document,
) -> list[ExtractedSymbol]:
    results: list[ExtractedSymbol] = []

    walk(
        node=tree.root_node,
        document=document,
        results=results,
        current_owner=None,
    )

    return results


def walk(
    node: Node,
    document: Document,
    results: list[ExtractedSymbol],
    current_owner: Symbol | None,
):
    symbol = visit(
        node=node,
        document=document,
        owner=current_owner,
    )

    if symbol is not None:
        results.append(
            ExtractedSymbol(
                symbol=symbol,
                node=node,
            )
        )

    next_owner = symbol or current_owner

    for child in node.children:
        walk(
            node=child,
            document=document,
            results=results,
            current_owner=next_owner,
        )


def visit(
    node: Node,
    document: Document,
    owner: Symbol | None,
) -> Symbol | None:
    handler = NODE_HANDLERS.get(node.type)

    if handler is None:
        return

    symbol = handler(
        node=node,
        document=document,
        owner=owner,
    )

    return symbol
