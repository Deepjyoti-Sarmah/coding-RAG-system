from dataclasses import dataclass

from models.entities.symbol_kind import SymbolKind


@dataclass(slots=True)
class Symbol:
    symbol_id: str
    document_id: str
    name: str
    kind: SymbolKind
    relative_path: str

    start_line: int
    end_line: int
    start_byte: int
    end_byte: int

    content: str
    parent_symbol_id: str | None = None
    language: str = ""
