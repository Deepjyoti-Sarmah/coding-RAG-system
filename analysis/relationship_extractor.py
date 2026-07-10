from tree_sitter import Node

from analysis.relationship_registry import RELATIONSHIP_HANDLER
from analysis.semantic.create_symbol import creates_symbol
from indexing.symbol_index import SymbolIndex
from models.entities.symbol import Symbol
from models.relationships.relationship import Relationship


def extract_relationship(
    *,
    symbol: Symbol,
    symbol_node: Node,
    symbol_index: SymbolIndex,
) -> list[Relationship]:

    relationships: list[Relationship] = []

    walk(
        node=symbol_node,
        root_node=symbol_node,
        current_symbol=symbol,
        symbol_index=symbol_index,
        relationships=relationships,
    )

    return relationships


def walk(
    *,
    node: Node,
    root_node: Node,
    current_symbol: Symbol,
    symbol_index: SymbolIndex,
    relationships: list[Relationship],
):
    # Entered another symbol's ownership boundary
    if node != root_node and creates_symbol(node):
        return

    hander = RELATIONSHIP_HANDLER.get(node.type)

    if hander is not None:
        hander(
            node=node,
            current_symbol=current_symbol,
            symbol_index=symbol_index,
            relationships=relationships,
        )

    for child in node.children:
        walk(
            node=child,
            root_node=root_node,
            current_symbol=current_symbol,
            symbol_index=symbol_index,
            relationships=relationships,
        )
