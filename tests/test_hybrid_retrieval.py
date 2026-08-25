import tempfile
import unittest
from pathlib import Path

import numpy as np

from embeddings.fake_provider import FakeEmbeddingProvider
from indexing.embedding_queue import run_embedding_worker
from indexing.indexer import reindex_index
from models.entities.fts_hit import FtsHit
from retrieval.hybrid_retriever import HybridRetriever, detect_intent
from retrieval.index_queries import build_hybrid_retriever
from retrieval.ranking import reciprocal_rank_fusion
from retrieval.vector_store import VectorSearchHit, VectorStore

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

IMPORTERS = {
    "auth.ts": (
        "export function login(name: string) { return 1; }\n"
        "function internalDetail() { return 2; }\n"
    ),
    "api.ts": (
        'import { login } from "./auth";\n'
        "export function run() { login(\"admin\"); }\n"
        "function apiPrivate() { return 3; }\n"
    ),
    "cli.ts": (
        'import { login as signIn } from "./auth";\n'
        "export function prompt() { signIn(\"x\"); }\n"
    ),
}


class _StubVectorStore(VectorStore):
    def __init__(self, hits: list[VectorSearchHit]) -> None:
        self.hits = hits

    def search(
        self,
        query_vector,
        *,
        top_k: int = 5,
        relative_path: str | None = None,
    ) -> list[VectorSearchHit]:
        return self.hits[:top_k]


def _fts_hit(chunk_key: str) -> FtsHit:
    return FtsHit(
        chunk_key=chunk_key,
        symbol_name="",
        qualified_name="",
        relative_path="",
        score=-1.0,
    )


def _vector_hit(chunk_key: str) -> VectorSearchHit:
    return VectorSearchHit(
        chunk_key=chunk_key,
        relative_path="",
        score=0.9,
    )


class TestReciprocalRankFusion(unittest.TestCase):
    def test_key_in_multiple_sources_outranks_single_source(self):
        fused = reciprocal_rank_fusion(
            [["a", "b", "c"], ["b", "c", "d"]]
        )

        self.assertGreater(fused["b"], fused["a"])
        self.assertGreater(fused["b"], fused["d"])
        self.assertGreater(fused["c"], fused["d"])

    def test_empty_lists_produce_empty_fusion(self):
        self.assertEqual(reciprocal_rank_fusion([]), {})


