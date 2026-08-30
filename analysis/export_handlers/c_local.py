from tree_sitter import Node

from analysis.export_builder import build_export
from analysis.symbol_handlers.c_callable import callable_name
from models.entities.documents import Document
from models.entities.exports import Export


def handle_c_export(*, node: Node, document: Document) -> list[Export] | None:
    name = node.child_by_field_name("name")
    if name is None and node.type in ("declaration", "function_definition"):
        raw_name = callable_name(node)
        if raw_name is not None:
            return [build_export(document=document, exported_name=raw_name,
                                 symbol_name=raw_name, node=node)]
    if name is None:
        for child in node.children:
            if child.type in ("identifier", "type_identifier", "field_identifier"):
                name = child
                break
    if name is None or name.text is None:
        return None
    return [build_export(document=document, exported_name=name.text.decode("utf-8"),
                         symbol_name=name.text.decode("utf-8"), node=node)]
