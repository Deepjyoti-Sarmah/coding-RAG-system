from uuid import uuid4

from analysis.build_result import BuildResult
from analysis.fingerprints import (
    build_stable_key,
    compute_content_hash,
    compute_signature_hash,
)
from analysis.indexing_context import IndexingContext
from models.common.source_location import SourceLocation
from models.entities.documents import Document
from models.entities.symbol_kind import SymbolKind
from models.entities.symbols import Symbol


def run_module_symbol_pass(*, context: IndexingContext, result: BuildResult) -> None:
    """Synthesize one module-level Symbol for a document that yielded none.

    A document that is entirely module-level statements - a bare re-export,
    a constants-only file, an `__init__.py` that just re-exports - is parsed
    and stored but the symbol pass extracts nothing from it, so it never
    becomes a chunk and is unreachable by any query (see
    benchmarks/results/COVERAGE.md). Giving such a document one synthetic
    module symbol lets it flow through the existing chunker path unchanged.

    Synthesize only when there's something worth retrieving - a document
    with imports or exports has real content; one with neither (a bare
    `__init__.py`) gets nothing, since an empty chunk is index noise with
    no recall benefit. Must run after run_import_pass and run_export_pass,
    which populate the sets this checks.
    """
    documents_with_symbols = {symbol.document_id for symbol in result.symbols}

    imported_document_ids = {ir.document_id for ir in result.import_references}
    exported_document_ids = {export.document_id for export in result.exports}

    new_symbols = []

    for parsed in context.parsed_documents:
        document = parsed.document

        if document.document_id in documents_with_symbols:
            continue

        has_imports = document.document_id in imported_document_ids
        has_exports = document.document_id in exported_document_ids

        if not has_imports and not has_exports:
            continue

        new_symbols.append(build_module_symbol(document))

    result.symbols.extend(new_symbols)
    context.symbol_index.add_many(new_symbols)


def build_module_symbol(document: Document) -> Symbol:
    qualified_name = document.relative_path

    return Symbol(
        symbol_id=str(uuid4()),
        document_id=document.document_id,
        name=document.file_name,
        kind=SymbolKind.MODULE,
        relative_path=document.relative_path,
        location=SourceLocation(
            start_line=1,
            end_line=max(document.line_count, 1),
            start_byte=0,
            end_byte=len(document.content),
        ),
        content=document.content,
        qualified_name=qualified_name,
        content_hash=compute_content_hash(document.content),
        signature_hash=compute_signature_hash(qualified_name),
        stable_key=build_stable_key(
            relative_path=document.relative_path,
            language=document.language,
            qualified_name=qualified_name,
            kind=SymbolKind.MODULE,
        ),
    )