class TestHybridRetrieverStubs(unittest.TestCase):
    def _graph_and_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, content in AUTH.items():
                (root / name).write_text(content, encoding="utf-8")
            from analysis.build_graph import build_graph
            return build_graph(str(root))

    def _retriever(self, *, fts_keys=None, vector_hits=None):
        result = self._graph_and_index()
        fts_keys = fts_keys or []
        vector_hits = vector_hits or []

        return HybridRetriever(
            symbol_index=result.symbol_index,
            graph=result.graph,
            fts_search=lambda query, limit: [_fts_hit(key) for key in fts_keys],
            vector_store=_StubVectorStore(vector_hits),
            embed=lambda query: np.zeros(8, dtype=np.float32),
        )

    def test_hybrid_merges_and_ranks_candidates(self):
        self._graph_and_index()
        login_key = "auth.ts|typescript|login|function"
        create_auth_key = "auth.ts|typescript|createAuth|function"

        retriever = self._retriever(
            fts_keys=[login_key, create_auth_key],
            vector_hits=[_vector_hit(create_auth_key), _vector_hit(login_key)],
        )

        retrieval = retriever.retrieve("login")

        self.assertEqual(retrieval.strategy, "hybrid")
        self.assertEqual(retrieval.candidates[0].symbol_name, "login")
        self.assertIn("fts", retrieval.candidates[0].sources)
        self.assertIn("vector", retrieval.candidates[0].sources)

    def test_graph_expansion_adds_one_hop_neighbor(self):
        result = self._graph_and_index()
        create_auth_key = "auth.ts|typescript|createAuth|function"

        retriever = HybridRetriever(
            symbol_index=result.symbol_index,
            graph=result.graph,
            fts_search=lambda query, limit: [_fts_hit(create_auth_key)],
            vector_store=None,
            embed=None,
        )

        retrieval = retriever.retrieve("createAuth implementation")

        login = next(
            candidate
            for candidate in retrieval.candidates
            if candidate.symbol_name == "login"
        )
        self.assertIn("graph", login.sources)

    def test_no_vector_source_still_returns_fts_results(self):
        result = self._graph_and_index()
        login_key = "auth.ts|typescript|login|function"

        retriever = HybridRetriever(
            symbol_index=result.symbol_index,
            graph=result.graph,
            fts_search=lambda query, limit: [_fts_hit(login_key)],
            vector_store=None,
            embed=None,
        )

        retrieval = retriever.retrieve("some login text")

        self.assertGreater(len(retrieval.candidates), 0)
        self.assertEqual(retrieval.candidates[0].symbol_name, "login")

    def test_expansion_includes_callers_callees_and_exports(self):
        result = self._graph_and_index()
        login_key = "auth.ts|typescript|login|function"

        retriever = HybridRetriever(
            symbol_index=result.symbol_index,
            graph=result.graph,
            fts_search=lambda query, limit: [_fts_hit(login_key)],
            vector_store=None,
            embed=None,
            resolved_imports=result.resolved_import_references,
            exports=result.exports,
        )

        retrieval = retriever.retrieve("login")

        expanded = {
            candidate.symbol_name
            for candidate in retrieval.candidates
            if "graph" in candidate.sources
        }
        self.assertIn("run", expanded)
        self.assertIn("createAuth", expanded)
        self.assertIn("logout", expanded)

    def test_expansion_includes_import_neighbor(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "utils.ts").write_text(
                "export function helper() { return 1; }\n",
                encoding="utf-8",
            )
            (root / "orchestrator.ts").write_text(
                'import { helper } from "./utils";\n'
                "export function orchestrate() { return 2; }\n",
                encoding="utf-8",
            )
            from analysis.build_graph import build_graph
            result = build_graph(str(root))

        orchestrate_key = "orchestrator.ts|typescript|orchestrate|function"

        retriever = HybridRetriever(
            symbol_index=result.symbol_index,
            graph=result.graph,
            fts_search=lambda query, limit: [_fts_hit(orchestrate_key)],
            vector_store=None,
            embed=None,
            resolved_imports=result.resolved_import_references,
            exports=result.exports,
        )

        retrieval = retriever.retrieve("orchestrate")

        expanded = {
            candidate.symbol_name
            for candidate in retrieval.candidates
            if "graph" in candidate.sources
        }
        self.assertIn("helper", expanded)


