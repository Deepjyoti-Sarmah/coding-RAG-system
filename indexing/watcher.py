"""Filesystem watcher that keeps the index fresh.

Watches a repository and re-runs the incremental indexer after edits go
quiet for a debounce window. Writes to the index database itself (the
`.sg` directory) are ignored so indexing cannot trigger itself.
"""

import threading
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from embeddings.provider import EmbeddingProvider
from indexing.embedding_queue import run_embedding_worker
from indexing.indexer import reindex_index

DEFAULT_DEBOUNCE_SECONDS = 0.5


class _DebouncedReindexer(FileSystemEventHandler):
    def __init__(
        self,
        root: str,
        db_path: str,
        *,
        debounce_seconds: float,
        provider: EmbeddingProvider | None,
        embed_limit: int | None = 200,
        on_report,
    ) -> None:
        super().__init__()
        self._root = root
        self._db_path = db_path
        self._debounce_seconds = debounce_seconds
        self._provider = provider
        self._embed_limit = embed_limit
        self._on_report = on_report
        self._index_dir = Path(db_path).parent.resolve()
        self._lock = threading.Lock()
        self._timer: threading.Timer | None = None

    def on_any_event(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return

        source = str(event.src_path or "")

        # Compare normalized paths instead of string prefixes. This works
        # across POSIX and Windows separators and avoids treating a sibling
        # path such as `.sg-backup` as the index directory.
        try:
            Path(source).resolve().relative_to(self._index_dir)
        except ValueError:
            pass
        else:
            return

        with self._lock:
            if self._timer is not None:
                self._timer.cancel()

            self._timer = threading.Timer(
                self._debounce_seconds,
                self._reindex,
            )
            self._timer.daemon = True
            self._timer.start()

    def _reindex(self) -> None:
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        report = reindex_index(self._db_path, self._root)

        if self._provider is not None:
            run_embedding_worker(self._db_path, self._provider, limit=self._embed_limit)

        if report.parsed_files:
            self._on_report(report)


def watch_repository(
    root: str,
    db_path: str,
    *,
    provider: EmbeddingProvider | None = None,
    debounce_seconds: float = DEFAULT_DEBOUNCE_SECONDS,
    embed_limit: int | None = 200,
    on_report=print,
) -> None:
    """Block while watching `root`; Ctrl+C stops the watcher."""
    handler = _DebouncedReindexer(
        root,
        db_path,
        debounce_seconds=debounce_seconds,
        provider=provider,
        embed_limit=embed_limit,
        on_report=on_report,
    )

    observer = Observer()
    observer.schedule(handler, root, recursive=True)
    observer.start()

    try:
        observer.join()
    except KeyboardInterrupt:
        pass
    finally:
        observer.stop()
        observer.join()
