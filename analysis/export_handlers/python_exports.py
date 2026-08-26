from tree_sitter import Node

from analysis.export_builder import build_export
from models.entities.documents import Document
from models.entities.exports import Export


def handle_python_top_level(
    *,
    node: Node,
    document: Document,
) -> list[Export] | None:
    """Python has no `export` keyword: top-level defs and classes are
    the module's public surface. Nested definitions stay private.
    """
    if node.type not in ("function_definition", "class_definition"):
        return None

    if not _is_top_level(node):
        return None

    name = node.child_by_field_name("name")
    raw_name = name.text if name is not None else None

    if raw_name is None:
        return None

    return [
        build_export(
            document=document,
            exported_name=raw_name.decode("utf-8"),
            symbol_name=raw_name.decode("utf-8"),
            node=node,
        )
    ]


def _is_top_level(node: Node) -> bool:
    parent = node.parent

    # Decorated definitions wrap the actual def/class one level down.
    while parent is not None and parent.type == "decorated_definition":
        parent = parent.parent

    return parent is not None and parent.type == "module"
