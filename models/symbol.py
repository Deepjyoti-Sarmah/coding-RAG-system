from dataclasses import dataclass


@dataclass(slots=True)
class Symbol:
    symbol_id: str

    document_id: str

    name: str

    symbol_type: str

    relative_path: str

    start_line: int
    end_line: int

    content: str
