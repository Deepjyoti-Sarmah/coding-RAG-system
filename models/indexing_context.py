from dataclasses import dataclass, field

from indexing.document_index import DocumentIndex
from indexing.symbol_index import SymbolIndex
from models.extracted_symbol import ExtractedSymbol


@dataclass(slots=True)
class IndexingContext:
    document_index: DocumentIndex = field(default_factory=DocumentIndex)

    symbol_index: SymbolIndex = field(default_factory=SymbolIndex)

    extracted_symbols: list[ExtractedSymbol] = field(default_factory=list)
