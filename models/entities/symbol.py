from dataclasses import dataclass

from models.common.source_location import SourceLocation
from models.entities.symbol_kind import SymbolKind


@dataclass(slots=True)
class Symbol:
    symbol_id: str
    document_id: str

    name: str
    kind: SymbolKind

    relative_path: str

    location: SourceLocation

    content: str

    parent_symbol_id: str | None = None
    language: str = ""
