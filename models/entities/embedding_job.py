from dataclasses import dataclass


@dataclass(slots=True)
class EmbeddingJob:
    chunk_key: str
    content_hash: str
    status: str
    attempts: int = 0
    error: str | None = None
    claimed_at: int | None = None