from dataclasses import dataclass

import numpy as np

from embeddings.provider import EmbeddingProvider
from indexing.embedding_store import embed_chunks
from storage import db, schema
from storage.index_store import load_embedding_cache
from storage.repositories import (
    chunk_repository,
    embedding_job_repository,
    embedding_repository,
)


@dataclass(slots=True)
class EmbeddingRunReport:
    claimed: int = 0
    done: int = 0
    reused: int = 0
    stale: int = 0
    failed: int = 0


def enqueue_embedding_jobs(db_path: str, chunks: list) -> int:
    conn = db.connect(db_path)

    try:
        schema.create_schema(conn)

        with db.transaction(conn):
            for chunk in chunks:
                embedding_job_repository.enqueue(
                    conn,
                    chunk.chunk_key,
                    chunk.content_hash,
                )

        return len(chunks)
    finally:
        conn.close()


def run_embedding_worker(
    db_path: str,
    provider: EmbeddingProvider,
    *,
    limit: int | None = None,
) -> EmbeddingRunReport:
    conn = db.connect(db_path)
    report = EmbeddingRunReport()

    try:
        schema.create_schema(conn)

        jobs = embedding_job_repository.claim(conn, limit=limit)

        if not jobs:
            return report

        report.claimed = len(jobs)

        claimed_keys = {job.chunk_key for job in jobs}
        chunks_by_key = {
            chunk.chunk_key: chunk
            for chunk in chunk_repository.fetch_all(conn)
            if chunk.chunk_key in claimed_keys
        }

        embeddable: list = []
        stale: list[tuple[str, str]] = []
        orphaned: list[str] = []

        for job in jobs:
            chunk = chunks_by_key.get(job.chunk_key)

            if chunk is None:
                orphaned.append(job.chunk_key)
            elif chunk.content_hash != job.content_hash:
                stale.append((job.chunk_key, chunk.content_hash))
            else:
                embeddable.append(chunk)

        report.stale = len(stale) + len(orphaned)

        embeddings_by_key: dict[str, np.ndarray] = {}

        try:
            if embeddable:
                embeddings_by_key, missing = embed_chunks(
                    embeddable,
                    provider,
                    load_embedding_cache(db_path),
                )
                report.done = len(embeddable)
                report.reused = len(embeddable) - missing
        except Exception as exc:  # noqa: BLE001 - any provider failure marks jobs failed instead of crashing the run
            with db.transaction(conn):
                for chunk in embeddable:
                    embedding_job_repository.mark_failed(conn, chunk.chunk_key, str(exc))

            report.failed = len(embeddable)
            return report

        with db.transaction(conn):
            if embeddings_by_key:
                embedding_repository.upsert(conn, embeddings_by_key)

            for chunk in embeddable:
                embedding_job_repository.mark_done(conn, chunk.chunk_key)

            for chunk_key, content_hash in stale:
                embedding_job_repository.reenqueue(conn, chunk_key, content_hash)

            for chunk_key in orphaned:
                conn.execute(
                    "DELETE FROM embedding_jobs WHERE chunk_key = ?",
                    (chunk_key,),
                )

        return report
    finally:
        conn.close()


def queue_status(db_path: str) -> dict[str, int]:
    conn = db.connect(db_path)

    try:
        schema.create_schema(conn)
        return embedding_job_repository.status_counts(conn)
    finally:
        conn.close()