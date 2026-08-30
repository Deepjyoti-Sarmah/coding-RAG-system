from tree_sitter import Node

from analysis.export_builder import build_export
from models.entities.documents import Document
from models.entities.exports import Export


def handle_rust_exports(
    *,
    node: Node,
    document: Document,
) -> list[Export] | None:
    """`pub` items are Rust's export surface. `pub(crate)` and other
    restricted-visibility forms are treated as not exported in v1 --
    they are visible only within the crate, which this single-crate
    model has no boundary for.
    """
    name_node = node.child_by_field_name("name")

    if name_node is None or name_node.text is None:
        return None

    if not _is_pub(node):
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


def _is_pub(node: Node) -> bool:
    modifier = next(
        (child for child in node.children if child.type == "visibility_modifier"),
        None,
    )

    if modifier is None:
        return False

    return modifier.text == b"pub"
