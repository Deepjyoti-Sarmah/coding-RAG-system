from abc import ABC, abstractmethod

from models.document import Document

from tree_sitter import Tree


class BaseParser(ABC):
    @abstractmethod
    def parse(self, document: Document) -> Tree:
        raise NotImplementedError
