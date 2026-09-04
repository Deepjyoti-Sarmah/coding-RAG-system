from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from analysis.fingerprints import compute_content_hash
from graph.code_graph import CodeGraph
from models.entities.exports import Export
from models.entities.import_references import ImportReference
from models.entities.symbols import Symbol

if TYPE_CHECKING:
    from analysis.build_result import BuildResult

CHUNK_VERSION = "v1"


@dataclass(slots=True)
class SemanticChunk:
    chunk_key: str
    symbol_id: str
    relative_path: str
    embedding_text: str
    display_text: str
    content_hash: str
    chunk_version: str = CHUNK_VERSION


def build_semantic_chunks(result: BuildResult) -> list[SemanticChunk]:
    imports_by_document: dict[str, list[ImportReference]] = {}
    for import_reference in result.import_references:
        imports_by_document.setdefault(import_reference.document_id, []).append(
            import_reference
        )

    exports_by_document: dict[str, list[Export]] = {}
    for export in result.exports:
        exports_by_document.setdefault(export.document_id, []).append(export)

    chunks = [
        build_semantic_chunk(
            symbol,
            result.graph,
            document_imports=imports_by_document.get(symbol.document_id, []),
            exports=exports_by_document.get(symbol.document_id, []),
        )
        for symbol in result.symbols
    ]
    # Fallback for docs with no symbols but non-empty content → synthetic MODULE symbol + chunk
    symbol_doc_ids = {s.document_id for s in result.symbols}
    for doc in result.documents:
        if doc.document_id not in symbol_doc_ids and doc.content.strip():
            # Only for fallback languages or genuinely chunk-worthy docs (avoid empty __init__.py noise)
            # Create synthetic MODULE symbol first so FK passes, then chunk
            from analysis.passes.module_symbol_pass import build_module_symbol

            # Reuse module_symbol logic but without import/export guard for fallback langs
            # Check if fallback extension
            from ckg.config import FALLBACK_EXTENSIONS

            ext = "." + doc.relative_path.split(".")[-1].lower() if "." in doc.relative_path else ""
            is_fallback = ext in FALLBACK_EXTENSIONS
            # For strict langs, only fallback if doc had imports/exports (original module_symbol logic)
            # For fallback langs, always create MODULE chunk when non-empty
            should_fallback = is_fallback or doc.relative_path.endswith((".html", ".css", ".json", ".md", ".yaml", ".xml"))
            if should_fallback or doc.content.strip():
                # Avoid duplicating empty-file test: empty file already filtered by content.strip()
                # For strict langs, respect original guard: need imports/exports to be worth chunking
                if not is_fallback:
                    # Keep original behavior for strict langs: require imports/exports to avoid noise
                    # Already handled by module_symbol_pass, so skip here to avoid duplicate
                    continue
                synth = build_module_symbol(doc)
                # Ensure stable_key matches fallback chunk key expectations
                result.symbols.append(synth)
                # Also need to add to graph/symbol_index? chunker doesn't have context, but result.symbols is enough for FK
                chunks.append(_fallback_module_chunk(doc, synth))
    return chunks


def _fallback_module_chunk(doc, synth=None) -> SemanticChunk:
    # Use synthetic symbol's stable_key/symbol_id if provided
    if synth is not None:
        text = doc.content[:2000]
        return SemanticChunk(
            chunk_key=synth.stable_key,
            symbol_id=synth.symbol_id,
            relative_path=doc.relative_path,
            embedding_text=f"module {doc.relative_path}\nsource:\n{text}",
            display_text=text,
            content_hash=compute_content_hash(text),
            chunk_version=CHUNK_VERSION,
        )
    text = doc.content[:2000]
    stable = f"{doc.relative_path}|{doc.language}|__module__|module"
    return SemanticChunk(
        chunk_key=stable,
        symbol_id=doc.document_id,
        relative_path=doc.relative_path,
        embedding_text=f"module {doc.relative_path}\nsource:\n{text}",
        display_text=text,
        content_hash=compute_content_hash(text),
        chunk_version=CHUNK_VERSION,
    )


def build_semantic_chunk(
    symbol: Symbol,
    graph: CodeGraph,
    *,
    document_imports: list[ImportReference],
    exports: list[Export],
) -> SemanticChunk:
    callee_names = get_related_names(graph.callees_of(symbol.symbol_id))
    caller_names = get_related_names(graph.callers_of(symbol.symbol_id))
    parent_names = get_related_names(graph.parents_of(symbol.symbol_id))

    embedding_text = build_embedding_text(
        symbol=symbol,
        callee_names=callee_names,
        caller_names=caller_names,
        parent_names=parent_names,
        imports=sorted(document_imports, key=import_sort_key),
        exports=get_symbol_exports(exports, symbol.name),
        language=language_for_path(symbol.relative_path),
    )

    return SemanticChunk(
        chunk_key=symbol.stable_key,
        symbol_id=symbol.symbol_id,
        relative_path=symbol.relative_path,
        embedding_text=embedding_text,
        display_text=symbol.content,
        content_hash=compute_content_hash(embedding_text),
        chunk_version=CHUNK_VERSION,
    )


def get_related_names(symbols: list[Symbol]) -> str:

    if not symbols:
        return "none"

    names = [s.name for s in symbols]
    return ", ".join(names)


def get_symbol_exports(exports: list[Export], symbol_name: str) -> str:
    aliases = sorted(
        format_export(export) for export in exports if export.symbol_name == symbol_name
    )

    if not aliases:
        return "none"

    return ", ".join(aliases)


def format_export(export: Export) -> str:
    if export.exported_name == export.symbol_name:
        return export.exported_name

    return f"{export.symbol_name} as {export.exported_name}"


def import_sort_key(import_reference: ImportReference) -> tuple[str, str]:
    return (
        import_reference.imported_name,
        import_reference.module_path,
    )


def language_for_path(relative_path: str) -> str:
    from ingestion.language import detect_language

    suffix = relative_path.rsplit(".", 1)
    return detect_language(f".{suffix[-1]}") if len(suffix) == 2 else "unknown"


def build_embedding_text(
    symbol: Symbol,
    callee_names: str,
    caller_names: str,
    parent_names: str,
    imports: list[ImportReference],
    exports: str,
    *,
    language: str = "typescript",
) -> str:
    import_lines = (
        "none"
        if not imports
        else ", ".join(
            format_import(import_reference, language=language)
            for import_reference in imports
        )
    )

    lines = [
        f"{symbol.kind.value} {symbol.name}",
        f"qualified name: {symbol.qualified_name}",
        f"file: {symbol.relative_path}",
        f"parent: {parent_names}",
        f"calls: {callee_names}",
        f"called by: {caller_names}",
        f"imports: {import_lines}",
        f"exports: {exports}",
        f"source:\n{symbol.content}",
    ]

    return "\n".join(lines)


def format_import(import_reference: ImportReference, *, language: str) -> str:
    module_path = import_reference.module_path

    if language == "go":
        return f'import "{module_path}"'

    # Python relative imports look like `.auth` / `..pkg.auth`: dotted,
    # but never containing a slash (that is the TS `./x` shape).
    if module_path.startswith(".") and "/" not in module_path:
        return (
            f'from "{module_path}" '
            f"import {import_reference.imported_name}"
        )

    return (
        f"import {{ {import_reference.imported_name} }} "
        f'from "{module_path}"'
    )
