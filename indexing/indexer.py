from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from analysis.build_graph import build_graph
from analysis.build_result import BuildResult
from analysis.fingerprints import compute_content_hash
from analysis.indexing_context import IndexingContext
from analysis.pipeline import run_extraction_passes, run_resolution_passes
from analysis.symbol_matching import match_symbols
from chunking.symbol_chunker import build_semantic_chunks
from indexing.diff import (
    FileChange,
    ScanResult,
    importers_of,
    scan_files,
)
from indexing.embedding_queue import enqueue_embedding_jobs
from indexing.export_index import ExportIndex
from indexing.rebuild_plan import (
    FilePartition,
    PreviousSnapshot,
    RebuildPlan,
    build_previous_snapshot,
    partition_files,
    plan_rebuild,
)
from indexing.resource_governor import onnx_thread_cap
from indexing.symbol_index import SymbolIndex
from ingestion.loader import build_document
from models.entities.documents import Document
from models.file_state import FileState
from storage.index_store import load_file_states, load_index, persist_index

onnx_thread_cap()


@dataclass(slots=True)
class IndexRunReport:
    changes: dict[str, FileChange] = field(default_factory=dict)

    parsed_files: int = 0

    resolved_references: int = 0

    # Embedding is async (Phase 18): reindex_index never embeds, it only
    # enqueues jobs for the embedding worker to pick up.
    new_embeddings: int = 0


def reindex_index(db_path: str, root_dir: str, *, on_progress=None) -> IndexRunReport:
    from indexing.resource_governor import ProjectIndexLock

    with ProjectIndexLock(root_dir):
        previous_states = _load_previous_states(db_path)
        scan = scan_files(root_dir, previous_states)

        if on_progress is not None:
            total = len(scan.current)
            if total >= 50:
                try:
                    on_progress(f"Scanning {total} files...")
                except Exception:
                    pass

        if not previous_states:
            result = build_graph(root_dir, on_progress=on_progress)
            states = _file_states_from_documents(result.documents)
            persist_index(
                db_path,
                result,
                states,
            )
            _persist_merkle(db_path, states)
            enqueue_embedding_jobs(db_path, result.chunks)

            return IndexRunReport(
                changes=scan.changes,
                parsed_files=len(result.documents),
                resolved_references=len(result.references),
            )

        return _incremental_rebuild(
            db_path=db_path,
            previous_states=previous_states,
            scan=scan,
            on_progress=on_progress,
        )


def _incremental_rebuild(
    *,
    db_path: str,
    previous_states: dict[str, FileState],
    scan: ScanResult,
    on_progress=None,
) -> IndexRunReport:
    changes = scan.changes
    partition = partition_files(scan)

    if not partition.has_work:
        return IndexRunReport(changes=changes)

    snapshot = build_previous_snapshot(load_index(db_path))

    documents_by_path = _build_documents(
        scan=scan,
        changes=changes,
        previous_docs_by_path=snapshot.docs_by_path,
        on_progress=on_progress,
    )
    documents_by_id = {d.document_id: d for d in documents_by_path.values()}

    context = IndexingContext()
    result = BuildResult()
    context.document_index.add_many(list(documents_by_path.values()))

    run_extraction_passes(
        context=context,
        result=result,
        documents=[
            documents_by_path[path]
            for path in partition.rebuild
            if path in documents_by_path
        ],
    )

    fresh_reference_count = len(result.references)

    _remap_reference_owners(
        result.references,
        _reconcile_identity(
            previous_symbols=_previous_symbols_for_changed(
                previous=snapshot.result,
                changes=changes,
                prev_docs_by_path=snapshot.docs_by_path,
            ),
            new_symbols=result.symbols,
        ),
    )

    plan = plan_rebuild(
        partition=partition,
        snapshot=snapshot,
        importers=_importers_for(
            partition=partition,
            snapshot=snapshot,
            fresh_imports=result.import_references,
            documents_by_id=documents_by_id,
        ),
        documents_by_id=documents_by_id,
        fresh_exports=result.exports,
        fresh_symbols=result.symbols,
    )

    reused_reference_count = _merge_reused_state(
        result=result,
        plan=plan,
        snapshot=snapshot,
        documents_by_path=documents_by_path,
    )

    context.symbol_index = SymbolIndex()
    context.symbol_index.add_many(result.symbols)
    context.export_index = ExportIndex()
    context.export_index.add_many(result.exports)
    result.symbol_index = context.symbol_index

    run_resolution_passes(context=context, result=result)

    # Untouched files keep the resolutions merged in above, so their raw
    # imports and references are re-attached only after the resolver
    # passes have run - re-resolving them would duplicate that work. The
    # relationship and graph passes read `resolved_references`, not these
    # lists, so attaching them afterwards is equivalent.
    for path in plan.untouched:
        result.import_references.extend(snapshot.imports_by_path.get(path, []))
        result.references.extend(snapshot.references_by_path.get(path, []))

    result.chunks = build_semantic_chunks(result)

    states = _build_file_states(
        scan=scan,
        changes=changes,
        previous_states=previous_states,
    )
    persist_index(
        db_path,
        result,
        states,
        removed_paths=partition.rebuild | partition.deleted,
        reresolve_paths=plan.reresolve,
    )
    _persist_merkle(db_path, states)
    enqueue_embedding_jobs(db_path, result.chunks)

    return IndexRunReport(
        changes=changes,
        parsed_files=len(partition.rebuild),
        resolved_references=fresh_reference_count + reused_reference_count,
    )


