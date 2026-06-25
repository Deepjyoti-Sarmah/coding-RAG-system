from abc import ABC, abstractmethod

from models.document import Document

from tree_sitter import Tree


class BaseParser(ABC):
    """Converts a document into a AST."""

    @abstractmethod
    def parse(self, document: Document) -> Tree:
        raise NotImplementedError
