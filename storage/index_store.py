import storage.db as db
import storage.schema as schema
from models.build_result import BuildResult
from storage.repositories import (
    document_repository,
    export_repository,
    import_repository,
    reference_repository,
    relationship_repository,
    resolved_import_repository,
    resolved_reference_repository,
    symbol_repository,
)

_TABLES_IN_DEPENDENCY_ORDER = [
    "embeddings",
    "resolved_imports",
    "resolved_references",
    "relationships",
    "references",
    "exports",
    "imports",
    "chunks",
    "symbols",
    "documents",
    "file_state",
]


def persist_index(
    db_path: str,
    result: BuildResult,
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

        symbols_by_id = {symbol.symbol_id: symbol for symbol in symbols}
        documents_by_id = {document.document_id: document for document in documents}
        references_by_id = {reference.reference_id: reference for reference in references}
        imports_by_id = {
            stored.import_id: stored for stored in stored_imports
        }

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
            import_references=[
                stored.import_reference for stored in stored_imports
            ],
            exports=exports,
            resolved_import_references=resolved_imports,
            references=references,
            resolved_references=resolved_references,
            relationships=relationships,
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
