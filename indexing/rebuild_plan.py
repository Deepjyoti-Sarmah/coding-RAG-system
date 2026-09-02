from typing import Any

"""Deciding what an incremental run must redo.

An incremental rebuild answers two questions before it touches any
source: which files need re-parsing, and which *unchanged* files need
their names resolved again because something they import moved. This
module answers both, so the decision can be tested without indexing a
repository.

The second question is the subtle one. A file must be re-resolved when
anything it imports changes shape:

- a changed file whose exported interface differs from last run
- a deleted file
- a *newly added* file, which may satisfy imports that previously had
  no target at all

Everything else keeps last run's resolutions.
"""

from collections import defaultdict
from dataclasses import dataclass

from analysis.build_result import BuildResult
from indexing.diff import FileChange, ScanResult, interface_fingerprint
from models.entities.documents import Document


@dataclass(slots=True, frozen=True)
class FilePartition:
    """Every current path, bucketed by how this run must treat it."""

    changes: dict[str, FileChange]
    current: frozenset[str]
    rebuild: frozenset[str]
    deleted: frozenset[str]
    new: frozenset[str]
    changed: frozenset[str]

    @property
    def has_work(self) -> bool:
        return bool(self.rebuild or self.deleted)


@dataclass(slots=True, frozen=True)
class RebuildPlan:
    """`FilePartition` plus the resolution decision layered on top."""

    partition: FilePartition
    invalidation_sources: frozenset[str]
    reresolve: frozenset[str]
    untouched: frozenset[str]


@dataclass(slots=True)
class PreviousSnapshot:
    """Last run's index, indexed by path for reuse lookups."""

    result: BuildResult
    docs_by_path: dict[str, Document]
    docs_by_id: dict[str, Document]
    symbols_by_path: dict[str, list[Any]]
    imports_by_path: dict[str, list[Any]]
    exports_by_path: dict[str, list[Any]]
    references_by_path: dict[str, list[Any]]
    resolved_references_by_path: dict[str, list[Any]]
    resolved_imports_by_path: dict[str, list[Any]]


def partition_files(scan: ScanResult) -> FilePartition:
    changes = scan.changes

    def paths_where(*kinds: FileChange) -> frozenset[str]:
        return frozenset(
            path for path, change in changes.items() if change in kinds
        )

    return FilePartition(
        changes=changes,
        current=frozenset(scan.current),
        rebuild=paths_where(FileChange.NEW, FileChange.CHANGED),
        deleted=paths_where(FileChange.DELETED),
        new=paths_where(FileChange.NEW),
        changed=paths_where(FileChange.CHANGED),
    )


def build_previous_snapshot(previous: BuildResult) -> PreviousSnapshot:
    docs_by_id = {d.document_id: d for d in previous.documents}

    return PreviousSnapshot(
        result=previous,
        docs_by_path={d.relative_path: d for d in previous.documents},
        docs_by_id=docs_by_id,
        symbols_by_path=group_by_path(previous.symbols, docs_by_id),
        imports_by_path=group_by_path(previous.import_references, docs_by_id),
        exports_by_path=group_by_path(previous.exports, docs_by_id),
        references_by_path=group_by_path(previous.references, docs_by_id),
        resolved_references_by_path=group_by_path(
            previous.resolved_references,
            docs_by_id,
            document_id=lambda r: r.reference.document_id,
        ),
        resolved_imports_by_path=group_by_path(
            previous.resolved_import_references,
            docs_by_id,
            document_id=lambda r: r.import_reference.document_id,
        ),
    )


