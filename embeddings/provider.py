from abc import ABC, abstractmethod

import numpy as np


class EmbeddingProvider(ABC):
    @property
    @abstractmethod
    def dimension(self) -> int:
        ...

    @property
    @abstractmethod
    def model_id(self) -> str:
        """Stable identifier for the model/backend (e.g. 'local:all-MiniLM-L6-v2' or 'ollama:nomic-embed-text')."""
        ...

    @abstractmethod
    def embed(self, text: str) -> np.ndarray:
        ...

    @abstractmethod
    def embed_batch(self, texts: list[str]) -> np.ndarray:
        ...

    @abstractmethod
    def embed_query(self, query: str) -> np.ndarray:
        ...
