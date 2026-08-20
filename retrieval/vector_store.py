from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from chunking.symbol_chunker import SemanticChunk


@dataclass(slots=True)
class VectorSearchHit:
    chunk_key: str
    relative_path: str
    score: float
    chunk: SemanticChunk | None = None


class VectorStore(ABC):
    @abstractmethod
    def search(
        self,
        query_vector: np.ndarray,
        *,
        top_k: int = 5,
        relative_path: str | None = None,
    ) -> list[VectorSearchHit]: ...
