from tree_sitter import Node

from analysis.symbol_builder import build_symbol
from models.document import Document
from models.symbol import Symbol
from models.symbol_kind import SymbolKind


def handle_function(
    node: Node,
    document: Document,
) -> Symbol | None:

    name = node.child_by_field_name("name")

    if name is None:
        return None

    return build_symbol(
        node=node,
        name=name.text.decode(),
        kind=SymbolKind.FUNCTION,
        document=document,
    )
