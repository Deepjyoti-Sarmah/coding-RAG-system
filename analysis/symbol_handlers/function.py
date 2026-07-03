from tree_sitter import Node

from analysis.symbol_builder import build_symbol
from models.document import Document
from models.symbol import Symbol
from models.symbol_kind import SymbolKind


def handle_function(
    *,
    node: Node,
    document: Document,
    owner: Symbol | None,
) -> Symbol | None:

    name_node = node.child_by_field_name("name")

    if name_node is None:
        return None

    name: str = name_node.text.decode("utf-8")

    return build_symbol(
        node=node,
        name=name,
        kind=SymbolKind.FUNCTION,
        document=document,
        owner=owner,
    )
