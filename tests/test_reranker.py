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
        # token_overlap. "token.ts"'s basename ("token") is itself a query
        # token, so it earns the full basename-match credit, not the
        # capped generic-directory-overlap credit.
        loser = next(c for c in ranked if c.symbol_name == "connectDatabase")
        self.assertAlmostEqual(loser.score, 0.1 + 0.3 * 1.0)


BASE_COMMAND = {
    "core/management/base.ts": (
        "export function execute() { return 1; }\n"
    ),
    "core/management/commands/testserver.ts": (
        "export function Command() { return 2; }\n"
    ),
}


class TestPathMatchBasenameVsDirectory(unittest.TestCase):
    def setUp(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for relative_path, content in BASE_COMMAND.items():
                path = root / relative_path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
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

    def test_basename_match_outranks_generic_directory_match(self):
        execute = _symbol(self.result, "execute")
        command = _symbol(self.result, "Command")

        # "base" is core/management/base.py's own basename - a specific
        # signal this is the named file. "management" is shared by every
        # file under core/management/, including the unrelated sibling -
        # a generic signal that must not out-rank the specific one.
        ranked = self._rerank(
            [
                _candidate(command, score=0.1),
                _candidate(execute, score=0.1),
            ],
            "management command base class parse arguments and execute",
        )

        self.assertEqual([c.symbol_name for c in ranked], ["execute", "Command"])

    def test_generic_directory_overlap_still_contributes_something(self):
        execute = _symbol(self.result, "execute")
        command = _symbol(self.result, "Command")

        ranked = self._rerank(
            [_candidate(execute, score=0.0), _candidate(command, score=0.0)],
            "management",
        )

        for candidate in ranked:
            self.assertGreater(candidate.score, 0.0)


TEST_EXAMPLE_FILES = {
    "middleware/logger/logger.ts": (
        "export function New() { return 1; }\n"
    ),
    "middleware/logger/logger_test.ts": (
        "export function TestNew() { return 2; }\n"
    ),
}


class TestTestExamplePenalty(unittest.TestCase):
    def setUp(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for relative_path, content in TEST_EXAMPLE_FILES.items():
                path = root / relative_path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            self.result = build_graph(str(root))

        self.graph = self.result.graph
        self.symbols_by_key = {
            symbol.stable_key: symbol for symbol in self.result.symbols
        }

    def test_test_file_deprioritized_at_equal_score(self):
        new = _symbol(self.result, "New")
        test_new = _symbol(self.result, "TestNew")

        ranked = rerank_candidates(
            [
                _candidate(test_new, score=0.1),
                _candidate(new, score=0.1),
            ],
            "logger",
            graph=self.graph,
            symbols_by_key=self.symbols_by_key,
        )

        self.assertEqual([c.symbol_name for c in ranked], ["New", "TestNew"])

    def test_examples_dir_is_deprioritized(self):
        from retrieval.reranker import _is_test_or_example

        self.assertTrue(_is_test_or_example("_examples/router-walk/main.go"))
        self.assertTrue(_is_test_or_example("middleware/logger/logger_test.go"))
        self.assertTrue(_is_test_or_example("tests/test_foo.py"))
        self.assertTrue(_is_test_or_example("pkg/testdata/fixture.go"))
        self.assertFalse(_is_test_or_example("middleware/logger/logger.go"))
        self.assertFalse(_is_test_or_example("core/management/base.py"))


class TestIDFWeightedPathMatch(unittest.TestCase):
    def test_rare_basename_outranks_common_basename(self):
        # Corpus: "converters" appears in 1 of 100 docs (rare), "test" in 60 of 100 (common)
        from retrieval.reranker import _idf_weight, _path_match

        # build a synthetic df where converters is rare, test is common
        df = {"converters": 1, "test": 60}
        total_docs = 100

        # rare should have high weight ~0.9, common low ~0.12
        self.assertGreater(_idf_weight(1, 100), _idf_weight(60, 100))
        self.assertGreater(_idf_weight(1, 100), 0.8)
        self.assertLess(_idf_weight(60, 100), 0.2)

        # Two candidates whose basenames differ, query contains both tokens
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "converters.ts").write_text("export function foo() { return 1; }\n", encoding="utf-8")
            (root / "test.ts").write_text("export function bar() { return 2; }\n", encoding="utf-8")
            result = build_graph(str(root))
        foo = next(s for s in result.symbols if s.name == "foo")
        bar = next(s for s in result.symbols if s.name == "bar")

        # Query contains both basenames
        query = "converters test"
        tokens = {"converters", "test"}
        pm_rare = _path_match(_candidate(foo, score=0.0), tokens, df, total_docs)
        pm_common = _path_match(_candidate(bar, score=0.0), tokens, df, total_docs)
        # converters.py's basename "converters" maps to foo only if foo's path is converters.py
        # Adjust: ensure relative_paths align - foo is converters.py, bar is test.py
        # So rare should score higher than common
        self.assertGreater(pm_rare, pm_common)

        # End-to-end: rare basename candidate outranks common at equal fused score
        ranked = rerank_candidates(
            [_candidate(bar, score=0.1), _candidate(foo, score=0.1)],
            query,
            graph=result.graph,
            symbols_by_key={s.stable_key: s for s in result.symbols},
            basename_token_df=df,
            total_docs=total_docs,
        )
        self.assertEqual(ranked[0].symbol_name, "foo")

    def test_rare_token_weight_shape(self):
        from retrieval.reranker import _idf_weight

        # 1 of 900 => strong ~0.9
        self.assertAlmostEqual(_idf_weight(1, 900), 0.898, delta=0.05)
        # 1 of 10 => weaker but not zero
        w = _idf_weight(1, 10)
        self.assertGreater(w, 0.5)
        self.assertLess(w, 0.85)


class TestIDFWeightedKindMatch(unittest.TestCase):
    def test_kind_shared_by_most_contributes_nothing(self):
        # Pool where 9 of 10 candidates are "class", 1 is "function", query says "class"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            parts = []
            for i in range(9):
                parts.append(f"export class Cls{i} {{}}\n")
            parts.append("export function myFunc() { return 1; }\n")
            (root / "lib.ts").write_text("".join(parts), encoding="utf-8")
            result = build_graph(str(root))

        symbols = {s.name: s for s in result.symbols}
        _cls0 = symbols["Cls0"]
        # Create 9 class candidates + 1 function, but we test the class boost is damped
        candidates = []
        for i in range(9):
            candidates.append(_candidate(symbols[f"Cls{i}"], score=0.1))
        candidates.append(_candidate(symbols["myFunc"], score=0.1))

        # Query contains "class": normally every class gets +0.2, but when 9/10 share it, should be damped
        ranked = rerank_candidates(
            candidates,
            "class",
            graph=result.graph,
            symbols_by_key={s.stable_key: s for s in result.symbols},
        )
        # The best-ranked candidate should NOT be decisively the first class due to kind boost alone;
        # kind boost should be near zero when most share it. We verify by checking that
        # the score increment from kind is minimal.
        # Measure: if kind were undamped, Cls0 would get +0.2=0.3 total, myFunc 0.1; huge gap.
        # Damped, gap should be small (<0.05) because weight ~0.2*0.2 ~0.04 or less
        cls_candidate = next(c for c in ranked if c.symbol_name == "Cls0")
        func_candidate = next(c for c in ranked if c.symbol_name == "myFunc")
        # Both started 0.1, class got damped kind boost, func got none. Gap should be small.
        self.assertLess(cls_candidate.score - func_candidate.score, 0.06)

    def test_kind_rare_not_damped(self):
        # 1 of 2 share kind -> not "most", should keep full boost (so lookup vs Account case still passes)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.ts").write_text("export class Account {}\nexport function lookup() { return 1; }\n", encoding="utf-8")
            result = build_graph(str(root))
        account = next(s for s in result.symbols if s.name == "Account")
        lookup = next(s for s in result.symbols if s.name == "lookup")
        ranked = rerank_candidates(
            [_candidate(account, score=0.2), _candidate(lookup, score=0.1)],
            "function",
            graph=result.graph,
            symbols_by_key={s.stable_key: s for s in result.symbols},
        )
        self.assertEqual([c.symbol_name for c in ranked], ["lookup", "Account"])


if __name__ == "__main__":
    unittest.main()