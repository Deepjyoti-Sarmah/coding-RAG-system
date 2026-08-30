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
    if name is None:
        return None
    text = node_text(name)
    return text.split("::")[-1]


def callable_qualifier(node: Node) -> str | None:
    declarator = function_declarator(node)
    if declarator is None:
        return None
    name = declarator.child_by_field_name("declarator") or declarator.child_by_field_name("name")
    if name is None:
        for child in declarator.children:
            if child.type in ("qualified_identifier", "destructor_name"):
                name = child
                break
    if name is None:
        return None
    text = node_text(name)
    if "::" not in text:
        return None
    return text.rsplit("::", 1)[0]


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
    qualifier = callable_qualifier(node)
    qualified = None
    if qualifier is not None:
        owner_prefix = owner.qualified_name + "." if owner is not None else ""
        qualified = qualifier.replace("::", ".")
        if owner_prefix and not qualified.startswith(owner_prefix):
            qualified = owner_prefix + qualified
        qualified += "." + name
    kind = SymbolKind.METHOD if qualifier is not None else SymbolKind.FUNCTION
    return build_symbol(node=node, name=name, kind=kind, document=document,
                        owner=owner, identity_discriminator=callable_identity(node),
                        qualified_name_override=qualified)


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
