from tree_sitter import Node

from analysis.symbol_builder import build_symbol
from models.entities.documents import Document
from models.entities.symbol_kind import SymbolKind
from models.entities.symbols import Symbol
from parsing.node_text import node_text


def handle_rust_mod(
    *,
    node: Node,
    document: Document,
    owner: Symbol | None,
) -> Symbol | None:
    """Inline `mod name { ... }` only; file-backed modules (`mod name;`)
    have no body node here and are handled by path resolution instead."""
    name_node = node.child_by_field_name("name")

    if name_node is None:
        return None

    return build_symbol(
        node=node,
        name=node_text(name_node),
        kind=SymbolKind.MODULE,
        document=document,
        owner=owner,
    )
