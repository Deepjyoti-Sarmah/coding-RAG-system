from models.entities.documents import Document
from models.entities.resolved_import_reference import ResolvedImportReference
from models.entities.symbols import Symbol
from storage.repositories import (
    document_repository,
    import_repository,
    symbol_repository,
)
from storage.repositories.import_repository import StoredImport


def insert_many(
    conn,
    resolved_imports: list[ResolvedImportReference],
    ids_by_import_object: dict[int, int],
) -> None:
    for resolved in resolved_imports:
        import_id = ids_by_import_object.get(id(resolved.import_reference))

        if import_id is None:
            continue

        conn.execute(
            """
            INSERT OR REPLACE INTO resolved_imports (import_id, target_document_id, target_symbol_id)
            VALUES (?, ?, ?)
            """,
            (
                import_id,
                resolved.target_document.document_id,
                (
                    resolved.target_symbol.symbol_id
                    if resolved.target_symbol is not None
                    else None
                ),
            ),
        )


def fetch_all(
    conn,
    *,
    imports_by_id: dict[int, StoredImport],
    documents_by_id: dict[str, Document],
    symbols_by_id: dict[str, Symbol],
) -> list[ResolvedImportReference]:
    rows = conn.execute(
        """
        SELECT import_id, target_document_id, target_symbol_id
        FROM resolved_imports
        """
    ).fetchall()

    result: list[ResolvedImportReference] = []

    for row in rows:
        stored_import = imports_by_id.get(row["import_id"])
        target_document = documents_by_id.get(row["target_document_id"])

        if stored_import is None or target_document is None:
            continue

        result.append(
            ResolvedImportReference(
                import_reference=stored_import.import_reference,
                target_document=target_document,
                target_symbol=symbols_by_id.get(row["target_symbol_id"]),
            )
        )

    return result


def fetch_by_import_ids(
    conn,
    import_ids: list[int],
) -> dict[int, ResolvedImportReference]:
    """Resolved imports for specific import rows, keyed by import_id."""
    if not import_ids:
        return {}

    stored = import_repository.fetch_by_ids(conn, import_ids)
    stored_by_id = {stored.import_id: stored for stored in stored}

    documents = document_repository.fetch_all(conn)
    documents_by_id = {document.document_id: document for document in documents}
    symbols_by_id = {
        symbol.symbol_id: symbol for symbol in symbol_repository.fetch_all(conn)
    }

    placeholders = ",".join("?" * len(import_ids))
    rows = conn.execute(
        f"""
        SELECT import_id, target_document_id, target_symbol_id
        FROM resolved_imports
        WHERE import_id IN ({placeholders})
        """,
        import_ids,
    ).fetchall()

    resolved_by_id: dict[int, ResolvedImportReference] = {}

    for row in rows:
        stored_import = stored_by_id.get(row["import_id"])
        target_document = documents_by_id.get(row["target_document_id"])

        if stored_import is None or target_document is None:
            continue

        resolved_by_id[row["import_id"]] = ResolvedImportReference(
            import_reference=stored_import.import_reference,
            target_document=target_document,
            target_symbol=symbols_by_id.get(row["target_symbol_id"]),
        )

    return resolved_by_id
