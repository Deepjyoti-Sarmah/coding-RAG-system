from dataclasses import dataclass

from models.common.source_location import SourceLocation
from models.entities.reference_kind import ReferenceKind


@dataclass(slots=True)
class Reference:
    reference_id: str

    document_id: str

    name: str

    location: SourceLocation

    kind: ReferenceKind

    owner_symbol_id: str
