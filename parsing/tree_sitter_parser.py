import threading

from tree_sitter import Language, Parser, Tree

from models.entities.documents import Document
from parsing.base_parser import BaseParser


class TreeSitterParser(BaseParser):
    def __init__(self, language: Language) -> None:
        self._language = language
        self._local = threading.local()

    def _parser(self) -> Parser:
        p = getattr(self._local, "parser", None)
        if p is None:
            p = Parser(language=self._language)
            self._local.parser = p
        return p

    def parse(self, document: Document) -> Tree:
        return self._parser().parse(
            document.content.encode(),
        )
