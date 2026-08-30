from tree_sitter import Node

from analysis.import_builder import build_import_reference
from models.common.source_location import SourceLocation
from models.entities.documents import Document
from models.entities.import_references import ImportReference


def handle_java_import(
    *,
    node: Node,
    document: Document,
) -> ImportReference | None:
    """`import a.b.C;`, `import static a.b.C.field;`, `import a.b.*;`.

    module_path is the full dotted path (package + type, minus any
    trailing `.*`); local/imported name is the last segment, or `*`
    for wildcard imports.
    """
    if node.type != "import_declaration":
        return None

    path_node = next(
        (
            child
            for child in node.children
            if child.type in ("scoped_identifier", "identifier")
        ),
        None,
    )

    if path_node is None:
        return None

    module_path = _dotted_text(path_node)

    if not module_path:
        return None

    is_wildcard = any(child.type == "asterisk" for child in node.children)

    local = "*" if is_wildcard else module_path.rsplit(".", 1)[-1]

    return build_import_reference(
        document=document,
        module_path=module_path,
        imported_name=local,
        local_name=local,
        location=SourceLocation(
            start_line=node.start_point.row + 1,
            end_line=node.end_point.row + 1,
            start_byte=node.start_byte,
            end_byte=node.end_byte,
        ),
    )


def _dotted_text(node: Node) -> str:
    raw = node.text
    return raw.decode("utf-8") if raw is not None else ""
