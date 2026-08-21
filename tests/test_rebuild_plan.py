"""Unit tests for the incremental invalidation decision.

`plan_rebuild` decides which unchanged files must be resolved again.
Testing it directly - rather than only through `reindex_index` - means a
missing invalidation source shows up as a failing set comparison instead
of a stale resolution three layers away.
"""

import unittest

from indexing.diff import FileChange, ScannedFile, ScanResult
from indexing.rebuild_plan import (
    build_previous_snapshot,
    partition_files,
    plan_rebuild,
)
from models.build_result import BuildResult
from models.common.source_location import SourceLocation
from models.entities.documents import Document
from models.entities.exports import Export
from models.entities.symbol_kind import SymbolKind
from models.entities.symbols import Symbol

LOCATION = SourceLocation(
    start_line=1, end_line=1, start_byte=0, end_byte=1
)


def _document(path: str) -> Document:
    return Document(
        document_id=f"doc-{path}",
        absolute_path=f"/repo/{path}",
        relative_path=path,
        file_name=path,
        extension=".ts",
        language="typescript",
        size_bytes=1,
        line_count=1,
        content="",
    )


def _symbol(path: str, name: str, *, signature: str = "sig") -> Symbol:
    return Symbol(
        symbol_id=f"sym-{path}-{name}",
        document_id=f"doc-{path}",
        name=name,
        kind=SymbolKind.FUNCTION,
        relative_path=path,
        location=LOCATION,
        content="",
        qualified_name=name,
        signature_hash=signature,
        stable_key=f"{path}|typescript|{name}|function",
    )


def _export(path: str, name: str) -> Export:
    return Export(
        document_id=f"doc-{path}",
        exported_name=name,
        symbol_name=name,
        location=LOCATION,
    )


def _scan(changes: dict[str, FileChange]) -> ScanResult:
    current = {
        path: ScannedFile(
            file_path=None,
            relative_path=path,
            size_bytes=1,
            mtime_ns=1,
            content=None,
        )
        for path, change in changes.items()
        if change != FileChange.DELETED
    }

    return ScanResult(changes=changes, current=current)


def _snapshot(paths: list[str], exports: dict[str, list[str]] | None = None):
    exports = exports or {}
    previous = BuildResult()
    previous.documents = [_document(p) for p in paths]

    for path in paths:
        for name in exports.get(path, []):
            previous.symbols.append(_symbol(path, name))
            previous.exports.append(_export(path, name))

    return build_previous_snapshot(previous)


class TestPartitionFiles(unittest.TestCase):
    def test_buckets_every_change_kind(self):
        partition = partition_files(
            _scan(
                {
                    "new.ts": FileChange.NEW,
                    "edited.ts": FileChange.CHANGED,
                    "same.ts": FileChange.UNCHANGED,
                    "gone.ts": FileChange.DELETED,
                }
            )
        )

        self.assertEqual(partition.new, {"new.ts"})
        self.assertEqual(partition.changed, {"edited.ts"})
        self.assertEqual(partition.deleted, {"gone.ts"})
        self.assertEqual(partition.rebuild, {"new.ts", "edited.ts"})
        self.assertEqual(
            partition.current, {"new.ts", "edited.ts", "same.ts"}
        )
        self.assertTrue(partition.has_work)

    def test_all_unchanged_is_no_work(self):
        partition = partition_files(_scan({"a.ts": FileChange.UNCHANGED}))

        self.assertFalse(partition.has_work)


class TestPlanRebuild(unittest.TestCase):
    """`importer.ts` imports `target.ts` in every case below."""

    def _plan(self, changes, *, snapshot, fresh_exports, fresh_symbols):
        partition = partition_files(_scan(changes))
        documents = {
            f"doc-{p}": _document(p) for p in partition.current
        }

        return plan_rebuild(
            partition=partition,
            snapshot=snapshot,
            importers={"target.ts": {"doc-importer.ts"}},
            documents_by_id=documents,
            fresh_exports=fresh_exports,
            fresh_symbols=fresh_symbols,
        )

    def test_new_file_invalidates_its_importers(self):
        # The importer was indexed while target.ts did not exist, so its
        # import resolved to nothing and must be retried now.
        plan = self._plan(
            {"target.ts": FileChange.NEW, "importer.ts": FileChange.UNCHANGED},
            snapshot=_snapshot(["importer.ts"]),
            fresh_exports=[_export("target.ts", "helper")],
            fresh_symbols=[_symbol("target.ts", "helper")],
        )

        self.assertIn("target.ts", plan.invalidation_sources)
        self.assertEqual(plan.reresolve, {"importer.ts"})
        self.assertEqual(plan.untouched, set())

    def test_deleted_file_invalidates_its_importers(self):
        plan = self._plan(
            {
                "target.ts": FileChange.DELETED,
                "importer.ts": FileChange.UNCHANGED,
            },
            snapshot=_snapshot(
                ["target.ts", "importer.ts"], {"target.ts": ["helper"]}
            ),
            fresh_exports=[],
            fresh_symbols=[],
        )

        self.assertEqual(plan.reresolve, {"importer.ts"})

    def test_changed_body_with_identical_interface_does_not_invalidate(self):
        plan = self._plan(
            {
                "target.ts": FileChange.CHANGED,
                "importer.ts": FileChange.UNCHANGED,
            },
            snapshot=_snapshot(
                ["target.ts", "importer.ts"], {"target.ts": ["helper"]}
            ),
            fresh_exports=[_export("target.ts", "helper")],
            fresh_symbols=[_symbol("target.ts", "helper")],
        )

        self.assertEqual(plan.invalidation_sources, set())
        self.assertEqual(plan.reresolve, set())
        self.assertEqual(plan.untouched, {"importer.ts"})

    def test_changed_interface_invalidates_importers(self):
        plan = self._plan(
            {
                "target.ts": FileChange.CHANGED,
                "importer.ts": FileChange.UNCHANGED,
            },
            snapshot=_snapshot(
                ["target.ts", "importer.ts"], {"target.ts": ["helper"]}
            ),
            fresh_exports=[_export("target.ts", "renamed")],
            fresh_symbols=[_symbol("target.ts", "renamed")],
        )

        self.assertEqual(plan.invalidation_sources, {"target.ts"})
        self.assertEqual(plan.reresolve, {"importer.ts"})

    def test_changed_signature_invalidates_importers(self):
        plan = self._plan(
            {
                "target.ts": FileChange.CHANGED,
                "importer.ts": FileChange.UNCHANGED,
            },
            snapshot=_snapshot(
                ["target.ts", "importer.ts"], {"target.ts": ["helper"]}
            ),
            fresh_exports=[_export("target.ts", "helper")],
            fresh_symbols=[
                _symbol("target.ts", "helper", signature="different")
            ],
        )

        self.assertEqual(plan.reresolve, {"importer.ts"})

    def test_untouched_excludes_rebuilt_and_reresolved(self):
        plan = self._plan(
            {
                "target.ts": FileChange.NEW,
                "importer.ts": FileChange.UNCHANGED,
                "unrelated.ts": FileChange.UNCHANGED,
            },
            snapshot=_snapshot(["importer.ts", "unrelated.ts"]),
            fresh_exports=[_export("target.ts", "helper")],
            fresh_symbols=[_symbol("target.ts", "helper")],
        )

        self.assertEqual(plan.untouched, {"unrelated.ts"})


if __name__ == "__main__":
    unittest.main()
