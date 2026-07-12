from tree_sitter import Node

from analysis.import_builder import build_import_reference
from analysis.import_utils import get_module_path
from models.common.source_location import SourceLocation
from models.entities.documents import Document
from models.entities.import_references import ImportReference


def handle_import_specifier(
    *,
    node: Node,
    document: Document,
) -> ImportReference | None:

    module_path = get_module_path(node)

    if module_path is None:
        return None

    identifiers = [child for child in node.children if child.type == "identifier"]

    if len(identifiers) == 1:
        imported_name = identifiers[0].text.decode("utf-8")
        local_name = imported_name
    elif len(identifiers) == 2:
        imported_name = identifiers[0].text.decode("utf-8")
        local_name = identifiers[1].text.decode("utf-8")
    else:
        return None

    return build_import_reference(
        document=document,
        module_path=module_path,
        imported_name=imported_name,
        local_name=local_name,
        location=SourceLocation(
            start_line=node.start_point.row + 1,
            end_line=node.end_point.row + 1,
            start_byte=node.start_byte,
            end_byte=node.end_byte,
        ),
    )
