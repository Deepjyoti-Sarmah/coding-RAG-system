from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from analysis.build_graph import build_graph
from analysis.fingerprints import compute_content_hash
from analysis.passes.export_pass import run_export_pass
from analysis.passes.graph_pass import run_graph_pass
from analysis.passes.import_pass import run_import_pass
from analysis.passes.import_resolver_pass import run_import_resolver_pass
from analysis.passes.parse_pass import run_parse_pass
from analysis.passes.reference_pass import run_reference_pass
from analysis.passes.relationship_pass import run_relationship_pass
from analysis.passes.resolver_pass import run_reference_resolver_pass
from analysis.passes.symbol_pass import run_symbol_pass
from analysis.symbol_matching import match_symbols
from indexing.diff import (
    FileChange,
    ScanResult,
    interface_fingerprint,
    importers_of,
    scan_files,
)
from indexing.export_index import ExportIndex
from indexing.symbol_index import SymbolIndex
from ingestion.loader import build_document
from models.build_result import BuildResult
from models.entities.documents import Document
from models.file_state import FileState
from models.indexing_context import IndexingContext
from storage.index_store import load_file_states, load_index, persist_index


@dataclass(slots=True)
class IndexRunReport:
    changes: dict[str, FileChange] = field(default_factory=dict)

    parsed_files: int = 0

    resolved_references: int = 0

    new_embeddings: int = 0


def reindex_index(
    db_path: str,
    root_dir: str,
) -> IndexRunReport:
    previous_states = _load_previous_states(db_path)

    scan = scan_files(root_dir, previous_states)

    if not previous_states:
        result = build_graph(root_dir)
        persist_index(
            db_path,
            result,
            _file_states_from_documents(result.documents),
        )

        return IndexRunReport(
            changes=scan.changes,
            parsed_files=len(result.documents),
            resolved_references=len(result.references),
        )

    return _incremental_rebuild(
        db_path=db_path,
        previous_states=previous_states,
        scan=scan,
    )


