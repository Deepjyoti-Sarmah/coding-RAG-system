"""Interface member handler: property_signature / method_signature inside interface."""

from tree_sitter import Node

from analysis.symbol_builder import build_symbol
from models.entities.documents import Document
from models.entities.symbol_kind import SymbolKind
from models.entities.symbols import Symbol
from parsing.node_text import node_text


def handle_property_signature(*, node: Node, document: Document, owner: Symbol | None) -> Symbol | None:
    if node.type != "property_signature":
        return None
    name = node.child_by_field_name("name")
    if name is None:
        # fallback: first identifier child
        for c in node.children:
            if c.type == "property_identifier":
                name = c
                break
    if name is None:
        return None
    return build_symbol(node=node, name=node_text(name), kind=SymbolKind.VARIABLE, document=document, owner=owner)


def handle_method_signature(*, node: Node, document: Document, owner: Symbol | None) -> Symbol | None:
    if node.type != "method_signature":
        return None
    name = node.child_by_field_name("name")
    if name is None:
        for c in node.children:
            if c.type == "property_identifier":
                name = c
                break
    if name is None:
        return None
    return build_symbol(node=node, name=node_text(name), kind=SymbolKind.METHOD, document=document, owner=owner)
