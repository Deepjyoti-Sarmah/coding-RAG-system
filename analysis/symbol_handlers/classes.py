from tree_sitter import Node

from analysis.symbol_builder import build_symbol
from models.entities.documents import Document
from models.entities.symbol_kind import SymbolKind
from models.entities.symbols import Symbol
from parsing.node_text import node_text


def handle_class(
    *,
    node: Node,
    document: Document,
    owner: Symbol | None,
) -> Symbol | None:

    name = node.child_by_field_name("name")

    if name is None:
        return None

    return build_symbol(
        node=node,
        name=node_text(name),
        kind=SymbolKind.CLASS,
        document=document,
        owner=owner,
    )
