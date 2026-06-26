from tree_sitter import Tree
from analysis.base_analyzer import BaseAnalyzer
from models.document import Document
from models.symbol import Symbol


class SymbolExtractor(BaseAnalyzer):
    def analyze(
        self,
        tree: Tree,
        document: Document,
    ) -> list[Symbol]:

        self.document = document

        self.walk(tree.root_node)

        return self.symbols

    def walk(self, node):
        self.visit(node)

        for child in node.children:
            self.walk(child)

    def visit(self, node):
        pass