def _incremental_rebuild(
    *,
    db_path: str,
    previous_states: dict[str, FileState],
    scan: ScanResult,
) -> IndexRunReport:
    changes = scan.changes
    current_paths = set(scan.current)

    rebuild_paths = {
        path
        for path, change in changes.items()
        if change in (FileChange.NEW, FileChange.CHANGED)
    }
    deleted_paths = {
        path for path, change in changes.items() if change == FileChange.DELETED
    }

    if not rebuild_paths and not deleted_paths:
        return IndexRunReport(changes=changes)

    previous = load_index(db_path)

    prev_docs_by_path = {d.relative_path: d for d in previous.documents}
    prev_docs_by_id = {d.document_id: d for d in previous.documents}
    prev_symbols_by_path = _group_by_path(previous.symbols, prev_docs_by_id)
    prev_imports_by_path = _group_by_path(
        previous.import_references, prev_docs_by_id
    )
    prev_exports_by_path = _group_by_path(previous.exports, prev_docs_by_id)
    prev_references_by_path = _group_by_path(previous.references, prev_docs_by_id)
    prev_resolved_refs_by_path = _group_resolved_references(
        previous.resolved_references, prev_docs_by_id
    )
    prev_resolved_imports_by_path = _group_resolved_imports(
        previous.resolved_import_references, prev_docs_by_id
    )

    documents_by_path = _build_documents(
        scan=scan,
        changes=changes,
        previous_docs_by_path=prev_docs_by_path,
    )
    documents_by_id = {d.document_id: d for d in documents_by_path.values()}

    context = IndexingContext()
    result = BuildResult()
    context.document_index.add_many(list(documents_by_path.values()))

    rebuild_documents = [
        documents_by_path[path]
        for path in rebuild_paths
        if path in documents_by_path
    ]

    run_parse_pass(
        context=context,
        result=result,
        documents=rebuild_documents,
    )

    for parsed in context.parsed_documents:
        run_symbol_pass(
            document=parsed.document,
            tree=parsed.tree,
            context=context,
            result=result,
        )

    run_import_pass(context=context, result=result)
    run_export_pass(context=context, result=result)
    run_reference_pass(context=context, result=result)

    fresh_reference_count = len(result.references)

    id_map = _reconcile_identity(
        previous_symbols=_previous_symbols_for_changed(
            previous=previous,
            changes=changes,
            prev_docs_by_path=prev_docs_by_path,
        ),
        new_symbols=result.symbols,
    )
    _remap_reference_owners(result.references, id_map)

    changed_paths = {
        path for path, change in changes.items() if change == FileChange.CHANGED
    }

    interface_changed_paths = _interface_changed_paths(
        changed_paths=changed_paths,
        prev_docs_by_path=prev_docs_by_path,
        prev_exports_by_path=prev_exports_by_path,
        prev_symbols_by_path=prev_symbols_by_path,
        fresh_exports=result.exports,
        fresh_symbols=result.symbols,
    )

    combined_imports = list(result.import_references)

    for path in current_paths - rebuild_paths:
        combined_imports.extend(prev_imports_by_path.get(path, []))

    importers = importers_of(
        import_references=combined_imports,
        documents_by_id=documents_by_id,
    )

    reresolve_paths = _reresolve_paths(
        invalidation_sources=interface_changed_paths | deleted_paths,
        importers=importers,
        documents_by_id=documents_by_id,
    )

    untouched_paths = current_paths - rebuild_paths - reresolve_paths

    reused_symbols: list = []
    reused_exports: list = []

    for path in untouched_paths | reresolve_paths:
        reused_symbols.extend(prev_symbols_by_path.get(path, []))
        reused_exports.extend(prev_exports_by_path.get(path, []))

    result.symbols = [*reused_symbols, *result.symbols]
    result.exports = [*reused_exports, *result.exports]
    result.documents = [documents_by_path[path] for path in current_paths]

    reused_imports_for_reresolve: list = []
    reused_references_for_reresolve: list = []

    for path in reresolve_paths:
        reused_imports_for_reresolve.extend(prev_imports_by_path.get(path, []))
        reused_references_for_reresolve.extend(prev_references_by_path.get(path, []))

    result.import_references = [
        *reused_imports_for_reresolve,
        *result.import_references,
    ]
    result.references = [
        *reused_references_for_reresolve,
        *result.references,
    ]

    for path in untouched_paths:
        result.resolved_import_references.extend(
            prev_resolved_imports_by_path.get(path, [])
        )
        result.resolved_references.extend(prev_resolved_refs_by_path.get(path, []))

    context.symbol_index = SymbolIndex()
    context.symbol_index.add_many(result.symbols)
    context.export_index = ExportIndex()
    context.export_index.add_many(result.exports)
    result.symbol_index = context.symbol_index

    run_import_resolver_pass(context=context, result=result)
    run_reference_resolver_pass(context=context, result=result)

    for path in untouched_paths:
        result.import_references.extend(prev_imports_by_path.get(path, []))
        result.references.extend(prev_references_by_path.get(path, []))

    run_relationship_pass(result=result)
    run_graph_pass(result=result)

    persist_index(
        db_path,
        result,
        _build_file_states(
            scan=scan,
            changes=changes,
            previous_states=previous_states,
        ),
    )

    return IndexRunReport(
        changes=changes,
        parsed_files=len(rebuild_paths),
        resolved_references=fresh_reference_count
        + len(reused_references_for_reresolve),
    )


def _load_previous_states(db_path: str) -> dict[str, FileState]:
    if not Path(db_path).exists():
        return {}

    return {
        state.relative_path: state for state in load_file_states(db_path)
    }


def _build_documents(
    *,
    scan: ScanResult,
    changes: dict[str, FileChange],
    previous_docs_by_path: dict[str, Document],
) -> dict[str, Document]:
    documents_by_path: dict[str, Document] = {}

    for path, scanned in scan.current.items():
        previous_doc = previous_docs_by_path.get(path)

        if changes[path] == FileChange.UNCHANGED:
            documents_by_path[path] = previous_doc
            continue

        document_id = (
            previous_doc.document_id if previous_doc is not None else str(uuid4())
        )

        documents_by_path[path] = build_document(
            file_path=scanned.file_path,
            relative_path=path,
            content=scanned.content,
            document_id=document_id,
        )

    return documents_by_path


def _previous_symbols_for_changed(
    *,
    previous: BuildResult,
    changes: dict[str, FileChange],
    prev_docs_by_path: dict[str, Document],
) -> list:
    changed_doc_ids = {
        prev_docs_by_path[path].document_id
        for path, change in changes.items()
        if change == FileChange.CHANGED and path in prev_docs_by_path
    }

    return [
        symbol
        for symbol in previous.symbols
        if symbol.document_id in changed_doc_ids
    ]


