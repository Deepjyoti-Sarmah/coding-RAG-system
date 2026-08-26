from tree_sitter import Node

from analysis.symbol_builder import build_symbol
from models.entities.documents import Document
from models.entities.symbol_kind import SymbolKind
from models.entities.symbols import Symbol


def handle_go_function(
    *,
    node: Node,
    document: Document,
    owner: Symbol | None,
) -> Symbol | None:
    """Top-level `func name(...)`. Generic type parameters live in a
    separate field and do not affect the declared name."""
    return _named_symbol(node, document, owner, SymbolKind.FUNCTION)


def handle_go_method(
    *,
    node: Node,
    document: Document,
    owner: Symbol | None,
) -> Symbol | None:
    """`func (r *Type) Name(...)` — methods are top-level in Go's AST."""
    return _named_symbol(node, document, owner, SymbolKind.METHOD)


def handle_go_type_spec(
    *,
    node: Node,
    document: Document,
    owner: Symbol | None,
) -> Symbol | None:
    """`type Name struct {...}` / `type Name interface {...}` as classes.

    Non-structural types (aliases, named primitives) are skipped.
    """
    type_node = node.child_by_field_name("type")

    if type_node is None or type_node.type not in (
        "struct_type",
        "interface_type",
    ):
        return None

    return _named_symbol(node, document, owner, SymbolKind.CLASS)


def _named_symbol(
    node: Node,
    document: Document,
    owner: Symbol | None,
    kind: SymbolKind,
) -> Symbol | None:
    name_node = node.child_by_field_name("name")
    raw_name = name_node.text if name_node is not None else None

    if raw_name is None:
        return None

    return build_symbol(
        node=node,
        name=raw_name.decode("utf-8"),
        kind=kind,
        document=document,
        owner=owner,
    )
