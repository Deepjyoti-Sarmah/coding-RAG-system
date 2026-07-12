from abc import ABC, abstractmethod

from tree_sitter import Tree

from models.entities.documents import Document


class BaseParser(ABC):
    @abstractmethod
    def parse(self, document: Document) -> Tree:
        raise NotImplementedError
