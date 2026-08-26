from tree_sitter import Node

from analysis.symbol_builder import build_symbol
from models.entities.documents import Document
from models.entities.symbol_kind import SymbolKind
from models.entities.symbols import Symbol


def handle_python_function(
    *,
    node: Node,
    document: Document,
    owner: Symbol | None,
) -> Symbol | None:
    """`function_definition` doubles as method when nested in a class."""
    name_node = node.child_by_field_name("name")

    if name_node is None:
        return None

    raw_name = name_node.text

    if raw_name is None:
        return None

    is_method = owner is not None and owner.kind == SymbolKind.CLASS

    return build_symbol(
        node=node,
        name=raw_name.decode("utf-8"),
        kind=SymbolKind.METHOD if is_method else SymbolKind.FUNCTION,
        document=document,
        owner=owner,
    )

