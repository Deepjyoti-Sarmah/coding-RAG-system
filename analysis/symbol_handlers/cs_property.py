from tree_sitter import Node

from analysis.symbol_builder import build_symbol
from models.entities.documents import Document
from models.entities.symbol_kind import SymbolKind
from models.entities.symbols import Symbol
from parsing.node_text import node_text


def handle_cs_property(
    *,
    node: Node,
    document: Document,
    owner: Symbol | None,
) -> Symbol | None:
    """`public string Name { get; set; }`. No PROPERTY kind exists;
    VARIABLE is the closest fit, matching how Java fields are mapped."""
    name_node = node.child_by_field_name("name")

    if name_node is None:
        return None

    return build_symbol(
        node=node,
        name=node_text(name_node),
        kind=SymbolKind.VARIABLE,
        document=document,
        owner=owner,
    )


def handle_cs_field(
    *,
    node: Node,
    document: Document,
    owner: Symbol | None,
) -> Symbol | None:
    for child in node.children:
        if child.type != "variable_declaration":
            continue

        for declarator in child.children:
            if declarator.type != "variable_declarator":
                continue

            name_node = declarator.child_by_field_name("name")

            if name_node is None:
                continue

            return build_symbol(
                node=declarator,
                name=node_text(name_node),
                kind=SymbolKind.VARIABLE,
                document=document,
                owner=owner,
            )

    return None
