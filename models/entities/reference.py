from dataclasses import dataclass

from models.common.source_location import SourceLocation


@dataclass(slots=True)
class Reference:
    reference_id: str

    document_id: str

    text: str

    location: SourceLocation
