from tree_sitter import Node

from analysis.symbol_builder import build_symbol
from models.entities.document import Document
from models.entities.symbol import Symbol
from models.entities.symbol_kind import SymbolKind


def handle_varibale_declarator(
    *,
    node: Node,
    document: Document,
    owner: Symbol | None,
) -> Symbol | None:

    if not _is_module_scoped(node):
        return None

    name_node = node.child_by_field_name("name")

    if name_node is None:
        return None

    # Skip destructuring like const { a, b } = x — no searchable name
    if name_node.type in ("object_pattern", "array_pattern"):
        return None

    value_node = node.child_by_field_name("value")

    if value_node is None:
        return None

    if value_node.type in ("arrow_function", "function_expression"):
        kind = SymbolKind.FUNCTION
    else:
        kind = SymbolKind.VARIABLE

    name: str = name_node.text.decode("utf-8")

    return build_symbol(
        node=node,
        name=name,
        kind=kind,
        document=document,
        owner=owner,
    )


def _is_module_scoped(node: Node) -> bool:
    # always lexical_declaration
    parent = node.parent
    if parent is None:
        return False

    # this actully differs
    grandparent = parent.parent
    if grandparent is None:
        return False

    if grandparent.type in ("program", "export_statement"):
        return True

    return False
