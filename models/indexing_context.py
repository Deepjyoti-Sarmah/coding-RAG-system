from dataclasses import dataclass, field

from indexing.document_index import DocumentIndex
from indexing.symbol_index import SymbolIndex
from models.extracted_symbol import ExtractedSymbol


@dataclass(slots=True)
class IndexingContext:
    # TODO: Extend this context with ParsedDocument IR, import/export indexes, and
    # file-hash state so passes can share reusable intermediate results.
    document_index: DocumentIndex = field(default_factory=DocumentIndex)

    symbol_index: SymbolIndex = field(default_factory=SymbolIndex)

    extracted_symbols: list[ExtractedSymbol] = field(default_factory=list)
