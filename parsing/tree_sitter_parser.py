from tree_sitter import Language, Parser, Tree

from models.entities.document import Document
from parsing.base_parser import BaseParser


class TreeSitterParser(BaseParser):
    def __init__(self, language: Language) -> None:
        self.parser = Parser(language=language)

    def parse(self, document: Document) -> Tree:
        return self.parser.parse(
            document.content.encode(),
        )
