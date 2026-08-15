from tree_sitter import Node

from models.common.source_location import SourceLocation
from models.entities.documents import Document
from models.entities.exports import Export


def build_export(
    *,
    document: Document,
    exported_name: str,
    symbol_name: str | None,
    node: Node,
) -> Export:

    return Export(
        document_id=document.document_id,
        exported_name=exported_name,
        symbol_name=symbol_name,
        location=SourceLocation(
            start_line=node.start_point.row + 1,
            end_line=node.end_point.row + 1,
            start_byte=node.start_byte,
            end_byte=node.end_byte,
        ),
    )
