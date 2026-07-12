from uuid import uuid4

from tree_sitter import Node

from models.common.source_location import SourceLocation
from models.entities.references import Reference
from models.entities.reference_kind import ReferenceKind
from models.entities.symbols import Symbol


def build_reference(
    *,
    node: Node,
    owner_symbol: Symbol,
    kind: ReferenceKind,
) -> Reference:
    return Reference(
        reference_id=str(uuid4()),
        document_id=owner_symbol.document_id,
        owner_symbol_id=owner_symbol.symbol_id,
        name=node.text.decode("utf-8"),
        kind=kind,
        location=SourceLocation(
            start_line=node.start_point.row + 1,
            end_line=node.end_point.row + 1,
            start_byte=node.start_byte,
            end_byte=node.end_byte,
        ),
    )
