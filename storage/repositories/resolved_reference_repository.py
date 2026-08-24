from models.entities.references import Reference
from models.entities.resolved_reference import ResolutionStatus, ResolvedReference
from models.entities.symbols import Symbol


def insert_many(conn, resolved_references: list[ResolvedReference]) -> None:
    conn.executemany(
        """
        INSERT OR REPLACE INTO resolved_references (reference_id, status, target_symbol_id)
        VALUES (?, ?, ?)
        """,
        [
            (
                resolved.reference.reference_id,
                resolved.status.value,
                (
                    resolved.target_symbol.symbol_id
                    if resolved.target_symbol is not None
                    else None
                ),
            )
            for resolved in resolved_references
        ],
    )


def fetch_all(
    conn,
    *,
    references_by_id: dict[str, Reference],
    symbols_by_id: dict[str, Symbol],
) -> list[ResolvedReference]:
    rows = conn.execute(
        """
        SELECT reference_id, status, target_symbol_id
        FROM resolved_references
        """
    ).fetchall()

    result: list[ResolvedReference] = []

    for row in rows:
        reference = references_by_id.get(row["reference_id"])

        if reference is None:
            continue

        target_symbol = symbols_by_id.get(row["target_symbol_id"])

        result.append(
            ResolvedReference(
                reference=reference,
                status=ResolutionStatus(row["status"]),
                target_symbol=target_symbol,
            )
        )

    return result
