from tree_sitter import Node, Tree

from analysis.handlers.function import handle_function
from analysis.registry import NODE_HANDLERS
from models.document import Document
from models.symbol import Symbol


def extract_symbols(
    tree: Tree,
    document: Document,
) -> list[Symbol]:
    symbols: list[Symbol] = []

    walk(
        node=tree.root_node,
        document=document,
        symbols=symbols,
    )

    return symbols


def walk(
    node: Node,
    document: Document,
    symbols: list[Symbol],
):
    visit(
        node=node,
        document=document,
        symbols=symbols,
    )

    for child in node.children:
        walk(
            node=child,
            document=document,
            symbols=symbols,
        )


def visit(
    node: Node,
    document: Document,
    symbols: list[Symbol],
):
    handler = NODE_HANDLERS.get(node.type)

    if handler is None:
        return

    symbol = handle_function(
        node=node,
        document=document,
    )

    if symbol is not None:
        symbols.append(symbol)
