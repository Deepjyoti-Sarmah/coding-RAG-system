from tree_sitter import Language, Parser, Tree
from tree_sitter_typescript import language_typescript

from models.document import Document
from parsing.base_parser import BaseParser


class TypescriptParser(BaseParser):
    def __init__(self) -> None:
        self._parser = Parser(
            Language(language_typescript()),
        )

    def parse(self, document: Document) -> Tree:
        return self._parser.parse(
            document.content.encode("utf-8"),
        )