class TestImportersStrategyStubs(unittest.TestCase):
    def _build(self, files):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, content in files.items():
                (root / name).write_text(content, encoding="utf-8")
            from analysis.build_graph import build_graph
            return build_graph(str(root))

    def _retriever(self, files):
        result = self._build(files)

        return HybridRetriever(
            symbol_index=result.symbol_index,
            graph=result.graph,
            fts_search=lambda query, limit: [],
            vector_store=None,
            embed=None,
            resolved_imports=result.resolved_import_references,
            exports=result.exports,
        )

    def test_module_mode_returns_exported_surface_of_each_importer(self):
        retriever = self._retriever(IMPORTERS)

        retrieval = retriever.retrieve("What imports auth.ts?")

        self.assertEqual(retrieval.strategy, "graph_importers")
        self.assertEqual(retrieval.query, "auth.ts")
        names = [c.symbol_name for c in retrieval.candidates]
        self.assertIn("run", names)
        self.assertIn("prompt", names)
        self.assertNotIn("internalDetail", names)
        for candidate in retrieval.candidates:
            self.assertEqual(candidate.sources, ("graph",))
            self.assertNotEqual(candidate.relative_path, "auth.ts")

    def test_non_exported_module_symbols_rank_after_exported(self):
        retriever = self._retriever(IMPORTERS)

        retrieval = retriever.retrieve("importers of auth.ts")

        api_names = [
            c.symbol_name
            for c in retrieval.candidates
            if c.relative_path == "api.ts"
        ]
        self.assertEqual(api_names.index("run"), 0)
        self.assertLess(api_names.index("run"), api_names.index("apiPrivate"))

    def test_importer_documents_are_ordered_by_path(self):
        retriever = self._retriever(IMPORTERS)

        first = retriever.retrieve("What imports auth.ts?")
        second = retriever.retrieve("what imports auth.ts")

        first_paths = [c.relative_path for c in first.candidates]
        second_paths = [c.relative_path for c in second.candidates]
        self.assertEqual(sorted(set(first_paths)), ["api.ts", "cli.ts"])
        self.assertEqual(first_paths, second_paths)

    def test_unknown_module_falls_back_to_hybrid(self):
        retriever = self._retriever(IMPORTERS)

        retrieval = retriever.retrieve("What imports missing.ts?")

        # No importer data for the unknown module: rather than an empty
        # structural answer, the query degrades to hybrid search.
        self.assertNotEqual(retrieval.strategy, "graph_importers")

    def test_symbol_mode_resolves_importers_by_symbol_name(self):
        retriever = self._retriever(IMPORTERS)

        retrieval = retriever.retrieve("who imports login")

        self.assertEqual(retrieval.strategy, "graph_importers")
        paths = {c.relative_path for c in retrieval.candidates}
        self.assertEqual(paths, {"api.ts", "cli.ts"})

    def test_unknown_symbol_name_returns_no_candidates(self):
        retriever = self._retriever(IMPORTERS)

        retrieval = retriever.retrieve("who imports nonexistent")

        self.assertEqual(retrieval.candidates, [])

    def test_callee_direction_is_not_routed_to_importers(self):
        result = self._build(AUTH)
        login_key = "auth.ts|typescript|login|function"

        retriever = HybridRetriever(
            symbol_index=result.symbol_index,
            graph=result.graph,
            fts_search=lambda query, limit: [_fts_hit(login_key)],
            vector_store=None,
            embed=None,
        )

        retrieval = retriever.retrieve("what does auth import")

        self.assertNotEqual(retrieval.strategy, "graph_importers")


