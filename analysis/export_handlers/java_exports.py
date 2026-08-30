from tree_sitter import Node

from analysis.export_builder import build_export
from models.entities.documents import Document
from models.entities.exports import Export


def handle_java_exports(
    *,
    node: Node,
    document: Document,
) -> list[Export] | None:
    """Java has no export syntax; visibility is the closest analogue.

    A top-level type is part of the compilation unit's public surface
    only when explicitly marked `public` (the tree-sitter grammar calls
    this modifier out by name). Package-private (no modifier) top-level
    types are not resolvable from outside the package in v1, so they are
    not treated as exports.
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
    modifiers = next(
        (child for child in node.children if child.type == "modifiers"),
        None,
    )

    if modifiers is None:
        return False

    return any(child.type == "public" for child in modifiers.children)
