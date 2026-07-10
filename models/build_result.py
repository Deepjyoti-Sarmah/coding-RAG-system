from dataclasses import dataclass

from graph.code_graph import CodeGraph
from indexing.symbol_index import SymbolIndex


@dataclass
class BuildResult:
    graph: CodeGraph
    symbol_index: SymbolIndex
