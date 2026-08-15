from tree_sitter import Node

from analysis.export_builder import build_export
from models.entities.documents import Document
from models.entities.exports import Export


def handle_export_specifier(
    *,
    node: Node,
    document: Document,
) -> list[Export] | None:

    if node.type != "export_specifier":
        return None

    statement = _enclosing_export_statement(node)

    if statement is None:
        return None

    # export { a } from "./x" — deferred re-export
    if statement.child_by_field_name("source") is not None:
        return None

    identifiers = [child for child in node.children if child.type == "identifier"]

    if len(identifiers) == 1:
        name = identifiers[0].text.decode("utf-8")
        exported_name = name
        symbol_name = name
    elif len(identifiers) == 2:
        symbol_name = identifiers[0].text.decode("utf-8")
        exported_name = identifiers[1].text.decode("utf-8")
    else:
        return None

    return [
        build_export(
            document=document,
            exported_name=exported_name,
            symbol_name=symbol_name,
            node=node,
        )
    ]


def _enclosing_export_statement(node: Node) -> Node | None:
    current = node.parent

    while current is not None:
        if current.type == "export_statement":
            return current

        current = current.parent

    return None
