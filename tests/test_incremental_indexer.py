import os
import tempfile
import time
import unittest
from pathlib import Path

from indexing.indexer import FileChange, reindex_index
from models.entities.resolved_reference import ResolutionStatus
from models.relationships.relationship_kind import RelationshipKind
from storage.index_store import load_index


def _write(root: Path, files: dict[str, str]) -> None:
    for relative_path, content in files.items():
        (root / relative_path).write_text(content, encoding="utf-8")


def _symbols_by_path(result, relative_path: str):
    return [
        symbol
        for symbol in result.symbols
        if symbol.relative_path == relative_path
    ]


def _symbol_by_name(result, name: str):
    matches = [symbol for symbol in result.symbols if symbol.name == name]
    return matches[0] if matches else None


def _statuses_for(result, relative_path: str) -> dict[str, ResolutionStatus]:
    document_ids = {
        document.document_id
        for document in result.documents
        if document.relative_path == relative_path
    }

    return {
        resolved.reference.name: resolved.status
        for resolved in result.resolved_references
        if resolved.reference.document_id in document_ids
    }


AUTH = {
    "a.ts": "export function createAuth() { return 1; }\n",
    "b.ts": (
        'import { createAuth } from "./a";\n'
        "export function run() { createAuth(); }\n"
    ),
}


