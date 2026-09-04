import os
import re
import tempfile
import time
import unittest
from pathlib import Path

from indexing.indexer import FileChange, reindex_index
from models.entities.resolved_reference import ResolutionStatus
from models.relationships.relationship_kind import RelationshipKind
from storage import db
from storage.index_store import load_index

_UUID_PATTERN = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
)
_TIMESTAMP_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?\+00:00")
_TMPDIR_PATTERN = re.compile(r"/tmp/tmp[A-Za-z0-9_]+")
_MTIME_PATTERN = re.compile(r"\b1[0-9]{18}\b")
_GENERATION_PATTERN = re.compile(r"\('generation', '[0-9]+'\)")


def _write(root: Path, files: dict[str, str]) -> None:
    for relative_path, content in files.items():
        (root / relative_path).write_text(content, encoding="utf-8")


def _symbols_by_path(result, relative_path: str):
    return [
        symbol for symbol in result.symbols if symbol.relative_path == relative_path
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
        'import { createAuth } from "./a";\nexport function run() { createAuth(); }\n'
    ),
}


def _scalar(db_path: str, sql: str, parameters=()) -> int:
    conn = db.connect(db_path)
    try:
        return conn.execute(sql, parameters).fetchone()[0]
    finally:
        conn.close()


class TestDeltaPersistence(unittest.TestCase):
    """Incremental runs must leave the store identical to a full rebuild,
    while preserving the embedding cache for untouched chunks."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db_path = str(self.root / "index.sqlite")
        _write(self.root, AUTH)

    def tearDown(self):
        self.tmp.cleanup()

    def test_incremental_matches_full_rebuild(self):
        edited = "export function createAuth() { return 2; }\n"
        reindex_index(self.db_path, str(self.root))
        _write(self.root, {"a.ts": edited})
        reindex_index(self.db_path, str(self.root))

        full_tmp = tempfile.TemporaryDirectory()
        try:
            full_root = Path(full_tmp.name)
            _write(full_root, {"a.ts": edited, "b.ts": AUTH["b.ts"]})
            full_db = str(full_root / "index.sqlite")
            reindex_index(full_db, str(full_root))

            incremental_tables = self._snapshot(self.db_path)
            full_tables = self._snapshot(full_db)

            self.assertEqual(incremental_tables.keys(), full_tables.keys())
            for table, rows in incremental_tables.items():
                self.assertEqual(rows, full_tables[table], table)
        finally:
            full_tmp.cleanup()

    def test_editing_one_file_preserves_other_embeddings(self):
        from embeddings.fake_provider import FakeEmbeddingProvider

        provider = FakeEmbeddingProvider(dimension=8)
        reindex_index(self.db_path, str(self.root))

        import indexing.embedding_queue as queue

        queue.run_embedding_worker(self.db_path, provider)
        embeddings_before = _scalar(self.db_path, "SELECT COUNT(*) FROM embeddings")
        self.assertGreater(embeddings_before, 0)

        _write(self.root, {"a.ts": "export function createAuth() { return 3; }\n"})
        reindex_index(self.db_path, str(self.root))
        queue.run_embedding_worker(self.db_path, provider)

        # b.ts chunks kept their vectors without re-embedding.
        untouched_vectors = _scalar(
            self.db_path,
            """
            SELECT COUNT(DISTINCT e.chunk_id) FROM embeddings e
            JOIN chunks c ON c.chunk_id = e.chunk_id
            WHERE c.relative_path = 'b.ts'
            """,
        )
        self.assertGreater(untouched_vectors, 0)
        self.assertEqual(
            _scalar(self.db_path, "SELECT COUNT(*) FROM embeddings"),
            _scalar(self.db_path, "SELECT COUNT(*) FROM chunks"),
        )

    def test_deleted_file_leaves_no_rows_behind(self):
        gone = "gone.ts"
        _write(self.root, {gone: "export function vanish() { return 1; }\n"})
        reindex_index(self.db_path, str(self.root))
        (self.root / gone).unlink()

        report = reindex_index(self.db_path, str(self.root))

        self.assertEqual(report.changes[gone], FileChange.DELETED)
        for sql in (
            "SELECT COUNT(*) FROM documents WHERE relative_path = ?",
            "SELECT COUNT(*) FROM symbols WHERE relative_path = ?",
            "SELECT COUNT(*) FROM chunks WHERE relative_path = ?",
            "SELECT COUNT(*) FROM file_state WHERE relative_path = ?",
        ):
            self.assertEqual(_scalar(self.db_path, sql, (gone,)), 0, sql)

    def _snapshot(self, db_path: str) -> dict[str, list]:
        """Comparable per-table state.

        Random UUIDs (document/symbol/import ids) and wall-clock
        timestamps differ between any two indexing runs, so they are
        masked before comparison. Autoincrement-id tables are skipped.
        """
        conn = db.connect(db_path)
        root_path = str(Path(db_path).parent.resolve())
        try:
            tables = [
                row["name"]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                    " AND name NOT LIKE 'sqlite_%'"
                    " ORDER BY name"
                )
            ]

            def normalized(row) -> str:
                text = repr(tuple(row))
                text = _UUID_PATTERN.sub("<uuid>", text)
                text = _TIMESTAMP_PATTERN.sub("<ts>", text)
                text = text.replace(root_path, "<root>")
                text = _TMPDIR_PATTERN.sub("<root>", text)
                text = _MTIME_PATTERN.sub("<mtime>", text)
                return _GENERATION_PATTERN.sub("('generation', <gen>)", text)

            return {
                name: sorted(
                    normalized(row) for row in conn.execute(f'SELECT * FROM "{name}"')
                )
                for name in tables
                if name
                not in (
                    "imports",
                    "exports",
                    "relationships",
                    "resolved_imports",
                )
                and not name.startswith("chunks_fts")
            }
        finally:
            conn.close()


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
            r for r in first.relationships if r.kind == RelationshipKind.EXTENDS
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
                    next(
                        x for x in second.symbols if x.symbol_id == r.source_symbol_id
                    ),
                    next(
                        x for x in second.symbols if x.symbol_id == r.target_symbol_id
                    ),
                )
                for r in second.relationships
                if r.kind == RelationshipKind.EXTENDS
            )
        ]

        self.assertEqual(report.changes["child.ts"], FileChange.UNCHANGED)
        self.assertEqual(second_edges, [("Child", "Base")])


IMPLEMENTS = {
    "shapes.ts": "export interface Shape { area(): number }\n",
    "impl.ts": 'import { Shape } from "./shapes";\nclass Impl implements Shape {}\n',
}


class TestImplementsIncrementalInvalidation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db_path = str(self.root / "index.sqlite")

    def tearDown(self):
        self.tmp.cleanup()

    def _implements_edges(self) -> list[tuple[str, str]]:
        result = load_index(self.db_path)
        names = {s.symbol_id: s.name for s in result.symbols}

        return sorted(
            (names[r.source_symbol_id], names[r.target_symbol_id])
            for r in result.relationships
            if r.kind == RelationshipKind.IMPLEMENTS
        )

    def test_member_set_edit_invalidates_implementers(self):
        _write(self.root, IMPLEMENTS)
        reindex_index(self.db_path, str(self.root))

        self.assertEqual(self._implements_edges(), [("Impl", "Shape")])

        # Renaming a member moves the interface's signature_hash, so the
        # interface fingerprint changes and implementers must re-resolve.
        _write(
            self.root,
            {"shapes.ts": "export interface Shape { size(): number }\n"},
        )
        report = reindex_index(self.db_path, str(self.root))

        self.assertGreater(report.resolved_references, 0)
        self.assertEqual(self._implements_edges(), [("Impl", "Shape")])

    def test_formatting_only_edit_does_not_invalidate_implementers(self):
        _write(self.root, IMPLEMENTS)
        reindex_index(self.db_path, str(self.root))

        _write(
            self.root,
            {
                "shapes.ts": "// the shape contract\n"
                "export interface Shape {\n  area(): number\n}\n"
            },
        )
        report = reindex_index(self.db_path, str(self.root))

        self.assertEqual(report.resolved_references, 0)
        self.assertEqual(report.changes["impl.ts"], FileChange.UNCHANGED)
        self.assertEqual(self._implements_edges(), [("Impl", "Shape")])

    def test_removing_the_interface_export_drops_the_edge(self):
        _write(self.root, IMPLEMENTS)
        reindex_index(self.db_path, str(self.root))

        _write(self.root, {"shapes.ts": "interface Shape { area(): number }\n"})
        reindex_index(self.db_path, str(self.root))

        self.assertEqual(self._implements_edges(), [])


class TestMerkleReuseAndGuardrails(unittest.TestCase):
    def test_reused_chunks_100_percent_after_one_edit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db = str(root / "index.sqlite")
            _write(root, AUTH)
            import indexing.embedding_queue as q
            from embeddings.fake_provider import FakeEmbeddingProvider
            prov = FakeEmbeddingProvider(dimension=8)
            reindex_index(db, str(root))
            q.run_embedding_worker(db, prov)
            before = _scalar(db, "SELECT COUNT(*) FROM chunks")
            _write(root, {"a.ts": "export function createAuth() { return 99; }\n"})
            reindex_index(db, str(root))
            q.run_embedding_worker(db, prov)
            after = _scalar(db, "SELECT COUNT(*) FROM chunks")
            self.assertEqual(before, after)
            # untouched b.ts chunks still there
            self.assertGreater(_scalar(db, "SELECT COUNT(*) FROM chunks WHERE relative_path='b.ts'"), 0)

    def test_merkle_root_persisted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db_path = str(root / "index.sqlite")
            _write(root, AUTH)
            reindex_index(db_path, str(root))
            conn = db.connect(db_path)
            try:
                row = conn.execute("SELECT value FROM index_metadata WHERE key='merkle_root'").fetchone()
                self.assertIsNotNone(row)
                self.assertEqual(len(row[0]), 64)
            finally:
                conn.close()

    def test_parse_once_per_file(self):
        # guardrail: build_graph parses once per document (not per pass)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, AUTH)
            from unittest.mock import patch

            from parsing.tree_sitter_parser import TreeSitterParser
            orig = TreeSitterParser.parse
            calls: list[str] = []
            def counted(self, document):
                calls.append(document.relative_path)
                return orig(self, document)
            with patch.object(TreeSitterParser, "parse", counted):
                reindex_index(str(root / "index.sqlite"), str(root))
            self.assertEqual(len(calls), 2)


if __name__ == "__main__":
    unittest.main()
