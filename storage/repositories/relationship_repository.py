from collections.abc import Sequence

from models.relationships.relationship_kind import RelationshipKind
from models.relationships.relationships import Relationship


def insert_many(conn, relationships: Sequence[Relationship]) -> None:
    conn.executemany(
        """
        INSERT INTO relationships (source_symbol_id, target_symbol_id, kind)
        VALUES (?, ?, ?)
        ON CONFLICT(source_symbol_id, target_symbol_id, kind) DO NOTHING
        """,
        [
            (
                relationship.source_symbol_id,
                relationship.target_symbol_id,
                relationship.kind.value,
            )
            for relationship in relationships
        ],
    )


def fetch_all(conn) -> list[Relationship]:
    rows = conn.execute(
        """
        SELECT source_symbol_id, target_symbol_id, kind
        FROM relationships
        """
    ).fetchall()

    return [
        Relationship(
            source_symbol_id=row["source_symbol_id"],
            target_symbol_id=row["target_symbol_id"],
            kind=RelationshipKind(row["kind"]),
        )
        for row in rows
    ]
