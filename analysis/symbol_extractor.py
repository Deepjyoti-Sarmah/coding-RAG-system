from tree_sitter import Node, Tree

from analysis.registry import NODE_HANDLERS
from models.document import Document
from models.symbol import Symbol
from models.symbol_kind import SymbolKind


def extract_symbols(
    tree: Tree,
    document: Document,
) -> list[tuple[Symbol, Node]]:
    results: list[tuple[Symbol, Node]] = []

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
    results: list[tuple[Symbol, Node]],
    current_owner: Symbol | None,
):
    symbol = visit(
        node=node,
        document=document,
    )

    if symbol is not None:
        if current_owner is not None:
            symbol.parent_symbol_id = current_owner.symbol_id

        results.append((symbol, node))

    if symbol and symbol.kind in (SymbolKind.CLASS, SymbolKind.FUNCTION):
        next_owner = symbol
    else:
        next_owner = current_owner

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
) -> Symbol | None:
    handler = NODE_HANDLERS.get(node.type)

    if handler is None:
        return

    symbol = handler(
        node=node,
        document=document,
    )

    return symbol
