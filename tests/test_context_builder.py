import tempfile
import unittest
from pathlib import Path

from analysis.build_graph import build_graph
from embeddings.fake_provider import FakeEmbeddingProvider
from indexing.embedding_queue import run_embedding_worker
from indexing.indexer import reindex_index
from models.entities.symbols import Symbol
from retrieval.candidate import HybridCandidate
from retrieval.context_builder import (
    ROLE_PRIMARY,
    ROLE_SUPPORTING,
    build_context_pack,
    estimate_tokens,
)
from storage.index_store import build_context_pack_from_index

AUTH = {
    "auth.ts": (
        "export function createAuth() { return 1; }\n"
        "export function login(name: string) { return createAuth(); }\n"
        "export function logout() { return 2; }\n"
    ),
    "api.ts": (
        'import { login } from "./auth";\n'
        "export function run() { login('admin'); }\n"
    ),
}


def _build():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for name, content in AUTH.items():
            (root / name).write_text(content, encoding="utf-8")
        return build_graph(str(root))


def _symbol(result, name) -> Symbol:
    return next(symbol for symbol in result.symbols if symbol.name == name)


def _candidate(
    symbol: Symbol,
    score: float,
    sources: tuple[str, ...] = ("fts",),
) -> HybridCandidate:
    return HybridCandidate(
        chunk_key=symbol.stable_key,
        symbol_id=symbol.symbol_id,
        symbol_name=symbol.name,
        qualified_name=symbol.qualified_name,
        relative_path=symbol.relative_path,
        symbol_kind=symbol.kind.value,
        score=score,
        sources=sources,
    )


def _full_cost(symbol: Symbol) -> int:
    header = _header(symbol)
    return estimate_tokens(f"{header}\n{symbol.content}")


def _header(symbol: Symbol) -> str:
    return (
        f"{symbol.kind.value} {symbol.qualified_name} "
        f"— {symbol.relative_path}:{symbol.location.start_line}"
    )


def _symbols_by_key(result):
    return {symbol.stable_key: symbol for symbol in result.symbols}


class TestEstimateTokens(unittest.TestCase):
    def test_four_chars_is_one_token(self):
        self.assertEqual(estimate_tokens("abcd"), 1)

    def test_empty_text_is_one_token(self):
        self.assertEqual(estimate_tokens(""), 1)

    def test_deterministic(self):
        self.assertEqual(estimate_tokens("auth login function"), estimate_tokens("auth login function"))


