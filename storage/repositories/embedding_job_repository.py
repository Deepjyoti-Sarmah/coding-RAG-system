import time

from models.entities.embedding_job import EmbeddingJob
from models.entities.embedding_job_status import EmbeddingJobStatus


def enqueue(conn, chunk_key: str, content_hash: str) -> None:
    conn.execute(
        """
        INSERT INTO embedding_jobs (chunk_key, content_hash, status, attempts, error)
        VALUES (?, ?, ?, 0, NULL)
        ON CONFLICT(chunk_key) DO UPDATE SET
            content_hash = excluded.content_hash,
            status = CASE
                WHEN embedding_jobs.status = 'FAILED' THEN 'FAILED'
                WHEN embedding_jobs.status = 'DONE'
                     AND embedding_jobs.content_hash = excluded.content_hash
                    THEN 'DONE'
                ELSE 'PENDING'
            END
        """,
        (chunk_key, content_hash, EmbeddingJobStatus.PENDING.value),
    )


MAX_ATTEMPTS = 3
LEASE_SECONDS = 300


def claim(conn, limit: int | None = None) -> list[EmbeddingJob]:
    now = int(time.time())
    lease_cutoff = now - LEASE_SECONDS
    sql = """
        UPDATE embedding_jobs
        SET status = ?, attempts = attempts + 1, claimed_at = ?
        WHERE chunk_key IN (
            SELECT chunk_key FROM embedding_jobs
            WHERE (
                status IN (?, ?) AND attempts < ?
            ) OR (
                status = ? AND claimed_at IS NOT NULL AND claimed_at < ?
                AND attempts < ?
            )
            ORDER BY chunk_key
            LIMIT ?
        )
        RETURNING chunk_key, content_hash, status, attempts, error, claimed_at
    """
    rows = conn.execute(
        sql,
        (
            EmbeddingJobStatus.PROCESSING.value,
            now,
            EmbeddingJobStatus.PENDING.value,
            EmbeddingJobStatus.FAILED.value,
            MAX_ATTEMPTS,
            EmbeddingJobStatus.PROCESSING.value,
            lease_cutoff,
            MAX_ATTEMPTS,
            limit if limit is not None else -1,
        ),
    ).fetchall()

    return [_row_to_job(row) for row in rows]


def reenqueue(conn, chunk_key: str, content_hash: str | None = None) -> None:
    if content_hash is None:
        conn.execute(
            """
            UPDATE embedding_jobs
            SET status = ?, error = NULL
            WHERE chunk_key = ?
            """,
            (EmbeddingJobStatus.PENDING.value, chunk_key),
        )
        return

    conn.execute(
        """
        UPDATE embedding_jobs
        SET status = ?, content_hash = ?, error = NULL
        WHERE chunk_key = ?
        """,
        (EmbeddingJobStatus.PENDING.value, content_hash, chunk_key),
    )


def mark_done(conn, chunk_key: str) -> None:
    conn.execute(
        """
        UPDATE embedding_jobs
        SET status = ?, error = NULL
        WHERE chunk_key = ?
        """,
        (EmbeddingJobStatus.DONE.value, chunk_key),
    )


def mark_failed(conn, chunk_key: str, error: str) -> None:
    conn.execute(
        """
        UPDATE embedding_jobs
        SET status = ?, error = ?
        WHERE chunk_key = ?
        """,
        (EmbeddingJobStatus.FAILED.value, error, chunk_key),
    )


def status_counts(conn) -> dict[str, int]:
    rows = conn.execute(
        "SELECT status, COUNT(*) AS n FROM embedding_jobs GROUP BY status"
    ).fetchall()

    counts = {row["status"]: row["n"] for row in rows}
    # count exhausted jobs separately (FAILED with attempts >= MAX_ATTEMPTS)
    exhausted = conn.execute(
        "SELECT COUNT(*) AS n FROM embedding_jobs WHERE status = ? AND attempts >= ?",
        (EmbeddingJobStatus.FAILED.value, MAX_ATTEMPTS),
    ).fetchone()
    if exhausted and exhausted["n"]:
        counts["exhausted"] = exhausted["n"]
    return counts


def fetch_all(conn) -> list[EmbeddingJob]:
    rows = conn.execute(
        """
        SELECT chunk_key, content_hash, status, attempts, error, claimed_at
        FROM embedding_jobs
        ORDER BY chunk_key
        """
    ).fetchall()

    return [_row_to_job(row) for row in rows]


def _row_to_job(row) -> EmbeddingJob:
    claimed_at = None
    try:
        claimed_at = row["claimed_at"]
    except (KeyError, IndexError):
        pass
    return EmbeddingJob(
        chunk_key=row["chunk_key"],
        content_hash=row["content_hash"],
        status=row["status"],
        attempts=row["attempts"],
        error=row["error"],
        claimed_at=claimed_at,
    )