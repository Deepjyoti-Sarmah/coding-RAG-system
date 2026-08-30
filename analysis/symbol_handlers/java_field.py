from tree_sitter import Node

from analysis.symbol_builder import build_symbol
from models.entities.documents import Document
from models.entities.symbol_kind import SymbolKind
from models.entities.symbols import Symbol
from parsing.node_text import node_text


def handle_java_field(
    *,
    node: Node,
    document: Document,
    owner: Symbol | None,
) -> Symbol | None:
    for child in node.children:
        if child.type == "variable_declarator":
            name_node = child.child_by_field_name("name")

            if name_node is None or not name_node.text:
                continue

            return build_symbol(
                node=child,
                name=node_text(name_node),
                kind=SymbolKind.VARIABLE,
                document=document,
                owner=owner,
            )

    return None
