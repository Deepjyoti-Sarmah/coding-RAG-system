import numpy as np

from models.build_result import BuildResult
from models.entities.fts_hit import FtsHit
from models.file_state import FileState
from retrieval.context_builder import ContextPack, build_context_pack
from retrieval.hybrid_retriever import HybridRetriever
from retrieval.numpy_vector_store import NumpyVectorStore
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
) -> None:
    conn = db.connect(db_path)

    try:
        schema.create_schema(conn)

        with db.transaction(conn):
            _clear_all(conn)

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


def _prune_derived(conn, chunks: list) -> None:
    current_keys = {chunk.chunk_key for chunk in chunks}

    if not current_keys:
        conn.execute("DELETE FROM embeddings")
        conn.execute("DELETE FROM embedding_jobs")
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


def load_vector_store(db_path: str) -> NumpyVectorStore:
    conn = db.connect(db_path)

    try:
        schema.create_schema(conn)
        chunks_by_key = {
            chunk.chunk_key: chunk for chunk in chunk_repository.fetch_all(conn)
        }
        vectors = embedding_repository.fetch_all(conn)
        entries = [
            (chunks_by_key[chunk_key], vector)
            for chunk_key, vector in vectors.items()
            if chunk_key in chunks_by_key
        ]
        return NumpyVectorStore(entries)
    finally:
        conn.close()


def build_hybrid_retriever(
    db_path: str,
    provider=None,
) -> HybridRetriever:
    result = load_index(db_path)

    vector_store = load_vector_store(db_path) if provider is not None else None
    embed = provider.embed_query if provider is not None else None

    return HybridRetriever(
        symbol_index=result.symbol_index,
        graph=result.graph,
        fts_search=lambda query, limit: search_lexical(db_path, query, limit=limit),
        vector_store=vector_store,
        embed=embed,
        resolved_imports=result.resolved_import_references,
        exports=result.exports,
    )


def build_context_pack_from_index(
    db_path: str,
    query: str,
    *,
    token_budget: int,
    provider=None,
    top_k: int = 5,
) -> ContextPack:
    result = load_index(db_path)
    retriever = build_hybrid_retriever(db_path, provider=provider)

    retrieval = retriever.retrieve(query, top_k=top_k)

    symbols_by_key = {symbol.stable_key: symbol for symbol in result.symbols}

    return build_context_pack(
        retrieval.candidates,
        query=query,
        graph=result.graph,
        symbols_by_key=symbols_by_key,
        token_budget=token_budget,
    )


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
