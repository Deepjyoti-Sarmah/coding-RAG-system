from tree_sitter import Node, Tree

from analysis.registry import SymbolHandler, symbol_handlers_for
from models.entities.documents import Document
from models.entities.symbols import Symbol
from models.extracted_symbol import ExtractedSymbol


def extract_symbols(
    *,
    tree: Tree,
    document: Document,
) -> list[ExtractedSymbol]:
    results: list[ExtractedSymbol] = []
    handlers = symbol_handlers_for(document.language)

    walk(
        node=tree.root_node,
        document=document,
        results=results,
        current_owner=None,
        handlers=handlers,
    )

    return results


def walk(
    node: Node,
    document: Document,
    results: list[ExtractedSymbol],
    current_owner: Symbol | None,
    handlers: dict[str, SymbolHandler],
):
    symbol = visit(
        node=node,
        document=document,
        owner=current_owner,
        handlers=handlers,
    )

    if symbol is not None:
        results.append(
            ExtractedSymbol(
                symbol=symbol,
                node=node,
                language=document.language,
            )
        )

    next_owner = symbol or current_owner

    for child in node.children:
        walk(
            node=child,
            document=document,
            results=results,
            current_owner=next_owner,
            handlers=handlers,
        )


def visit(
    node: Node,
    document: Document,
    owner: Symbol | None,
    handlers: dict[str, SymbolHandler],
) -> Symbol | None:
    handler = handlers.get(node.type)

    if handler is None:
        return None

    return handler(
        node=node,
        document=document,
        owner=owner,
    )
