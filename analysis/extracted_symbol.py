from dataclasses import dataclass

from tree_sitter import Node

from models.entities.symbol import Symbol


@dataclass(slots=True)
class ExtractedSymbol:
    symbol: Symbol
    node: Node
