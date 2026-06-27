from tree_sitter import Node, Tree

from analysis.handlers.function import handle_function
from analysis.registry import NODE_HANDLERS
from models.document import Document
from models.symbol import Symbol


def extract_symbols(
    tree: Tree,
    document: Document,
) -> list[tuple[Symbol, Node]]:
    results: list[tuple[Symbol, Node]] = []

    walk(
        node=tree.root_node,
        document=document,
        results=results,
    )

    return results


def walk(
    node: Node,
    document: Document,
    results: list[tuple[Symbol, Node]],
):
    visit(
        node=node,
        document=document,
        results=results,
    )

    for child in node.children:
        walk(
            node=child,
            document=document,
            results=results,
        )


def visit(
    node: Node,
    document: Document,
    results: list[tuple[Symbol, Node]],
):
    handler = NODE_HANDLERS.get(node.type)

    if handler is None:
        return

    symbol = handler(
        node=node,
        document=document,
    )

    if symbol is not None:
        results.append((symbol, node))
