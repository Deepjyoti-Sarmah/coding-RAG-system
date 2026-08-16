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

    return [
        StoredImport(
            import_id=row["import_id"],
            import_reference=ImportReference(
                document_id=row["document_id"],
                module_path=row["module_path"],
                imported_name=row["imported_name"],
                local_name=row["local_name"],
                location=source_location_from_row(row),
            ),
        )
        for row in rows
    ]
