import numpy as np

from analysis.build_result import BuildResult
from chunking.symbol_chunker import SemanticChunk
from models.entities.fts_hit import FtsHit
from models.entities.import_references import ImportReference
from models.entities.resolved_import_reference import ResolvedImportReference
from models.file_state import FileState
from storage import db, schema
from storage.repositories import (
    chunk_fts_repository,
    chunk_repository,
    document_repository,
    embedding_repository,
    export_repository,
    file_state_repository,
    import_repository,
    reference_repository,
    relationship_repository,
    resolved_import_repository,
    resolved_reference_repository,
    symbol_repository,
    vec_index_repository,
)

_TABLES_IN_DEPENDENCY_ORDER = [
    "resolved_imports",
    "resolved_references",
    "relationships",
    "references",
    "exports",
    "imports",
    "chunks",
    "chunks_fts",
    "symbols",
    "documents",
    "file_state",
]


def persist_index(
    db_path: str,
    result: BuildResult,
    file_states: list[FileState] | None = None,
    *,
    removed_paths: frozenset[str] | set[str] | None = None,
) -> None:
    """Replace the persisted index with `result`.

    Full builds pass no `removed_paths`: every table is cleared first.
    Incremental runs pass the paths that were rebuilt or deleted this run;
    their rows are purged precisely, analysis tables are reset (their ids
    are not stable across runs), and the embedding cache plus vector index
    survive for every chunk that is still current.
    """
    conn = db.connect(db_path)

    try:
        schema.create_schema(conn)

        with db.transaction(conn):
            if removed_paths is None:
                _clear_all(conn)
            else:
                _purge_paths(conn, removed_paths)
                _clear_analysis_tables(conn)

            document_repository.insert_many(conn, result.documents)
            symbol_repository.insert_many(conn, result.symbols)

            ids_by_import_object = import_repository.insert_many(
                conn,
                result.import_references,
            )

            export_repository.insert_many(conn, result.exports)
            reference_repository.insert_many(conn, result.references)
            resolved_reference_repository.insert_many(conn, result.resolved_references)
            resolved_import_repository.insert_many(
                conn,
                result.resolved_import_references,
                ids_by_import_object,
            )
            relationship_repository.insert_many(
                conn,
                result.graph.relationships(),
            )
            chunk_repository.insert_many(conn, result.chunks)

            if removed_paths is not None:
                _refresh_fts_keys(conn, {chunk.chunk_key for chunk in result.chunks})

            chunk_fts_repository.insert_many(
                conn,
                result.chunks,
                {symbol.symbol_id: symbol for symbol in result.symbols},
            )

            _prune_derived(conn, result.chunks)

            if file_states is not None:
                file_state_repository.insert_many(conn, file_states)

            schema.bump_generation(conn)
    finally:
        conn.close()


def current_generation(db_path: str) -> int:
    conn = db.connect(db_path)

    try:
        schema.create_schema(conn)
        return schema.current_generation(conn)
    finally:
        conn.close()


def count_rows(db_path: str) -> dict[str, int]:
    """Cheap table counts for status output, without materializing rows."""
    conn = db.connect(db_path)

    try:
        schema.create_schema(conn)
        return {
            "documents": _count(conn, "documents"),
            "symbols": _count(conn, "symbols"),
            "chunks": _count(conn, "chunks"),
            "embeddings": _count(conn, "embeddings"),
        }
    finally:
        conn.close()


def load_imports_for_path(
    db_path: str,
    relative_path: str,
) -> list[tuple[ImportReference, ResolvedImportReference | None]]:
    """A single file's imports and their resolutions, read directly."""
    conn = db.connect(db_path)

    try:
        stored_imports = import_repository.fetch_for_relative_path(
            conn,
            relative_path,
        )
        resolved_by_import_id = resolved_import_repository.fetch_by_import_ids(
            conn,
            [stored.import_id for stored in stored_imports],
        )

        return [
            (
                stored.import_reference,
                resolved_by_import_id.get(stored.import_id),
            )
            for stored in stored_imports
        ]
    finally:
        conn.close()


def _count(conn, table: str) -> int:
    return int(conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])


def _prune_derived(conn, chunks: list[SemanticChunk]) -> None:
    current_keys = {chunk.chunk_key for chunk in chunks}

    if not current_keys:
        conn.execute("DELETE FROM embeddings")
        conn.execute("DELETE FROM embedding_jobs")
        vec_index_repository.clear(conn)
        return

    placeholders = ",".join("?" * len(current_keys))
    conn.execute(
        f"DELETE FROM embeddings WHERE chunk_id NOT IN ({placeholders})",
        list(current_keys),
    )
    conn.execute(
        f"DELETE FROM embedding_jobs WHERE chunk_key NOT IN ({placeholders})",
        list(current_keys),
    )
    vec_index_repository.prune_not_in(conn, current_keys)


def load_embedding_cache(db_path: str) -> dict[str, np.ndarray]:
    conn = db.connect(db_path)

    try:
        schema.create_schema(conn)
        return embedding_repository.load_embedding_cache(conn)
    finally:
        conn.close()


