from tree_sitter import Node

from analysis.export_builder import build_export
from models.entities.documents import Document
from models.entities.exports import Export


def handle_cs_exports(
    *,
    node: Node,
    document: Document,
) -> list[Export] | None:
    """`public` types are C#'s export surface, same rule as Java.
    `internal` (the assembly-scoped default) is not exported in this
    single-assembly model, matching how Java's package-private default
    is not exported either.
    """
    name_node = node.child_by_field_name("name")

    if name_node is None or name_node.text is None:
        return None

    if not _is_public(node):
        return None

    name = name_node.text.decode("utf-8")

    return [
        build_export(
            document=document,
            exported_name=name,
            symbol_name=name,
            node=node,
        )
    ]


def _is_public(node: Node) -> bool:
    return any(
        child.type == "modifier" and child.text == b"public"
        for child in node.children
    )
