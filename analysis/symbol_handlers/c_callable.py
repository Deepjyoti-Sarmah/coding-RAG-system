from tree_sitter import Node

from analysis.symbol_builder import build_symbol
from models.entities.documents import Document
from models.entities.symbol_kind import SymbolKind
from models.entities.symbols import Symbol
from parsing.node_text import node_text


def function_declarator(node: Node) -> Node | None:
    if node.type in ("function_declarator", "pointer_declarator"):
        nested = node.child_by_field_name("declarator")
        if nested is not None and nested.type == "function_declarator":
            return nested
        if node.type == "function_declarator":
            return node
    for child in node.children:
        found = function_declarator(child)
        if found is not None:
            return found
    return None


def callable_name(node: Node) -> str | None:
    declarator = function_declarator(node)
    if declarator is None:
        return None
    name = declarator.child_by_field_name("declarator") or declarator.child_by_field_name("name")
    if name is None:
        for child in declarator.children:
            if child.type in ("identifier", "field_identifier", "destructor_name", "qualified_identifier"):
                name = child
                break
    return node_text(name) if name is not None else None


def callable_identity(node: Node) -> str:
    declarator = function_declarator(node)
    if declarator is None:
        return "arity:0"
    parameters = declarator.child_by_field_name("parameters")
    if parameters is None:
        return "arity:0"
    values = [node_text(child).strip() for child in parameters.children
              if child.type not in {"(", ")", ","}]
    return "params:" + ",".join(values)


def handle_function(*, node: Node, document: Document, owner: Symbol | None) -> Symbol | None:
    name = callable_name(node)
    if name is None:
        return None
    return build_symbol(node=node, name=name, kind=SymbolKind.FUNCTION, document=document,
                        owner=owner, identity_discriminator=callable_identity(node))


def handle_method(*, node: Node, document: Document, owner: Symbol | None) -> Symbol | None:
    name = callable_name(node)
    if name is None:
        return None
    return build_symbol(node=node, name=name, kind=SymbolKind.METHOD, document=document,
                        owner=owner, identity_discriminator=callable_identity(node))


def handle_declaration(*, node: Node, document: Document, owner: Symbol | None) -> Symbol | None:
    name = callable_name(node)
    if name is None:
        return None
    kind = SymbolKind.METHOD if owner is not None and owner.kind == SymbolKind.CLASS else SymbolKind.FUNCTION
    return build_symbol(node=node, name=name, kind=kind, document=document, owner=owner,
                        identity_discriminator=callable_identity(node))
