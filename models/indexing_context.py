from dataclasses import dataclass, field

from indexing.symbol_index import SymbolIndex
from models.extracted_symbol import ExtractedSymbol


@dataclass(slots=True)
class IndexingContext:
    extracted_symbols: list[ExtractedSymbol] = field(default_factory=list)

    symbol_index: SymbolIndex = field(default_factory=SymbolIndex)
