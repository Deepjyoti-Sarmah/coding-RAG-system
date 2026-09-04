"""Tests for benchmark harnesses — ensure they are not regressions-blind."""

import tempfile
import unittest
from pathlib import Path

from benchmarks.audit_coverage import audit, classify_walk


class TestAuditCoverage(unittest.TestCase):
    def test_audit_fixture_repo_is_fully_indexed(self):
        # tests/fixtures/python_repo is a small known repo — should have 0 skipped beyond expected
        root = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "python_repo"
        if not root.exists():
            self.skipTest("fixture not present")
        state = audit(root, verbose=False)
        report = state["report"]
        self.assertGreater(report["documents_created"], 0)
        self.assertGreater(report["total_symbols"], 0)
        self.assertGreater(report["total_chunks"], 0)
        # No documents with zero chunks for this fixture
        self.assertEqual(report["documents_zero_chunks"], 0)

    def test_classify_walk_respects_extensions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.py").write_text("x=1", encoding="utf-8")
            (root / "b.txt").write_text("hello", encoding="utf-8")
            result = classify_walk(root)
            # b.txt has extension .txt not in INCLUDE_EXTENSIONS -> skipped as extension
            self.assertEqual(result.skipped["extension"], 1)
            self.assertEqual(len(result.kept), 1)


class TestPruneDerived(unittest.TestCase):
    def test_prune_removes_orphaned_chunks_vectors_and_jobs(self):
        import tempfile
        from pathlib import Path

        from chunking.symbol_chunker import SemanticChunk
        from storage import db, schema
        from storage.index_store import _prune_derived

        with tempfile.TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "index.sqlite")
            conn = db.connect(db_path)
            try:
                schema.create_schema(conn)
                # Insert 2 chunks, embeddings, vec, jobs
                c1 = SemanticChunk(chunk_key="k1", symbol_id="s1", relative_path="a.py", embedding_text="t1", display_text="d1", content_hash="h1", chunk_version="v1")
                _c2 = SemanticChunk(chunk_key="k2", symbol_id="s1", relative_path="b.py", embedding_text="t2", display_text="d2", content_hash="h2", chunk_version="v1")
                # Minimal seed: need symbols/documents for FK — skip FK check and test prune logic directly
                # So test the core: _prune_derived with current_keys={k1} should leave only k1
                # Instead test via count after manual insert of embeddings vec
                # Create embeddings and jobs manually
                conn.execute("INSERT OR REPLACE INTO embeddings(chunk_id, embedding) VALUES (?, ?)", ("k1", b"\x00"))
                conn.execute("INSERT OR REPLACE INTO embeddings(chunk_id, embedding) VALUES (?, ?)", ("k2", b"\x00"))
                conn.execute("INSERT OR REPLACE INTO embedding_jobs(chunk_key, content_hash, status, attempts) VALUES (?, ?, ?, ?)", ("k1", "h1", "PENDING", 0))
                conn.execute("INSERT OR REPLACE INTO embedding_jobs(chunk_key, content_hash, status, attempts) VALUES (?, ?, ?, ?)", ("k2", "h2", "PENDING", 0))
                conn.commit()
                # Prune with only k1 remaining
                _prune_derived(conn, [c1])
                remain_emb = conn.execute("SELECT count(*) FROM embeddings").fetchone()[0]
                remain_jobs = conn.execute("SELECT count(*) FROM embedding_jobs").fetchone()[0]
                self.assertEqual(remain_emb, 1)
                self.assertEqual(remain_jobs, 1)
                # Empty -> clears all
                _prune_derived(conn, [])
                self.assertEqual(conn.execute("SELECT count(*) FROM embeddings").fetchone()[0], 0)
                conn.rollback()
            finally:
                conn.close()

    def test_prune_empty_current_clears_all(self):
        import tempfile
        from pathlib import Path

        from storage import db, schema
        from storage.index_store import _prune_derived

        with tempfile.TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "index.sqlite")
            conn = db.connect(db_path)
            try:
                schema.create_schema(conn)
                conn.execute("INSERT INTO embeddings(chunk_id, embedding) VALUES (?, ?)", ("orphan", b"\x00"))
                conn.commit()
                _prune_derived(conn, [])
                self.assertEqual(conn.execute("SELECT count(*) FROM embeddings").fetchone()[0], 0)
            finally:
                conn.close()


class TestExternalBenchmarkMetrics(unittest.TestCase):
    def test_run_external_produces_ceiling_and_over_returned(self):
        import tempfile
        from pathlib import Path

        from evaluation.external import ExternalQuestion, run_external_evaluation

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            (repo / "a.py").write_text("def foo(): pass\n", encoding="utf-8")
            (repo / "b.py").write_text("def bar(): pass\n", encoding="utf-8")
            q = ExternalQuestion(query="foo", expected_files=frozenset({"a.py"}))
            report = run_external_evaluation(repo, [q], provider=None, top_k=5, file_k=10)
            self.assertEqual(report.total_questions, 1)
            self.assertIsNotNone(report.mean_precision_ceiling_at_10)
            self.assertIsNotNone(report.mean_precision_over_returned)


if __name__ == "__main__":
    unittest.main()
