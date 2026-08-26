from tree_sitter import Node

from analysis.export_builder import build_export
from models.entities.documents import Document
from models.entities.exports import Export


def handle_go_exports(
    *,
    node: Node,
    document: Document,
) -> list[Export] | None:
    """Go's visibility rule is lexical: an uppercase-initial name is
    exported. Applies to top-level functions, types, and methods.
    """
    name_node = node.child_by_field_name("name")
    raw_name = name_node.text if name_node is not None else None

    if raw_name is None:
        return None

    name = raw_name.decode("utf-8")

    if not name[:1].isupper():
        return None

    return [
        build_export(
            document=document,
            exported_name=name,
            symbol_name=name,
            node=node,
        )
    ]
