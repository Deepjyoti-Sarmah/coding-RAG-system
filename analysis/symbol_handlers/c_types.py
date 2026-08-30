from tree_sitter import Node

from analysis.symbol_builder import build_symbol
from models.entities.documents import Document
from models.entities.symbol_kind import SymbolKind
from models.entities.symbols import Symbol
from parsing.node_text import node_text


def _name(node: Node) -> str | None:
    named = node.child_by_field_name("name")
    if named is not None:
        return node_text(named)
    for child in node.children:
        if child.type in ("type_identifier", "identifier", "field_identifier"):
            return node_text(child)
    return None


def handle_type(*, node: Node, document: Document, owner: Symbol | None) -> Symbol | None:
    name = _name(node)
    if name is None:
        return None
    kind = SymbolKind.TYPE_ALIAS if node.type == "type_definition" else SymbolKind.CLASS
    return build_symbol(node=node, name=name, kind=kind, document=document, owner=owner)


def handle_namespace(*, node: Node, document: Document, owner: Symbol | None) -> Symbol | None:
    name = _name(node) or "(anonymous)"
    return build_symbol(node=node, name=name, kind=SymbolKind.MODULE, document=document, owner=owner)


def handle_variable(*, node: Node, document: Document, owner: Symbol | None) -> Symbol | None:
    name = _name(node)
    if name is None:
        return None
    return build_symbol(node=node, name=name, kind=SymbolKind.VARIABLE, document=document, owner=owner)
