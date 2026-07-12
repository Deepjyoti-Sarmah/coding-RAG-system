from tree_sitter import Node

from analysis.import_builder import build_import_reference
from analysis.import_utils import get_module_path
from models.common.source_location import SourceLocation
from models.entities.documents import Document
from models.entities.import_references import ImportReference


def handle_namespace_import(
    *,
    node: Node,
    document: Document,
) -> ImportReference | None:

    identifier = None

    for child in node.children:
        if child.type == "identifier":
            identifier = child
            break

    if identifier is None:
        return None

    module_path = get_module_path(node)

    if module_path is None:
        return None

    return build_import_reference(
        document=document,
        module_path=module_path,
        imported_name="*",
        local_name=identifier.text.decode("utf-8"),
        location=SourceLocation(
            start_line=node.start_point.row + 1,
            end_line=node.end_point.row + 1,
            start_byte=node.start_byte,
            end_byte=node.end_byte,
        ),
    )