class TestBuildContextPack(unittest.TestCase):
    def setUp(self):
        self.result = _build()
        self.graph = self.result.graph
        self.symbols_by_key = _symbols_by_key(self.result)

    def _pack(self, candidates, budget):
        return build_context_pack(
            candidates,
            query="login",
            graph=self.graph,
            symbols_by_key=self.symbols_by_key,
            token_budget=budget,
        )

    def test_single_candidate_is_primary(self):
        login = _symbol(self.result, "login")

        pack = self._pack([_candidate(login, score=0.5)], budget=200)

        self.assertEqual(len(pack.primary_definitions), 1)
        self.assertEqual(pack.primary_definitions[0].qualified_name, "login")
        self.assertEqual(pack.primary_definitions[0].role, ROLE_PRIMARY)
        self.assertEqual(pack.supporting_definitions, [])
        self.assertIn("function login", pack.primary_definitions[0].source)

    def test_graph_only_candidate_is_supporting(self):
        login = _symbol(self.result, "login")
        create_auth = _symbol(self.result, "createAuth")

        pack = self._pack(
            [
                _candidate(login, score=0.5),
                _candidate(create_auth, score=0.0, sources=("graph",)),
            ],
            budget=400,
        )

        self.assertEqual(
            [entry.qualified_name for entry in pack.primary_definitions],
            ["login"],
        )
        self.assertEqual(
            [entry.qualified_name for entry in pack.supporting_definitions],
            ["createAuth"],
        )
        self.assertEqual(pack.supporting_definitions[0].role, ROLE_SUPPORTING)

    def test_hard_budget_never_exceeded(self):
        login = _symbol(self.result, "login")

        for budget in (1, 5, 10, _full_cost(login) - 1, _full_cost(login), 200):
            pack = self._pack([_candidate(login, score=0.5)], budget=budget)

            self.assertLessEqual(pack.total_tokens, budget, f"budget={budget}")

    def test_symbol_boundaries_preserved_without_truncation(self):
        login = _symbol(self.result, "login")
        budget = _full_cost(login) - 1

        pack = self._pack([_candidate(login, score=0.5)], budget=budget)

        self.assertEqual(len(pack.primary_definitions), 1)
        self.assertEqual(pack.primary_definitions[0].source, "")
        self.assertIn("auth.ts:", pack.primary_definitions[0].location)

    def test_symbol_skipped_when_even_header_does_not_fit(self):
        login = _symbol(self.result, "login")

        pack = self._pack([_candidate(login, score=0.5)], budget=1)

        self.assertEqual(pack.primary_definitions, [])
        self.assertEqual(pack.total_tokens, 0)

    def test_primary_before_supporting_when_budget_is_tight(self):
        login = _symbol(self.result, "login")
        create_auth = _symbol(self.result, "createAuth")

        budget = _full_cost(login) + estimate_tokens(_header(create_auth)) - 1

        pack = self._pack(
            [
                _candidate(login, score=0.5),
                _candidate(create_auth, score=0.0, sources=("graph",)),
            ],
            budget=budget,
        )

        self.assertEqual(
            [entry.qualified_name for entry in pack.primary_definitions],
            ["login"],
        )
        self.assertEqual(pack.supporting_definitions, [])
        self.assertLessEqual(pack.total_tokens, budget)

    def test_duplicate_candidate_appears_once(self):
        login = _symbol(self.result, "login")

        pack = self._pack(
            [
                _candidate(login, score=0.5, sources=("fts",)),
                _candidate(login, score=0.4, sources=("vector",)),
            ],
            budget=200,
        )

        self.assertEqual(len(pack.primary_definitions), 1)

    def test_relationships_only_among_selected_symbols(self):
        login = _symbol(self.result, "login")
        run = _symbol(self.result, "run")

        pack = self._pack(
            [
                _candidate(login, score=0.5),
                _candidate(run, score=0.4),
            ],
            budget=400,
        )

        self.assertEqual(pack.relationships, ("run -> login (calls)",))

    def test_file_paths_deduplicated_and_sorted(self):
        login = _symbol(self.result, "login")
        run = _symbol(self.result, "run")

        pack = self._pack(
            [
                _candidate(login, score=0.5),
                _candidate(run, score=0.4),
            ],
            budget=400,
        )

        self.assertEqual(pack.file_paths, ("api.ts", "auth.ts"))

    def test_unknown_candidate_key_is_skipped(self):
        login = _symbol(self.result, "login")

        unknown = HybridCandidate(
            chunk_key="missing.ts|typescript|ghost|function",
            symbol_id="",
            symbol_name="ghost",
            qualified_name="ghost",
            relative_path="missing.ts",
            symbol_kind="function",
            score=0.9,
            sources=("fts",),
        )

        pack = self._pack([unknown, _candidate(login, score=0.5)], budget=200)

        self.assertEqual(
            [entry.qualified_name for entry in pack.primary_definitions],
            ["login"],
        )

    def test_deterministic_across_two_runs(self):
        login = _symbol(self.result, "login")
        run = _symbol(self.result, "run")
        create_auth = _symbol(self.result, "createAuth")

        candidates = [
            _candidate(login, score=0.5),
            _candidate(run, score=0.4),
            _candidate(create_auth, score=0.3, sources=("graph",)),
        ]

        first = self._pack(candidates, budget=300)
        second = self._pack(candidates, budget=300)

        self.assertEqual(
            [entry.qualified_name for entry in first.primary_definitions],
            [entry.qualified_name for entry in second.primary_definitions],
        )
        self.assertEqual(
            [entry.qualified_name for entry in first.supporting_definitions],
            [entry.qualified_name for entry in second.supporting_definitions],
        )
        self.assertEqual(first.relationships, second.relationships)
        self.assertEqual(first.file_paths, second.file_paths)
        self.assertEqual(first.total_tokens, second.total_tokens)

    def test_empty_candidates_produce_empty_pack(self):
        pack = self._pack([], budget=200)

        self.assertEqual(pack.primary_definitions, [])
        self.assertEqual(pack.supporting_definitions, [])
        self.assertEqual(pack.relationships, ())
        self.assertEqual(pack.file_paths, ())
        self.assertEqual(pack.total_tokens, 0)


class TestBuildContextFromIndex(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db_path = str(self.root / "index.sqlite")
        self.provider = FakeEmbeddingProvider(dimension=8)
        for name, content in AUTH.items():
            (self.root / name).write_text(content, encoding="utf-8")
        reindex_index(self.db_path, str(self.root))
        run_embedding_worker(self.db_path, self.provider)

    def tearDown(self):
        self.tmp.cleanup()

    def test_queried_symbol_is_primary_within_budget(self):
        pack = build_context_pack_from_index(
            self.db_path,
            "login",
            token_budget=400,
            provider=self.provider,
        )

        self.assertEqual(
            [entry.qualified_name for entry in pack.primary_definitions][0],
            "login",
        )
        self.assertLessEqual(pack.total_tokens, 400)
        self.assertIn("auth.ts", pack.file_paths)

    def test_context_without_provider(self):
        pack = build_context_pack_from_index(
            self.db_path,
            "createAuth",
            token_budget=400,
        )

        self.assertTrue(
            any(
                entry.qualified_name == "createAuth"
                for entry in pack.primary_definitions
            )
        )
        self.assertLessEqual(pack.total_tokens, 400)


if __name__ == "__main__":
    unittest.main()