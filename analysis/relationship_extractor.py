from tree_sitter import Node

from analysis.handlers.call import handle_call
from indexing.symbol_index import SymbolIndex
from models.relationship import Relationship
from models.symbol import Symbol


def extract_relationship(
    symbol: Symbol,
    symbol_node: Node,
    symbol_index: SymbolIndex,
) -> list[Relationship]:

    relationships: list[Relationship] = []

    walk(
        node=symbol_node,
        current_symbol=symbol,
        symbol_index=symbol_index,
        relationships=relationships,
    )

    return relationships


def walk(
    node: Node,
    current_symbol: Symbol,
    symbol_index: SymbolIndex,
    relationships: list[Relationship],
):
    if node.type == "call_expression":
        handle_call(
            node,
            current_symbol,
            symbol_index,
            relationships,
        )

    for child in node.children:
        walk(
            child,
            current_symbol,
            symbol_index,
            relationships,
        )