def plan_rebuild(
    *,
    partition: FilePartition,
    snapshot: PreviousSnapshot,
    importers: dict[str, set[str]],
    documents_by_id: dict[str, Document],
    fresh_exports: list[Any],
    fresh_symbols: list[Any],
) -> RebuildPlan:
    """Decide which unchanged files still need re-resolution."""
    interface_changed = _interface_changed_paths(
        changed_paths=partition.changed,
        snapshot=snapshot,
        fresh_exports=fresh_exports,
        fresh_symbols=fresh_symbols,
    )

    # A new file is an invalidation source in its own right: it can
    # satisfy imports that previously resolved to nothing. It cannot go
    # through the fingerprint comparison above, which needs a previous
    # interface to diff against.
    invalidation_sources = interface_changed | partition.deleted | partition.new

    reresolve = _importer_paths(
        invalidation_sources=invalidation_sources,
        importers=importers,
        documents_by_id=documents_by_id,
    )

    return RebuildPlan(
        partition=partition,
        invalidation_sources=invalidation_sources,
        reresolve=reresolve,
        untouched=partition.current - partition.rebuild - reresolve,
    )


def group_by_path(
    entities: list[Any],
    docs_by_id: dict[str, Document],
    *,
    document_id=lambda entity: entity.document_id,
) -> dict[str, list[Any]]:
    grouped: dict[str, list[Any]] = defaultdict(list)

    for entity in entities:
        document = docs_by_id.get(document_id(entity))

        if document is None:
            continue

        grouped[document.relative_path].append(entity)

    return dict(grouped)


def _interface_changed_paths(
    *,
    changed_paths: frozenset[str],
    snapshot: PreviousSnapshot,
    fresh_exports: list[Any],
    fresh_symbols: list[Any],
) -> frozenset[str]:
    changed: set[str] = set()

    for path in changed_paths:
        doc_id = snapshot.docs_by_path[path].document_id

        current = interface_fingerprint(
            exports=[e for e in fresh_exports if e.document_id == doc_id],
            symbols=[s for s in fresh_symbols if s.document_id == doc_id],
        )
        previous = interface_fingerprint(
            exports=snapshot.exports_by_path.get(path, []),
            symbols=snapshot.symbols_by_path.get(path, []),
        )

        if previous != current:
            changed.add(path)

    return frozenset(changed)


def _importer_paths(
    *,
    invalidation_sources: frozenset[str],
    importers: dict[str, set[str]],
    documents_by_id: dict[str, Document],
) -> frozenset[str]:
    """Transitive closure over importers (BFS).

    If A is invalidated and B imports A, B must be re-resolved. If C
    imports B, C also becomes stale — but only because B's *resolution*
    may change, not because A's fingerprint directly touches C. We
    therefore walk the importer graph transitively, seeding with
    invalidation_sources. This is bounded because the graph is small and
    acyclic in practice; visited guards prevent loops.
    """
    # Build reverse map: module_path -> set[document_id] already given as `importers`
    # Need also to map document relative_path back to its module path for next hop.
    # However `importers` keys are module_paths (e.g. "src/auth"), not relative_paths.
    # First, collect direct importers, then iteratively expand.
    visited_sources: set[str] = set()
    queue: list[str] = list(invalidation_sources)
    result: set[str] = set()

    # To support transitive walk we need a way to go from importer document
    # -> its own module path -> its importers. Derive module path as
    # relative_path without extension.
    def module_paths_for_relative(relative_path: str) -> list[str]:
        # e.g. "src/auth.ts" -> ["src/auth", "src/auth.ts"] candidates that may appear as keys
        if "." in relative_path:
            without_ext = relative_path.rsplit(".", 1)[0]
            return [without_ext, relative_path]
        return [relative_path]

    while queue:
        source = queue.pop(0)
        if source in visited_sources:
            continue
        visited_sources.add(source)
        for importer_id in importers.get(source, set()):
            document = documents_by_id.get(importer_id)
            if document is None:
                continue
            relative = document.relative_path
            if relative not in result:
                result.add(relative)
                # Enqueue this importer as a new source for transitive importers
                for mp in module_paths_for_relative(relative):
                    if mp not in visited_sources:
                        queue.append(mp)
    # Exclude invalidation sources themselves — they are already in rebuild set
    return frozenset(result - set(invalidation_sources))
