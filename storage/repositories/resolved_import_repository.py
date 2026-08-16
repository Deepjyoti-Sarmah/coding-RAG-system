from models.entities.documents import Document
from models.entities.resolved_import_reference import ResolvedImportReference
from models.entities.symbols import Symbol
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
            INSERT INTO resolved_imports (import_id, target_document_id, target_symbol_id)
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
