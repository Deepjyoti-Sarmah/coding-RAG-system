from tree_sitter import Node
from analysis.symbol_builder import build_symbol
from models.document import Document
from models.symbol import Symbol
from models.symbol_kind import SymbolKind


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
        name=name.text.decode(),
        kind=SymbolKind.CLASS,
        document=document,
        owner=owner,
    )
