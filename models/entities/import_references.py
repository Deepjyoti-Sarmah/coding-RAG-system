from dataclasses import dataclass

from models.common.source_location import SourceLocation


@dataclass(slots=True)
class ImportReference:
    document_id: str

    module_path: str

    imported_name: str

    local_name: str

    location: SourceLocation
