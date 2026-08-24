import json

from models.entities.reference_kind import ReferenceKind
from models.entities.references import Reference
from storage._rows import location_columns, source_location_from_row


def insert_many(conn, references: list[Reference]) -> None:
    conn.executemany(
        """
        INSERT OR REPLACE INTO "references" (
            reference_id, document_id, name, kind, owner_symbol_id, path_json,
            start_line, end_line, start_byte, end_byte
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                reference.reference_id,
                reference.document_id,
                reference.name,
                reference.kind.value,
                reference.owner_symbol_id,
                json.dumps(list(reference.path)),
                *location_columns(reference.location),
            )
            for reference in references
        ],
    )


def fetch_all(conn) -> list[Reference]:
    rows = conn.execute(
        """
        SELECT reference_id, document_id, name, kind, owner_symbol_id, path_json,
               start_line, end_line, start_byte, end_byte
        FROM "references"
        """
    ).fetchall()

    return [
        Reference(
            reference_id=row["reference_id"],
            document_id=row["document_id"],
            name=row["name"],
            kind=ReferenceKind(row["kind"]),
            owner_symbol_id=row["owner_symbol_id"],
            path=tuple(json.loads(row["path_json"])),
            location=source_location_from_row(row),
        )
        for row in rows
    ]
