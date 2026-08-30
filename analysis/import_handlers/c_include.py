from tree_sitter import Node

from analysis.import_builder import build_import_reference
from models.common.source_location import SourceLocation
from models.entities.documents import Document
from models.entities.import_references import ImportReference


def handle_c_include(*, node: Node, document: Document) -> ImportReference | None:
    if node.type != "preproc_include":
        return None
    target = next((child for child in node.children if child.type == "string_literal"), None)
    if target is None or target.text is None:
        return None
    raw = target.text.decode("utf-8")
    if not (raw.startswith('"') and raw.endswith('"')):
        # Angle-bracket includes are recorded but intentionally unresolved.
        return build_import_reference(
            document=document, module_path=raw.strip("<>"), imported_name="*", local_name="*",
            location=SourceLocation(start_line=node.start_point.row + 1, end_line=node.end_point.row + 1,
                                    start_byte=node.start_byte, end_byte=node.end_byte),
        )
    return build_import_reference(
        document=document, module_path=raw[1:-1], imported_name="*", local_name="*",
        location=SourceLocation(start_line=node.start_point.row + 1, end_line=node.end_point.row + 1,
                                start_byte=node.start_byte, end_byte=node.end_byte),
    )
