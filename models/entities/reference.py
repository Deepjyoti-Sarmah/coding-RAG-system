from dataclasses import dataclass

from models.common.source_location import SourceLocation


@dataclass(slots=True)
class Reference:
    reference_id: str

    document_id: str

    name: str

    location: SourceLocation

    owner_symbol_id: str | None = None