def _reconcile_identity(
    *,
    previous_symbols: list,
    new_symbols: list,
) -> dict[str, str]:
    matches = match_symbols(
        old_symbols=previous_symbols,
        new_symbols=new_symbols,
    )

    id_map = {m.new_symbol.symbol_id: m.old_symbol.symbol_id for m in matches}

    for symbol in new_symbols:
        symbol.symbol_id = id_map.get(symbol.symbol_id, symbol.symbol_id)

        if symbol.parent_symbol_id is not None:
            symbol.parent_symbol_id = id_map.get(
                symbol.parent_symbol_id,
                symbol.parent_symbol_id,
            )

    return id_map


def _remap_reference_owners(references: list, id_map: dict[str, str]) -> None:
    for reference in references:
        reference.owner_symbol_id = id_map.get(
            reference.owner_symbol_id,
            reference.owner_symbol_id,
        )


def _interface_changed_paths(
    *,
    changed_paths: set[str],
    prev_docs_by_path: dict[str, Document],
    prev_exports_by_path: dict[str, list],
    prev_symbols_by_path: dict[str, list],
    fresh_exports: list,
    fresh_symbols: list,
) -> set[str]:
    changed: set[str] = set()

    for path in changed_paths:
        doc_id = prev_docs_by_path[path].document_id

        current_fingerprint = interface_fingerprint(
            exports=[
                export
                for export in fresh_exports
                if export.document_id == doc_id
            ],
            symbols=[
                symbol
                for symbol in fresh_symbols
                if symbol.document_id == doc_id
            ],
        )
        previous_fingerprint = interface_fingerprint(
            exports=prev_exports_by_path.get(path, []),
            symbols=prev_symbols_by_path.get(path, []),
        )

        if previous_fingerprint != current_fingerprint:
            changed.add(path)

    return changed


def _reresolve_paths(
    *,
    invalidation_sources: set[str],
    importers: dict[str, set[str]],
    documents_by_id: dict[str, Document],
) -> set[str]:
    paths: set[str] = set()

    for source_path in invalidation_sources:
        for importer_id in importers.get(source_path, set()):
            importer_document = documents_by_id.get(importer_id)

            if importer_document is not None:
                paths.add(importer_document.relative_path)

    return paths


def _build_file_states(
    *,
    scan: ScanResult,
    changes: dict[str, FileChange],
    previous_states: dict[str, FileState],
) -> list[FileState]:
    states: list[FileState] = []

    for path, scanned in scan.current.items():
        previous = previous_states.get(path)

        if (
            changes[path] == FileChange.UNCHANGED
            and previous is not None
            and previous.mtime_ns == scanned.mtime_ns
            and previous.size_bytes == scanned.size_bytes
        ):
            states.append(previous)
            continue

        states.append(
            FileState(
                relative_path=path,
                file_hash=_content_hash(scanned, previous),
                size_bytes=scanned.size_bytes,
                mtime_ns=scanned.mtime_ns,
                last_indexed_at=_now(),
            )
        )

    return states


def _file_states_from_documents(documents: list[Document]) -> list[FileState]:
    return [
        FileState(
            relative_path=document.relative_path,
            file_hash=_content_hash_for(document.content),
            size_bytes=document.size_bytes,
            mtime_ns=Path(document.absolute_path).stat().st_mtime_ns,
            last_indexed_at=_now(),
        )
        for document in documents
    ]


def _content_hash(
    scanned,
    previous: FileState | None,
) -> str:
    if scanned.content is not None:
        return _content_hash_for(scanned.content)

    if previous is not None:
        return previous.file_hash

    return ""


def _content_hash_for(content: str) -> str:
    return compute_content_hash(content)


def _group_by_path(
    entities: list,
    docs_by_id: dict[str, Document],
) -> dict[str, list]:
    grouped: dict[str, list] = defaultdict(list)

    for entity in entities:
        document = docs_by_id.get(entity.document_id)

        if document is None:
            continue

        grouped[document.relative_path].append(entity)

    return dict(grouped)


def _group_resolved_references(
    resolved_references: list,
    docs_by_id: dict[str, Document],
) -> dict[str, list]:
    grouped: dict[str, list] = defaultdict(list)

    for resolved in resolved_references:
        document = docs_by_id.get(resolved.reference.document_id)

        if document is None:
            continue

        grouped[document.relative_path].append(resolved)

    return dict(grouped)


def _group_resolved_imports(
    resolved_imports: list,
    docs_by_id: dict[str, Document],
) -> dict[str, list]:
    grouped: dict[str, list] = defaultdict(list)

    for resolved in resolved_imports:
        document = docs_by_id.get(resolved.import_reference.document_id)

        if document is None:
            continue

        grouped[document.relative_path].append(resolved)

    return dict(grouped)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()