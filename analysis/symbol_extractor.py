from tree_sitter import Node, Tree

from analysis.registry import NODE_HANDLERS
from models.entities.document import Document
from models.entities.symbol import Symbol


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
        owner=current_owner,
    )

    if symbol is not None:
        results.append((symbol, node))

    next_owner = symbol or current_owner

    for child in node.children:
        walk(
            node=child,
            document=document,
            results=results,
            current_owner=next_owner,
        )


def visit(node: Node, document: Document, owner: Symbol | None) -> Symbol | None:
    handler = NODE_HANDLERS.get(node.type)

    if handler is None:
        return

    symbol = handler(
        node=node,
        document=document,
        owner=owner,
    )

    return symbol
