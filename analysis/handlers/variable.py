from symtable import Symbol

from tree_sitter import Node
from models.document import Document
from models.symbol_kind import SymbolKind


def handle_varibale_declarator(*, node: Node, document: Document) -> Symbol | None:

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
        return SymbolKind.FUNCTION
    else:
        return SymbolKind.VARIABLE

    return None


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
