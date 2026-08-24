from dataclasses import dataclass

from models.entities.import_references import ImportReference
from storage._rows import location_columns, source_location_from_row


@dataclass(slots=True)
class StoredImport:
    import_id: int
    import_reference: ImportReference


def insert_many(
    conn,
    import_references: list[ImportReference],
) -> dict[int, int]:
    ids_by_object: dict[int, int] = {}

    for reference in import_references:
        cursor = conn.execute(
            """
            INSERT INTO imports (
                document_id, module_path, imported_name, local_name,
                start_line, end_line, start_byte, end_byte
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                reference.document_id,
                reference.module_path,
                reference.imported_name,
                reference.local_name,
                *location_columns(reference.location),
            ),
        )
        ids_by_object[id(reference)] = cursor.lastrowid

    return ids_by_object


def fetch_all(conn) -> list[StoredImport]:
    rows = conn.execute(
        """
        SELECT import_id, document_id, module_path, imported_name, local_name,
               start_line, end_line, start_byte, end_byte
        FROM imports
        """
    ).fetchall()

    return [_row_to_stored(row) for row in rows]


def fetch_by_ids(
    conn,
    import_ids: list[int],
) -> list[StoredImport]:
    if not import_ids:
        return []

    placeholders = ",".join("?" * len(import_ids))
    rows = conn.execute(
        f"""
        SELECT import_id, document_id, module_path, imported_name, local_name,
               start_line, end_line, start_byte, end_byte
        FROM imports
        WHERE import_id IN ({placeholders})
        """,
        import_ids,
    ).fetchall()

    return [_row_to_stored(row) for row in rows]


def fetch_for_relative_path(
    conn,
    relative_path: str,
) -> list[StoredImport]:
    rows = conn.execute(
        """
        SELECT i.import_id, i.document_id, i.module_path, i.imported_name,
               i.local_name, i.start_line, i.end_line, i.start_byte, i.end_byte
        FROM imports i
        JOIN documents d ON d.document_id = i.document_id
        WHERE d.relative_path = ?
        ORDER BY i.import_id
        """,
        (relative_path,),
    ).fetchall()

    return [_row_to_stored(row) for row in rows]


def _row_to_stored(row) -> StoredImport:
    return StoredImport(
        import_id=row["import_id"],
        import_reference=ImportReference(
            document_id=row["document_id"],
            module_path=row["module_path"],
            imported_name=row["imported_name"],
            local_name=row["local_name"],
            location=source_location_from_row(row),
        ),
    )
