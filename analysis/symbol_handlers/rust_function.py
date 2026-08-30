from tree_sitter import Node

from analysis.symbol_builder import build_symbol
from models.entities.documents import Document
from models.entities.symbol_kind import SymbolKind
from models.entities.symbols import Symbol
from parsing.node_text import node_text


def handle_rust_function(
    *,
    node: Node,
    document: Document,
    owner: Symbol | None,
) -> Symbol | None:
    """`fn name(...)` and `fn name(...);` (trait method signatures).

    Rust has one node type for both free functions and impl/trait
    methods; `impl` blocks are standalone top-level nodes rather than
    the method's owner (see `analysis.languages` docstring on
    `impl_node`), so methods inside them carry no owner symbol -- the
    same shape Go's top-level, receiver-based methods already have.
    Kind is decided structurally instead: an ancestor `impl_item`, or an
    owning trait symbol, both mean METHOD.
    """
    name_node = node.child_by_field_name("name")

    if name_node is None:
        return None

    kind = SymbolKind.METHOD if _is_method(node, owner) else SymbolKind.FUNCTION

    return build_symbol(
        node=node,
        name=node_text(name_node),
        kind=kind,
        document=document,
        owner=owner,
    )


def _is_method(node: Node, owner: Symbol | None) -> bool:
    if owner is not None and owner.kind == SymbolKind.INTERFACE:
        return True

    parent = node.parent

    return (
        parent is not None
        and parent.type == "declaration_list"
        and parent.parent is not None
        and parent.parent.type == "impl_item"
    )