class TestHybridRetrieverIntegration(unittest.TestCase):
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

    def test_who_calls_returns_graph_callers(self):
        retriever = build_hybrid_retriever(self.db_path, provider=self.provider)

        retrieval = retriever.retrieve("who calls login")

        self.assertEqual(retrieval.strategy, "graph_callers")
        self.assertEqual({c.symbol_name for c in retrieval.candidates}, {"run"})

    def test_what_does_call_returns_graph_callees(self):
        retriever = build_hybrid_retriever(self.db_path, provider=self.provider)

        retrieval = retriever.retrieve("what does login call")

        self.assertEqual(retrieval.strategy, "graph_callees")
        self.assertEqual({c.symbol_name for c in retrieval.candidates}, {"createAuth"})

    def test_where_is_returns_exact_symbol(self):
        retriever = build_hybrid_retriever(self.db_path, provider=self.provider)

        retrieval = retriever.retrieve("where is createAuth defined")

        self.assertEqual(retrieval.strategy, "exact_symbol")
        self.assertEqual([c.symbol_name for c in retrieval.candidates], ["createAuth"])

    def test_hybrid_query_puts_exact_name_first(self):
        retriever = build_hybrid_retriever(self.db_path, provider=self.provider)

        retrieval = retriever.retrieve("login")

        self.assertEqual(retrieval.strategy, "hybrid")
        self.assertEqual(retrieval.candidates[0].symbol_name, "login")

    def test_hybrid_without_provider_skips_vector(self):
        retriever = build_hybrid_retriever(self.db_path)

        retrieval = retriever.retrieve("createAuth")

        self.assertEqual(retrieval.strategy, "hybrid")
        self.assertTrue(
            any(c.symbol_name == "createAuth" for c in retrieval.candidates)
        )

    def test_hybrid_expansion_includes_import_neighbor(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db_path = str(root / "index.sqlite")
            (root / "utils.ts").write_text(
                "export function helper() { return 1; }\n",
                encoding="utf-8",
            )
            (root / "orchestrator.ts").write_text(
                'import { helper } from "./utils";\n'
                "export function orchestrate() { return 2; }\n",
                encoding="utf-8",
            )
            reindex_index(db_path, str(root))

            retriever = build_hybrid_retriever(db_path)

            retrieval = retriever.retrieve("orchestrate")

            helper = next(
                candidate
                for candidate in retrieval.candidates
                if candidate.symbol_name == "helper"
            )
            self.assertIn("graph", helper.sources)

    def test_what_imports_returns_importing_modules(self):
        retriever = build_hybrid_retriever(self.db_path)

        retrieval = retriever.retrieve("What imports auth.ts?")

        self.assertEqual(retrieval.strategy, "graph_importers")
        self.assertNotEqual(retrieval.candidates, [])
        self.assertEqual(
            {c.relative_path for c in retrieval.candidates}, {"api.ts"}
        )
        self.assertEqual(retrieval.candidates[0].symbol_name, "run")

    def test_caller_intent_routes_to_graph(self):
        retriever = build_hybrid_retriever(self.db_path, provider=self.provider)

        retrieval = retriever.retrieve("callers of login")

        self.assertEqual(retrieval.strategy, "graph_callers")
        self.assertEqual(retrieval.candidates[0].symbol_name, "run")

    def test_empty_index_returns_no_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            empty_root = Path(tmp)
            empty_db = str(empty_root / "empty.sqlite")
            reindex_index(empty_db, str(empty_root))

            retriever = build_hybrid_retriever(empty_db)

            retrieval = retriever.retrieve("nothing matches this")

            self.assertEqual(retrieval.candidates, [])


class TestIntentDetection(unittest.TestCase):
    def test_caller_phrasings(self):
        for query in (
            "who calls login",
            "callers of login",
            "find callers of parseQuery",
            "who invokes submitForm",
        ):
            self.assertEqual(detect_intent(query), ("callers", query.split()[-1].rstrip("?")), query)

    def test_callee_phrasings(self):
        self.assertEqual(detect_intent("what does run call"), ("callees", "run"))
        self.assertEqual(detect_intent("callees of handleAuth"), ("callees", "handleAuth"))

    def test_definition_phrasings(self):
        self.assertEqual(
            detect_intent("where is login defined"), ("definition", "login")
        )
        self.assertEqual(
            detect_intent("definition of createAuth"), ("definition", "createAuth")
        )

    def test_importer_phrasings(self):
        self.assertEqual(detect_intent("what imports auth.ts"), ("importers", "auth.ts"))
        self.assertEqual(detect_intent("which files use login"), ("importers", "login"))
        self.assertEqual(detect_intent("importers of auth.ts"), ("importers", "auth.ts"))

    def test_plain_query_has_no_intent(self):
        self.assertIsNone(detect_intent("how does authentication flow work"))
        self.assertIsNone(detect_intent("orchestrate"))


class TestEmptyIntentFallsBackToHybrid(unittest.TestCase):
    def test_unknown_symbol_falls_through_to_hybrid(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, content in AUTH.items():
                (root / name).write_text(content, encoding="utf-8")
            from analysis.build_graph import build_graph
            result = build_graph(str(root))

            retriever = HybridRetriever(
                symbol_index=result.symbol_index,
                graph=result.graph,
                fts_search=lambda query, limit: [
                    _fts_hit("auth.ts|typescript|login|function")
                ],
                vector_store=None,
                embed=None,
            )

            retrieval = retriever.retrieve("who calls totallyUnknownThing")

            self.assertEqual(retrieval.strategy, "hybrid")
            self.assertNotEqual(retrieval.candidates, [])


if __name__ == "__main__":
    unittest.main()