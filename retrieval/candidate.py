from dataclasses import dataclass


@dataclass(slots=True)
class HybridCandidate:
    chunk_key: str
    symbol_id: str
    symbol_name: str
    qualified_name: str
    relative_path: str
    symbol_kind: str
    score: float
    sources: tuple[str, ...]