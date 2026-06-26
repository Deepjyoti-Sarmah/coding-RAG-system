from abc import ABC, abstractmethod

from tree_sitter import Tree


class BaseAnalyzer(ABC):
    @abstractmethod
    def analyze(self, tree: Tree):
        raise NotImplementedError
