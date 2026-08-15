from dataclasses import dataclass

from models.common.source_location import SourceLocation


@dataclass(slots=True)
class Export:
    document_id: str

    exported_name: str

    symbol_name: str | None

    location: SourceLocation
