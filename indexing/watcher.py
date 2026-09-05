"""Filesystem watcher that keeps the index fresh.

Watches a repository and re-runs the incremental indexer after edits go
quiet for a debounce window. Writes to the index database itself (the
`.sg` directory) are ignored so indexing cannot trigger itself.
"""

import threading
import time
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
        # Generation increments on every filesystem event. Timer callbacks
        # capture the generation they were scheduled for; a callback whose
        # generation is stale was superseded by a newer event and must not
        # run. This collapses bursts deterministically without relying on
        # wall-clock timing.
        self._generation = 0
        # True while a reindex is running on a timer thread. Events arriving
        # during a run set _pending so they collapse into exactly one
        # follow-up reindex instead of running concurrently.
        self._running = False
        self._pending = False

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
            self._generation += 1
            generation = self._generation
            if self._running:
                # A reindex is in flight; coalesce this event (and any
                # further ones during the run) into a single follow-up.
                self._pending = True
                return
            if self._timer is not None:
                self._timer.cancel()

            self._timer = threading.Timer(
                self._debounce_seconds,
                self._reindex,
                args=(generation,),
            )
            self._timer.daemon = True
            self._timer.start()

    def _reindex(self, generation: int) -> None:
        with self._lock:
            # Superseded by a newer event: the newer timer owns the reindex.
            # (Cancel is best-effort; this covers the race where the callback
            # had already started when the newer event arrived.)
            if generation != self._generation:
                return
            self._timer = None
            self._running = True

        try:
            Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
            report = reindex_index(self._db_path, self._root)

            if self._provider is not None:
                run_embedding_worker(
                    self._db_path, self._provider, limit=self._embed_limit
                )

            if report.parsed_files:
                self._on_report(report)
        finally:
            with self._lock:
                self._running = False
                if self._pending:
                    self._pending = False
                    follow_up = self._generation
                    if self._timer is not None:
                        self._timer.cancel()
                    self._timer = threading.Timer(
                        self._debounce_seconds,
                        self._reindex,
                        args=(follow_up,),
                    )
                    self._timer.daemon = True
                    self._timer.start()

    def wait_for_idle(self, timeout: float = 10.0) -> bool:
        """Block until no reindex is running and no timer is pending.

        Returns True if idle was reached, False on timeout. Tests should
        prefer this over joining ``_timer`` directly: joining a single
        timer snapshot misses follow-up timers scheduled from the
        reindex thread.
        """
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with self._lock:
                timer = self._timer
                running = self._running
                pending = self._pending
            alive = timer is not None and timer.is_alive()
            if not running and not alive and not pending:
                # Give a final quiet-window check so an event arriving
                # just now still gets observed before we return.
                time.sleep(min(self._debounce_seconds, 0.05))
                with self._lock:
                    timer = self._timer
                    running = self._running
                    pending = self._pending
                alive = timer is not None and timer.is_alive()
                if not running and not alive and not pending:
                    return True
            time.sleep(0.02)
        return False


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