def _importers_for(
    *,
    partition: FilePartition,
    snapshot: PreviousSnapshot,
    fresh_imports: list[Any],
    documents_by_id: dict[str, Document],
) -> dict[str, set[str]]:
    """Who imports what, across freshly parsed and carried-over files."""
    combined = list(fresh_imports)

    for path in partition.current - partition.rebuild:
        combined.extend(snapshot.imports_by_path.get(path, []))

    return importers_of(
        import_references=combined,
        documents_by_id=documents_by_id,
    )


def _merge_reused_state(
    *,
    result: BuildResult,
    plan: RebuildPlan,
    snapshot: PreviousSnapshot,
    documents_by_path: dict[str, Document],
) -> int:
    """Fold last run's still-valid artifacts into this run's result.

    Symbols and exports come back for every file that was not reparsed.
    Files being re-resolved also need their raw imports and references
    back, so the resolver passes can run over them again; files left
    untouched instead keep their previous *resolutions*. Returns how many
    references were carried in for re-resolution, which the run report
    counts as work done.
    """
    reused_symbols: list[Any] = []
    reused_exports: list[Any] = []

    for path in plan.untouched | plan.reresolve:
        reused_symbols.extend(snapshot.symbols_by_path.get(path, []))
        reused_exports.extend(snapshot.exports_by_path.get(path, []))

    result.symbols = [*reused_symbols, *result.symbols]
    result.exports = [*reused_exports, *result.exports]
    result.documents = [
        documents_by_path[path] for path in plan.partition.current
    ]

    reused_imports: list[Any] = []
    reused_references: list[Any] = []

    for path in plan.reresolve:
        reused_imports.extend(snapshot.imports_by_path.get(path, []))
        reused_references.extend(snapshot.references_by_path.get(path, []))

    result.import_references = [*reused_imports, *result.import_references]
    result.references = [*reused_references, *result.references]

    for path in plan.untouched:
        result.resolved_import_references.extend(
            snapshot.resolved_imports_by_path.get(path, [])
        )
        result.resolved_references.extend(
            snapshot.resolved_references_by_path.get(path, [])
        )

    return len(reused_references)


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
    on_progress=None,
) -> dict[str, Document]:
    from indexing.resource_governor import adaptive_batch_size

    total = len(scan.current)
    batch = adaptive_batch_size(total)
    documents_by_path: dict[str, Document] = {}

    for idx, (path, scanned) in enumerate(scan.current.items(), start=1):
        previous_doc = previous_docs_by_path.get(path)

        if changes[path] == FileChange.UNCHANGED and previous_doc is not None:
            documents_by_path[path] = previous_doc
            continue

        content = scanned.content

        if content is None:
            continue

        document_id = (
            previous_doc.document_id if previous_doc is not None else str(uuid4())
        )

        documents_by_path[path] = build_document(
            file_path=scanned.file_path,
            relative_path=path,
            content=content,
            document_id=document_id,
        )

        if on_progress is not None and idx % batch == 0:
            try:
                on_progress(f"Parsed {idx}/{total} files...")
            except Exception:
                pass

    return documents_by_path


def _previous_symbols_for_changed(
    *,
    previous: BuildResult,
    changes: dict[str, FileChange],
    prev_docs_by_path: dict[str, Document],
) -> list[Any]:
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
    previous_symbols: list[Any],
    new_symbols: list[Any],
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


def _remap_reference_owners(references: list[Any], id_map: dict[str, str]) -> None:
    for reference in references:
        reference.owner_symbol_id = id_map.get(
            reference.owner_symbol_id,
            reference.owner_symbol_id,
        )


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


def _persist_merkle(db_path: str, states: list[FileState]) -> None:
    try:
        from indexing.merkle import compute_root
        from storage import db

        root = compute_root(states)
        conn = db.connect(db_path)
        try:
            conn.execute(
                "INSERT INTO index_metadata (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                ("merkle_root", root),
            )
            conn.commit()
        finally:
            conn.close()
    except Exception:
        pass


def _now() -> str:
    return datetime.now(UTC).isoformat()
