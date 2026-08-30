from tree_sitter import Node

from analysis.symbol_builder import build_symbol
from models.entities.documents import Document
from models.entities.symbol_kind import SymbolKind
from models.entities.symbols import Symbol
from parsing.node_text import node_text


def handle_java_method(
    *,
    node: Node,
    document: Document,
    owner: Symbol | None,
) -> Symbol | None:
    """`method_declaration` and `constructor_declaration`.

    Constructors have an empty `name` field; the class name
    lives in `identifier`.  Owner (class vs interface) drives
    the kind assignment.
    """
    if owner is not None and owner.kind == SymbolKind.CLASS:
        kind = SymbolKind.METHOD
    elif owner is not None and owner.kind == SymbolKind.INTERFACE:
        kind = SymbolKind.METHOD
    else:
        kind = SymbolKind.FUNCTION

    if node.type == "constructor_declaration":
        name_node = node.child_by_field_name("identifier")
    else:
        name_node = node.child_by_field_name("name")

    if name_node is None or not name_node.text:
        return None

    return build_symbol(
        node=node,
        name=node_text(name_node),
        kind=kind,
        document=document,
        owner=owner,
    )