def search_lexical(db_path: str, query: str, *, limit: int = 10) -> list[FtsHit]:
    conn = db.connect(db_path)

    try:
        schema.create_schema(conn)
        return chunk_fts_repository.search(conn, query, limit=limit)
    finally:
        conn.close()


def load_chunk_vectors(
    db_path: str,
) -> list[tuple[SemanticChunk, np.ndarray]]:
    """Every chunk that has an embedding, paired with it."""
    conn = db.connect(db_path)

    try:
        schema.create_schema(conn)

        chunks_by_key = {
            chunk.chunk_key: chunk for chunk in chunk_repository.fetch_all(conn)
        }

        return [
            (chunks_by_key[chunk_key], vector)
            for chunk_key, vector in embedding_repository.fetch_all(conn).items()
            if chunk_key in chunks_by_key
        ]
    finally:
        conn.close()


def load_file_states(db_path: str) -> list[FileState]:
    conn = db.connect(db_path)

    try:
        schema.create_schema(conn)
        return file_state_repository.fetch_all(conn)
    finally:
        conn.close()


def load_index(db_path: str) -> BuildResult:
    conn = db.connect(db_path)

    try:
        documents = document_repository.fetch_all(conn)
        symbols = symbol_repository.fetch_all(conn)
        stored_imports = import_repository.fetch_all(conn)
        exports = export_repository.fetch_all(conn)
        references = reference_repository.fetch_all(conn)
        relationships = relationship_repository.fetch_all(conn)
        chunks = chunk_repository.fetch_all(conn)

        symbols_by_id = {symbol.symbol_id: symbol for symbol in symbols}
        documents_by_id = {document.document_id: document for document in documents}
        references_by_id = {
            reference.reference_id: reference for reference in references
        }
        imports_by_id = {stored.import_id: stored for stored in stored_imports}

        resolved_references = resolved_reference_repository.fetch_all(
            conn,
            references_by_id=references_by_id,
            symbols_by_id=symbols_by_id,
        )
        resolved_imports = resolved_import_repository.fetch_all(
            conn,
            imports_by_id=imports_by_id,
            documents_by_id=documents_by_id,
            symbols_by_id=symbols_by_id,
        )

        result = BuildResult(
            documents=documents,
            symbols=symbols,
            import_references=[stored.import_reference for stored in stored_imports],
            exports=exports,
            resolved_import_references=resolved_imports,
            references=references,
            resolved_references=resolved_references,
            relationships=relationships,
            chunks=chunks,
        )

        result.symbol_index.add_many(symbols)
        result.graph.add_symbols(symbols)
        result.graph.add_relationships(relationships)

        return result
    finally:
        conn.close()


def _clear_all(conn) -> None:
    for table in _TABLES_IN_DEPENDENCY_ORDER:
        conn.execute(f'DELETE FROM "{table}"')


def _clear_analysis_tables(conn) -> None:
    """Reset tables whose row ids are not stable across runs.

    Imports and exports use autoincrement ids, and references/resolutions
    hang off them, so the merged full result is re-inserted from scratch
    each run. These tables hold small rows; the expensive content
    (documents, symbols, chunk text) stays in place.
    """
    for table in (
        "resolved_imports",
        "resolved_references",
        "relationships",
        "references",
        "imports",
        "exports",
    ):
        conn.execute(f'DELETE FROM "{table}"')


def _purge_paths(conn, paths: frozenset[str] | set[str]) -> None:
    """Remove every trace of `paths`, preserving still-current chunks."""
    if not paths:
        return

    path_list = list(paths)
    placeholders = ",".join("?" * len(path_list))

    chunk_rows = conn.execute(
        f"SELECT chunk_id FROM chunks WHERE relative_path IN ({placeholders})",
        path_list,
    ).fetchall()
    chunk_ids = [row["chunk_id"] for row in chunk_rows]

    if chunk_ids:
        key_placeholders = ",".join("?" * len(chunk_ids))
        conn.execute(
            f"DELETE FROM chunks_fts WHERE chunk_id IN ({key_placeholders})",
            chunk_ids,
        )
        vec_index_repository.delete_keys(conn, chunk_ids)
        conn.execute(
            f"DELETE FROM embeddings WHERE chunk_id IN ({key_placeholders})",
            chunk_ids,
        )
        conn.execute(
            f"DELETE FROM embedding_jobs WHERE chunk_key IN ({key_placeholders})",
            chunk_ids,
        )

    # Cascades wipe symbols, imports, exports, references, resolutions,
    # relationships, and chunks belonging to these documents.
    conn.execute(
        f"DELETE FROM documents WHERE relative_path IN ({placeholders})",
        path_list,
    )
    conn.execute(
        f"DELETE FROM file_state WHERE relative_path IN ({placeholders})",
        path_list,
    )


def _refresh_fts_keys(conn, current_keys: set[str]) -> None:
    """FTS rows for current chunks are rewritten; drop the stale copies.

    Untouched chunks keep their existing FTS rows only if their keys are
    here - so this deletes exactly the rows about to be reinserted.
    """
    if not current_keys:
        return

    placeholders = ",".join("?" * len(current_keys))
    conn.execute(
        f"DELETE FROM chunks_fts WHERE chunk_id IN ({placeholders})",
        list(current_keys),
    )
