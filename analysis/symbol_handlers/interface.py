from tree_sitter import Node

from analysis.symbol_builder import build_symbol
from models.entities.documents import Document
from models.entities.symbol_kind import SymbolKind
from models.entities.symbols import Symbol
from parsing.node_text import node_text


def handle_interface(
    *,
    node: Node,
    document: Document,
    owner: Symbol | None,
) -> Symbol | None:

    name = node.child_by_field_name("name")

    if name is None:
        return None

    # Members are property_signature / method_signature nodes, which no
    # existing handler understands; they stay in the interface signature
    # rather than becoming half-extracted child symbols.
    # Now also indexed as child symbols for finer retrieval (kind=variable/method).
    symbol = build_symbol(
        node=node,
        name=node_text(name),
        kind=SymbolKind.INTERFACE,
        document=document,
        owner=owner,
    )
    return symbol
