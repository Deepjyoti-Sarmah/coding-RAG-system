"""Generation-keyed cache for loaded indexes.

Materializing a full index (documents, symbols, references, relationships)
out of SQLite is expensive, and every query used to pay it. The index
metadata table carries a monotonically increasing `generation` that bumps
on every successful persist, so it doubles as a free invalidation key:
probing it is one single-row SELECT, and any write - from this process
(watcher reindex) or an external one (`sg index` in another terminal) -
changes the generation and forces the next load to refresh.
"""

import threading

from analysis.build_result import BuildResult
from storage.index_store import current_generation, load_index


class _CacheEntry:
    __slots__ = ("generation", "result")

    def __init__(self, generation: int, result: BuildResult) -> None:
        self.generation = generation
        self.result = result


_lock = threading.Lock()
_entries: dict[str, _CacheEntry] = {}


def load_index_cached(db_path: str) -> BuildResult:
    """Return the index for `db_path`, reloading only when its generation changed."""
    while True:
        entry = _entries.get(db_path)

        if entry is not None and current_generation(db_path) == entry.generation:
            return entry.result

        _reload(db_path)


def clear() -> None:
    with _lock:
        _entries.clear()


def _reload(db_path: str) -> None:
    with _lock:
        entry = _entries.get(db_path)

        if entry is not None and current_generation(db_path) == entry.generation:
            return

        result = load_index(db_path)
        _entries[db_path] = _CacheEntry(current_generation(db_path), result)
