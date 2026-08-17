import tempfile
import unittest
from pathlib import Path

from analysis.build_graph import build_graph
from chunking.symbol_chunker import CHUNK_VERSION, build_semantic_chunks
from models.build_result import BuildResult

FILES = {
    "auth.ts": (
        "export function createAuth() { return 1; }\n"
        "export function login(name: string) { return createAuth(); }\n"
        "export function logout() { return 2; }\n"
    ),
    "api.ts": (
        'import { login } from "./auth";\n'
        "export function run() { login('admin'); }\n"
    ),
    "util.ts": (
        "export function format(value: string) { return value.trim(); }\n"
    ),
}


def _build(files: dict[str, str]) -> BuildResult:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for relative_path, content in files.items():
            path = root / relative_path
            path.write_text(content, encoding="utf-8")
        return build_graph(str(root))


def _chunk_for(result: BuildResult, name: str):
    matches = [c for c in result.chunks if name in c.chunk_key]
    return matches[0] if matches else None


class TestSemanticChunkContent(unittest.TestCase):
    def test_login_chunk_contains_expected_graph_facts(self):
        result = _build(FILES)
        chunk = _chunk_for(result, "login")

        self.assertIsNotNone(chunk)
        self.assertIn("function login", chunk.embedding_text)
        self.assertIn("qualified name: login", chunk.embedding_text)
        self.assertIn("file: auth.ts", chunk.embedding_text)
        self.assertIn("calls: createAuth", chunk.embedding_text)
        self.assertIn("called by: run", chunk.embedding_text)
        self.assertIn("exports: login", chunk.embedding_text)

    def test_login_chunk_excludes_unrelated_symbol(self):
        result = _build(FILES)
        chunk = _chunk_for(result, "login")

        self.assertNotIn("format", chunk.embedding_text)
        self.assertNotIn("util.ts", chunk.embedding_text)
        self.assertNotIn("logout", chunk.embedding_text)

    def test_run_chunk_includes_its_import(self):
        result = _build(FILES)
        chunk = _chunk_for(result, "run")

        self.assertIn(
            'imports: import { login } from "./auth"',
            chunk.embedding_text,
        )
        self.assertIn("calls: login", chunk.embedding_text)


class TestStableChunkIdentity(unittest.TestCase):
    def test_chunk_uses_stable_key_not_uuid(self):
        result = _build(FILES)
        chunk = _chunk_for(result, "login")

        self.assertEqual(chunk.chunk_key, "auth.ts|typescript|login|function")
        self.assertEqual(chunk.chunk_version, CHUNK_VERSION)

    def test_deterministic_across_two_builds(self):
        first = _build(FILES)
        second = _build(FILES)

        self.assertEqual(
            {c.chunk_key for c in first.chunks},
            {c.chunk_key for c in second.chunks},
        )
        self.assertEqual(
            {c.content_hash for c in first.chunks},
            {c.content_hash for c in second.chunks},
        )
        self.assertEqual(
            {c.embedding_text for c in first.chunks},
            {c.embedding_text for c in second.chunks},
        )

    def test_body_edit_changes_hash_keeps_key(self):
        before = _build(FILES)

        edited = dict(FILES)
        edited["auth.ts"] = (
            "export function createAuth() { return 1; }\n"
            "export function login(name: string) { return createAuth() + 1; }\n"
            "export function logout() { return 2; }\n"
        )
        after = _build(edited)

        before_login = _chunk_for(before, "login")
        after_login = _chunk_for(after, "login")

        self.assertEqual(before_login.chunk_key, after_login.chunk_key)
        self.assertNotEqual(before_login.content_hash, after_login.content_hash)
        self.assertNotEqual(before_login.embedding_text, after_login.embedding_text)

    def test_distinct_symbols_have_distinct_keys(self):
        result = _build(FILES)

        keys = {c.chunk_key for c in result.chunks}

        self.assertEqual(len(keys), len(result.chunks))
        self.assertIn("auth.ts|typescript|createAuth|function", keys)
        self.assertIn("auth.ts|typescript|login|function", keys)
        self.assertIn("util.ts|typescript|format|function", keys)


class TestBuildSemanticChunks(unittest.TestCase):
    def test_one_chunk_per_symbol(self):
        result = _build(FILES)

        self.assertEqual(len(result.chunks), len(result.symbols))

    def test_chunks_group_imports_by_document(self):
        result = _build(FILES)

        self.assertEqual(len(build_semantic_chunks(result)), len(result.symbols))


if __name__ == "__main__":
    unittest.main()