from dataclasses import dataclass


@dataclass(slots=True)
class FtsHit:
    chunk_key: str
    symbol_name: str
    qualified_name: str
    relative_path: str
    score: float