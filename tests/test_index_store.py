import sqlite3
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

import numpy as np

from analysis.build_graph import build_graph
from models.build_result import BuildResult
from storage import db
from storage.index_store import load_embedding_cache, load_index, persist_index

FILES = {
    "auth.ts": (
        "export function createAuth() { return 1; }\n"
        "export function login(name: string) { return createAuth(); }\n"
        "export function logout() { return 2; }\n"
    ),
    "api.ts": (
        'import { login } from "./auth";\n'
        'import { logout as signOut } from "./auth";\n'
        'login("admin");\n'
        "signOut();\n"
    ),
}

DATA_TABLES = [
    "documents",
    "symbols",
    "imports",
    "exports",
    "references",
    "resolved_references",
    "resolved_imports",
    "relationships",
    "chunks",
    "embeddings",
]


def _build(files: dict[str, str]) -> BuildResult:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for relative_path, content in files.items():
            path = root / relative_path
            path.write_text(content, encoding="utf-8")
        return build_graph(str(root))


def _persist_and_load(files: dict[str, str]) -> tuple[BuildResult, BuildResult]:
    with tempfile.TemporaryDirectory() as tmp:
        db_path = str(Path(tmp) / "index.sqlite")

        original = _build(files)
        persist_index(db_path, original)
        loaded = load_index(db_path)

        return original, loaded


