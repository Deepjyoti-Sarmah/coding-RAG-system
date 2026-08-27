import tempfile
import unittest
from pathlib import Path

from analysis.build_graph import build_graph
from models.entities.symbols import Symbol
from retrieval.candidate import HybridCandidate
from retrieval.reranker import (
    detect_preference,
    rerank_candidates,
)

AUTH = {
    "auth.ts": (
        "export function createAuth() { return 1; }\n"
        "export function login(name: string) { return createAuth(); }\n"
        "export function logout() { return 2; }\n"
    ),
    "api.ts": (
        'import { login } from "./auth";\n'
        "export function run() { login(\"admin\"); }\n"
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
    fts_rank: int | None = None,
    vector_rank: int | None = None,
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
        fts_rank=fts_rank,
        vector_rank=vector_rank,
    )


class TestDetectPreference(unittest.TestCase):
    def test_caller_intents(self):
        for query in ("who calls login", "callers of login", "called by login"):
            self.assertEqual(detect_preference(query), "caller")

    def test_callee_intents(self):
        for query in ("what does login call", "callees of login", "what calls login"):
            self.assertEqual(detect_preference(query), "callee")

    def test_definition_intents(self):
        for query in (
            "where is createAuth defined",
            "definition of login",
            "login implementation",
            "createAuth is implemented here",
        ):
            self.assertEqual(detect_preference(query), "definition")

    def test_no_intent(self):
        self.assertIsNone(detect_preference("login"))


class TestRerankCandidates(unittest.TestCase):
    def setUp(self):
        self.result = _build()
        self.graph = self.result.graph
        self.symbols_by_key = {
            symbol.stable_key: symbol for symbol in self.result.symbols
        }

    def _rerank(self, candidates, query, seed=None, preference=None):
        return rerank_candidates(
            candidates,
            query,
            graph=self.graph,
            symbols_by_key=self.symbols_by_key,
            seed=seed,
            preference=preference,
        )

    def test_exact_symbol_boost_outranks_higher_base_score(self):
        login = _symbol(self.result, "login")
        create_auth = _symbol(self.result, "createAuth")

        ranked = self._rerank(
            [
                _candidate(create_auth, score=0.2),
                _candidate(login, score=0.1),
            ],
            "login",
        )

        self.assertEqual([c.symbol_name for c in ranked], ["login", "createAuth"])

    def test_relationship_preference_prioritizes_callers(self):
        login = _symbol(self.result, "login")
        run = _symbol(self.result, "run")
        create_auth = _symbol(self.result, "createAuth")

        ranked = self._rerank(
            [
                _candidate(create_auth, score=0.2),
                _candidate(run, score=0.1),
            ],
            "callers of login",
            seed=login,
            preference=detect_preference("callers of login"),
        )

        self.assertEqual([c.symbol_name for c in ranked], ["run", "createAuth"])

    def test_graph_distance_boost_neighbor_over_unrelated(self):
        login = _symbol(self.result, "login")
        create_auth = _symbol(self.result, "createAuth")
        logout = _symbol(self.result, "logout")

        ranked = self._rerank(
            [
                _candidate(logout, score=0.2),
                _candidate(create_auth, score=0.1),
            ],
            "login",
            seed=login,
        )

        self.assertEqual([c.symbol_name for c in ranked], ["createAuth", "logout"])

    def test_kind_match_boost(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "cls.ts").write_text(
                "export class Account { balance() { return 1; } }\n"
                "export function lookup() { return 2; }\n",
                encoding="utf-8",
            )
            result = build_graph(str(root))

        lookup = next(s for s in result.symbols if s.name == "lookup")
        account = next(s for s in result.symbols if s.name == "Account")

        ranked = rerank_candidates(
            [
                _candidate(account, score=0.2),
                _candidate(lookup, score=0.1),
            ],
            "function",
            graph=result.graph,
            symbols_by_key={s.stable_key: s for s in result.symbols},
        )

        self.assertEqual([c.symbol_name for c in ranked], ["lookup", "Account"])

    def test_path_match_boost(self):
        login = _symbol(self.result, "login")
        run = _symbol(self.result, "run")

        ranked = self._rerank(
            [
                _candidate(run, score=0.2),
                _candidate(login, score=0.1),
            ],
            "auth file",
        )

        self.assertEqual([c.symbol_name for c in ranked], ["login", "run"])

    def test_top_ranked_source_breaks_tie(self):
        login = _symbol(self.result, "login")
        create_auth = _symbol(self.result, "createAuth")

        ranked = self._rerank(
            [
                _candidate(
                    create_auth, score=0.1, sources=("vector",), vector_rank=5
                ),
                _candidate(login, score=0.1, sources=("fts",), fts_rank=0),
            ],
            "some login text",
        )

        self.assertEqual([c.symbol_name for c in ranked], ["login", "createAuth"])

    def test_lower_fts_rank_outranks_higher_rank_at_equal_score(self):
        login = _symbol(self.result, "login")
        create_auth = _symbol(self.result, "createAuth")

        ranked = self._rerank(
            [
                _candidate(create_auth, score=0.1, sources=("fts",), fts_rank=4),
                _candidate(login, score=0.1, sources=("fts",), fts_rank=0),
            ],
            "some login text",
        )

        self.assertEqual([c.symbol_name for c in ranked], ["login", "createAuth"])

    def test_deterministic_order(self):
        login = _symbol(self.result, "login")
        create_auth = _symbol(self.result, "createAuth")

        candidates = [
            _candidate(create_auth, score=0.2),
            _candidate(login, score=0.1),
        ]

        first = self._rerank(candidates, "login")
        second = self._rerank(candidates, "login")

        self.assertEqual(
            [c.symbol_name for c in first],
            [c.symbol_name for c in second],
        )

    def test_seed_not_boosted_as_definition_but_callers_are(self):
        login = _symbol(self.result, "login")
        run = _symbol(self.result, "run")
        create_auth = _symbol(self.result, "createAuth")

        ranked = self._rerank(
            [
                _candidate(create_auth, score=0.2),
                _candidate(login, score=0.1),
                _candidate(run, score=0.05),
            ],
            "who calls login",
            seed=login,
            preference=detect_preference("who calls login"),
        )

        self.assertEqual([c.symbol_name for c in ranked], ["run", "login", "createAuth"])


TOKEN = {
    "token.ts": (
        "export function validateToken(token) { return token.length > 0; }\n"
        "export function validateTokenExpiry(token) { return token.length > 0; }\n"
        "export function generateToken(userId) { return userId; }\n"
        "export function tokenExpiry(token) { return token.length; }\n"
        "export function connectDatabase() { return true; }\n"
    ),
}


class TestTokenOverlapFeature(unittest.TestCase):
    def setUp(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, content in TOKEN.items():
                (root / name).write_text(content, encoding="utf-8")
            self.result = build_graph(str(root))

        self.graph = self.result.graph
        self.symbols_by_key = {
            symbol.stable_key: symbol for symbol in self.result.symbols
        }

    def _rerank(self, candidates, query):
        return rerank_candidates(
            candidates,
            query,
            graph=self.graph,
            symbols_by_key=self.symbols_by_key,
        )

    def test_partial_overlap_ranks_above_lesser_overlap(self):
        validate_token = _symbol(self.result, "validateToken")
        validate_token_expiry = _symbol(self.result, "validateTokenExpiry")

        ranked = self._rerank(
            [
                _candidate(validate_token, score=0.1),
                _candidate(validate_token_expiry, score=0.1),
            ],
            "How is token expiry checked?",
        )

        self.assertEqual(
            [c.symbol_name for c in ranked],
            ["validateTokenExpiry", "validateToken"],
        )

    def test_full_overlap_beats_partial_overlap(self):
        token_expiry = _symbol(self.result, "tokenExpiry")
        validate_token_expiry = _symbol(self.result, "validateTokenExpiry")

        ranked = self._rerank(
            [
                _candidate(validate_token_expiry, score=0.1),
                _candidate(token_expiry, score=0.1),
            ],
            "How is token expiry checked?",
        )

        self.assertEqual(
            [c.symbol_name for c in ranked],
            ["tokenExpiry", "validateTokenExpiry"],
        )

    def test_zero_overlap_contributes_nothing(self):
        connect_database = _symbol(self.result, "connectDatabase")
        validate_token_expiry = _symbol(self.result, "validateTokenExpiry")

        ranked = self._rerank(
            [
                _candidate(connect_database, score=0.1),
                _candidate(validate_token_expiry, score=0.1),
            ],
            "How is token expiry checked?",
        )

        self.assertEqual(
            [c.symbol_name for c in ranked],
            ["validateTokenExpiry", "connectDatabase"],
        )

        # connectDatabase overlaps on nothing but the query's raw "token"
        # substring via path_match; its boost is entirely path_match, never
        # token_overlap.
        loser = next(c for c in ranked if c.symbol_name == "connectDatabase")
        self.assertAlmostEqual(loser.score, 0.1 + 0.3 * 0.5)


if __name__ == "__main__":
    unittest.main()