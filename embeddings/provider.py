from abc import ABC, abstractmethod

import numpy as np


class EmbeddingProvider(ABC):
    @property
    @abstractmethod
    def dimension(self) -> int:
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