class TestIndexStore(unittest.TestCase):
    def test_round_trip_preserves_documents_and_symbols(self):
        original, loaded = _persist_and_load(FILES)

        self.assertEqual(
            {d.relative_path for d in loaded.documents},
            {"auth.ts", "api.ts"},
        )
        self.assertEqual(
            {d.relative_path for d in loaded.documents},
            {d.relative_path for d in original.documents},
        )

        self.assertEqual(
            {s.stable_key for s in loaded.symbols},
            {s.stable_key for s in original.symbols},
        )
        self.assertEqual(
            {s.qualified_name for s in loaded.symbols},
            {s.qualified_name for s in original.symbols},
        )
        self.assertEqual(
            {s.content_hash for s in loaded.symbols},
            {s.content_hash for s in original.symbols},
        )
        self.assertEqual(
            {s.signature_hash for s in loaded.symbols},
            {s.signature_hash for s in original.symbols},
        )

    def test_round_trip_preserves_imports_exports_and_resolutions(self):
        original, loaded = _persist_and_load(FILES)

        self.assertEqual(
            {
                (i.module_path, i.imported_name, i.local_name)
                for i in loaded.import_references
            },
            {
                (i.module_path, i.imported_name, i.local_name)
                for i in original.import_references
            },
        )
        self.assertEqual(
            {(e.exported_name, e.symbol_name) for e in loaded.exports},
            {(e.exported_name, e.symbol_name) for e in original.exports},
        )
        self.assertEqual(
            {
                (
                    ri.import_reference.local_name,
                    ri.target_document.relative_path,
                    ri.target_symbol.name if ri.target_symbol else None,
                )
                for ri in loaded.resolved_import_references
            },
            {
                (
                    ri.import_reference.local_name,
                    ri.target_document.relative_path,
                    ri.target_symbol.name if ri.target_symbol else None,
                )
                for ri in original.resolved_import_references
            },
        )

    def test_round_trip_preserves_references_and_statuses(self):
        original, loaded = _persist_and_load(FILES)

        original_references = {
            r.reference_id: (r.name, r.kind, r.path) for r in original.references
        }

        self.assertEqual(
            {r.reference_id for r in loaded.references},
            set(original_references),
        )
        for reference in loaded.references:
            self.assertEqual(
                (reference.name, reference.kind, reference.path),
                original_references[reference.reference_id],
            )

        original_statuses = {
            rr.reference.reference_id: rr.status for rr in original.resolved_references
        }
        loaded_statuses = {
            rr.reference.reference_id: rr.status for rr in loaded.resolved_references
        }
        self.assertEqual(loaded_statuses, original_statuses)

        original_targets = {
            rr.reference.reference_id: rr.target_symbol.stable_key
            for rr in original.resolved_references
            if rr.target_symbol is not None
        }
        loaded_targets = {
            rr.reference.reference_id: rr.target_symbol.stable_key
            for rr in loaded.resolved_references
            if rr.target_symbol is not None
        }
        self.assertEqual(loaded_targets, original_targets)

    def test_round_trip_preserves_chunks(self):
        original, loaded = _persist_and_load(FILES)

        original_chunks = {
            (c.chunk_key, c.content_hash, c.chunk_version)
            for c in original.chunks
        }
        loaded_chunks = {
            (c.chunk_key, c.content_hash, c.chunk_version)
            for c in loaded.chunks
        }

        self.assertEqual(loaded_chunks, original_chunks)

        loaded_by_key = {c.chunk_key: c for c in loaded.chunks}

        for chunk in original.chunks:
            self.assertEqual(
                loaded_by_key[chunk.chunk_key].embedding_text,
                chunk.embedding_text,
            )
            self.assertEqual(
                loaded_by_key[chunk.chunk_key].display_text,
                chunk.display_text,
            )
            self.assertEqual(
                loaded_by_key[chunk.chunk_key].relative_path,
                chunk.relative_path,
            )

    def test_round_trip_preserves_relationships_and_graph(self):
        original, loaded = _persist_and_load(FILES)

        original_keys = {r.key for r in original.graph.relationships()}

        self.assertEqual({r.key for r in loaded.relationships}, original_keys)
        self.assertEqual({r.key for r in loaded.graph.relationships()}, original_keys)

        symbols_by_name = {s.name: s for s in loaded.symbols}

        self.assertEqual(
            {c.name for c in loaded.graph.callees_of(symbols_by_name["login"].symbol_id)},
            {"createAuth"},
        )
        self.assertEqual(
            loaded.graph.callers_of(symbols_by_name["createAuth"].symbol_id),
            [symbols_by_name["login"]],
        )

    def test_round_trip_preserves_embeddings(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "index.sqlite")

            original = _build(FILES)
            embeddings = {
                chunk.chunk_key: np.full(8, float(index), dtype=np.float32)
                for index, chunk in enumerate(original.chunks)
            }
            persist_index(
                db_path,
                original,
                embeddings=embeddings,
            )

            cache = load_embedding_cache(db_path)
            expected = {
                chunk.content_hash: embeddings[chunk.chunk_key]
                for chunk in original.chunks
            }

            self.assertEqual(set(cache), set(expected))
            for content_hash, vector in cache.items():
                np.testing.assert_array_equal(vector, expected[content_hash])

    def test_persist_without_embeddings_leaves_cache_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "index.sqlite")

            persist_index(db_path, _build(FILES))

            self.assertEqual(load_embedding_cache(db_path), {})

    def test_re_persist_does_not_duplicate(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "index.sqlite")

            original = _build(FILES)
            persist_index(db_path, original)
            persist_index(db_path, original)

            loaded = load_index(db_path)

            self.assertEqual(len(loaded.symbols), len(original.symbols))
            self.assertEqual(
                len(loaded.relationships),
                len(original.graph.relationships()),
            )
            self.assertEqual(
                len(loaded.references),
                len(original.references),
            )

    def test_persist_rolls_back_whole_index_on_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "index.sqlite")

            original = _build(FILES)
            broken = BuildResult(
                documents=original.documents,
                symbols=[
                    replace(original.symbols[0], document_id="missing-document")
                ],
            )

            with self.assertRaises(sqlite3.IntegrityError):
                persist_index(db_path, broken)

            conn = db.connect(db_path)
            try:
                for table in DATA_TABLES:
                    count = conn.execute(
                        f'SELECT COUNT(*) FROM "{table}"'
                    ).fetchone()[0]
                    self.assertEqual(count, 0, f"{table} should be empty")
            finally:
                conn.close()


if __name__ == "__main__":
    unittest.main()