class TestIncrementalIndexer(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db_path = str(self.root / "index.sqlite")

    def tearDown(self):
        self.tmp.cleanup()

    def test_second_run_is_noop(self):
        _write(self.root, AUTH)

        reindex_index(self.db_path, str(self.root))
        second = reindex_index(self.db_path, str(self.root))

        self.assertEqual(second.changes["a.ts"], FileChange.UNCHANGED)
        self.assertEqual(second.changes["b.ts"], FileChange.UNCHANGED)
        self.assertEqual(second.parsed_files, 0)
        self.assertEqual(second.resolved_references, 0)
        self.assertEqual(second.new_embeddings, 0)

    def test_edit_one_file_rebuilds_only_that_file(self):
        _write(self.root, AUTH)
        reindex_index(self.db_path, str(self.root))
        first = load_index(self.db_path)

        _write(self.root, {"a.ts": "export function createAuth() { return 2; }\n"})
        report = reindex_index(self.db_path, str(self.root))
        second = load_index(self.db_path)

        self.assertEqual(report.changes["a.ts"], FileChange.CHANGED)
        self.assertEqual(report.changes["b.ts"], FileChange.UNCHANGED)
        self.assertEqual(report.parsed_files, 1)

        self.assertEqual(
            {s.symbol_id for s in _symbols_by_path(second, "b.ts")},
            {s.symbol_id for s in _symbols_by_path(first, "b.ts")},
        )

    def test_body_edit_preserves_symbol_identity(self):
        _write(self.root, AUTH)
        reindex_index(self.db_path, str(self.root))
        first = load_index(self.db_path)

        _write(self.root, {"a.ts": "export function createAuth() { return 2; }\n"})
        reindex_index(self.db_path, str(self.root))
        second = load_index(self.db_path)

        self.assertEqual(
            _symbol_by_name(second, "createAuth").symbol_id,
            _symbol_by_name(first, "createAuth").symbol_id,
        )

    def test_body_edit_does_not_invalidate_importers(self):
        _write(self.root, AUTH)
        reindex_index(self.db_path, str(self.root))

        _write(self.root, {"a.ts": "export function createAuth() { return 2; }\n"})
        report = reindex_index(self.db_path, str(self.root))
        second = load_index(self.db_path)

        self.assertEqual(report.resolved_references, 0)
        self.assertEqual(
            _statuses_for(second, "b.ts")["createAuth"],
            ResolutionStatus.RESOLVED,
        )

    def test_interface_change_invalidates_importers(self):
        _write(self.root, AUTH)
        reindex_index(self.db_path, str(self.root))

        _write(self.root, {"a.ts": "export function makeAuth() { return 1; }\n"})
        report = reindex_index(self.db_path, str(self.root))
        second = load_index(self.db_path)

        self.assertGreater(report.resolved_references, 0)
        self.assertEqual(
            _statuses_for(second, "b.ts")["createAuth"],
            ResolutionStatus.UNRESOLVED,
        )

    def test_new_file_invalidates_importers_of_previously_missing_module(self):
        _write(self.root, {"b.ts": AUTH["b.ts"]})
        reindex_index(self.db_path, str(self.root))
        first = load_index(self.db_path)

        self.assertEqual(
            _statuses_for(first, "b.ts")["createAuth"],
            ResolutionStatus.UNRESOLVED,
        )

        _write(self.root, {"a.ts": AUTH["a.ts"]})
        report = reindex_index(self.db_path, str(self.root))
        second = load_index(self.db_path)

        self.assertEqual(report.changes["a.ts"], FileChange.NEW)
        self.assertEqual(report.changes["b.ts"], FileChange.UNCHANGED)
        self.assertEqual(
            _statuses_for(second, "b.ts")["createAuth"],
            ResolutionStatus.RESOLVED,
        )

    def test_deleted_file_removes_symbols_and_invalidates_importers(self):
        _write(self.root, AUTH)
        reindex_index(self.db_path, str(self.root))

        (self.root / "a.ts").unlink()
        report = reindex_index(self.db_path, str(self.root))
        second = load_index(self.db_path)

        self.assertEqual(report.changes["a.ts"], FileChange.DELETED)
        self.assertEqual(report.parsed_files, 0)
        self.assertEqual(_symbols_by_path(second, "a.ts"), [])
        self.assertEqual(
            _statuses_for(second, "b.ts")["createAuth"],
            ResolutionStatus.UNRESOLVED,
        )

    def test_second_run_keeps_identical_chunks(self):
        _write(self.root, AUTH)

        reindex_index(self.db_path, str(self.root))
        first = load_index(self.db_path)
        reindex_index(self.db_path, str(self.root))
        second = load_index(self.db_path)

        self.assertEqual(
            {c.chunk_key for c in second.chunks},
            {c.chunk_key for c in first.chunks},
        )
        self.assertEqual(
            {c.content_hash for c in second.chunks},
            {c.content_hash for c in first.chunks},
        )
        self.assertEqual(
            {c.embedding_text for c in second.chunks},
            {c.embedding_text for c in first.chunks},
        )

    def test_touch_without_content_change_does_not_reparse(self):
        _write(self.root, AUTH)
        reindex_index(self.db_path, str(self.root))

        future = time.time() + 10
        os.utime(self.root / "a.ts", (future, future))

        report = reindex_index(self.db_path, str(self.root))

        self.assertEqual(report.changes["a.ts"], FileChange.UNCHANGED)
        self.assertEqual(report.parsed_files, 0)
        self.assertEqual(report.resolved_references, 0)

    def test_extends_edge_survives_base_class_body_edit(self):
        _write(
            self.root,
            {
                "base.ts": "export class Base { method() { return 1; } }\n",
                "child.ts": 'import { Base } from "./base";\n'
                "class Child extends Base {}\n",
            },
        )
        reindex_index(self.db_path, str(self.root))
        first = load_index(self.db_path)
        first_edges = [
            r
            for r in first.relationships
            if r.kind == RelationshipKind.EXTENDS
        ]
        self.assertEqual(len(first_edges), 1)

        _write(
            self.root,
            {"base.ts": "export class Base { method() { return 2; } }\n"},
        )
        report = reindex_index(self.db_path, str(self.root))

        second = load_index(self.db_path)
        second_edges = [
            (s.name, t.name)
            for s, t in (
                (
                    next(x for x in second.symbols if x.symbol_id == r.source_symbol_id),
                    next(x for x in second.symbols if x.symbol_id == r.target_symbol_id),
                )
                for r in second.relationships
                if r.kind == RelationshipKind.EXTENDS
            )
        ]

        self.assertEqual(report.changes["child.ts"], FileChange.UNCHANGED)
        self.assertEqual(second_edges, [("Child", "Base")])


if __name__ == "__main__":
    unittest.main()