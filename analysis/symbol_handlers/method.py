from tree_sitter import Node
from analysis.symbol_builder import build_symbol
from models.document import Document
from models.symbol import Symbol
from models.symbol_kind import SymbolKind


def handle_method(
    node: Node,
    document: Document,
    owner: Symbol | None,
) -> Symbol | None:

    name_node = node.child_by_field_name("name")

    if not name_node:
        return None

    name: str = name_node.text.decode("utf-8")

    return build_symbol(
        node=node,
        name=name,
        kind=SymbolKind.METHOD,
        document=document,
        owner=owner,
    )
