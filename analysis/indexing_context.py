from dataclasses import dataclass, field

from analysis.semantic.namespace_index import NamespaceIndex
from indexing.document_index import DocumentIndex
from indexing.export_index import ExportIndex
from indexing.symbol_index import SymbolIndex
from models.extracted_symbol import ExtractedSymbol
from models.parsed_document import ParsedDocument


@dataclass(slots=True)
class IndexingContext:
    document_index: DocumentIndex = field(default_factory=DocumentIndex)

    symbol_index: SymbolIndex = field(default_factory=SymbolIndex)

    export_index: ExportIndex = field(default_factory=ExportIndex)

    namespace_index: NamespaceIndex = field(default_factory=NamespaceIndex)

    parsed_documents: list[ParsedDocument] = field(default_factory=list)

    extracted_symbols: list[ExtractedSymbol] = field(default_factory=list)
