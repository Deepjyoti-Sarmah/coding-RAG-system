import tempfile
import unittest
from pathlib import Path

from analysis.build_graph import build_graph
from graph.code_graph import CodeGraph
from models.entities.symbols import Symbol
from retrieval.neighborhood import (
    DEFAULT_ONE_HOP_BUDGET,
    NeighborhoodHit,
    expand_neighborhood,
)

FIXTURE = {
    "auth.ts": (
        "export function createAuth() { return 1; }\n"
        "export function login(name: string) { return createAuth(); }\n"
        "export function logout() { return 2; }\n"
    ),
    "api.ts": (
        'import { login } from "./auth";\n'
        "export function run() { login(\"admin\"); }\n"
    ),
    "service.ts": (
        "export class AuthService {\n"
        "    validateUser(name: string) { return this.tokenize(name); }\n"
        "    tokenize(name: string) { return name; }\n"
        "}\n"
    ),
    "utils.ts": "export function helper() { return 1; }\n",
    "orchestrator.ts": (
        'import { helper } from "./utils";\n'
        "export function orchestrate() { return 2; }\n"
    ),
}


def _build():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for name, content in FIXTURE.items():
            (root / name).write_text(content, encoding="utf-8")
        return build_graph(str(root))


def _symbol(result, name) -> Symbol:
    return next(symbol for symbol in result.symbols if symbol.name == name)


class TestExpandNeighborhood(unittest.TestCase):
    def setUp(self):
        self.result = _build()

    def _expand(self, seed_name, **kwargs):
        return expand_neighborhood(
            _symbol(self.result, seed_name),
            graph=self.result.graph,
            **kwargs,
        )

    def test_one_hop_callers_callees_exports(self):
        hits = self._expand("login")

        relations = {hit.relation for hit in hits}
        self.assertEqual(relations, {"caller", "callee", "export"})

        by_name = {hit.symbol.name: hit for hit in hits}
        self.assertEqual(by_name["run"].relation, "caller")
        self.assertEqual(by_name["createAuth"].relation, "callee")
        self.assertEqual(by_name["logout"].relation, "export")
        self.assertTrue(all(hit.hop == 1 for hit in hits))

    def test_import_relation_without_call(self):
        hits = self._expand("orchestrate")

        self.assertEqual(
            [(hit.symbol.name, hit.relation, hit.hop) for hit in hits],
            [("helper", "import", 1)],
        )

    def test_parent_relation(self):
        hits = self._expand("validateUser")

        auth_service = next(
            hit.symbol for hit in hits if hit.symbol.name == "AuthService"
        )
        self.assertEqual(auth_service.qualified_name, "AuthService")
        self.assertEqual(
            next(hit.relation for hit in hits if hit.symbol.name == "AuthService"),
            "parent",
        )

    def test_dedup_same_symbol_across_relations(self):
        hits = self._expand("run")

        self.assertEqual(
            [(hit.symbol.name, hit.relation, hit.hop) for hit in hits],
            [("login", "callee", 1)],
        )

    def test_two_hop_only_when_no_direct_call_edges(self):
        hits = self._expand("AuthService")

        self.assertEqual(
            [(hit.symbol.name, hit.relation, hit.hop) for hit in hits],
            [("tokenize", "callee", 2)],
        )

    def test_no_two_hop_when_seed_has_direct_callee(self):
        hits = self._expand("login")

        self.assertTrue(all(hit.hop == 1 for hit in hits))

    def test_one_hop_budget_caps_exports(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            content = "".join(
                f"export function f{i}() {{ return {i}; }}\n" for i in range(10)
            )
            (root / "many.ts").write_text(content, encoding="utf-8")
            result = build_graph(str(root))

        hits = expand_neighborhood(
            _symbol(result, "f0"),
            graph=result.graph,
        )

        self.assertEqual(len(hits), DEFAULT_ONE_HOP_BUDGET)
        self.assertTrue(all(hit.relation == "export" for hit in hits))
        self.assertEqual(
            [hit.symbol.name for hit in hits],
            [f"f{i}" for i in range(1, DEFAULT_ONE_HOP_BUDGET + 1)],
        )

    def test_one_hop_budget_is_configurable(self):
        hits = self._expand("login", one_hop_budget=1)

        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].relation, "caller")
        self.assertEqual(hits[0].symbol.name, "run")

    def test_deterministic_order_across_runs(self):
        first = self._expand("login")
        second = self._expand("login")

        self.assertEqual(
            [(h.symbol.name, h.relation, h.hop) for h in first],
            [(h.symbol.name, h.relation, h.hop) for h in second],
        )

    def test_empty_result_when_isolated_leaf(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "leaf.ts").write_text("export function leaf() { return 1; }\n")
            result = build_graph(str(root))

        hits = expand_neighborhood(
            _symbol(result, "leaf"),
            graph=result.graph,
        )

        self.assertEqual(hits, [])

    def test_without_document_edges_skips_supporting_relations(self):
        """A graph carrying only symbols and relationships still expands.

        Import/export relations come from `add_document_edges`; without that
        call the neighborhood degrades to call/parent edges rather than
        failing.
        """
        graph = CodeGraph()
        graph.add_symbols(self.result.symbols)
        graph.add_relationships(self.result.relationships)

        hits = expand_neighborhood(_symbol(self.result, "login"), graph=graph)

        relations = {hit.relation for hit in hits}
        self.assertEqual(relations, {"caller", "callee"})

    def test_neighborhood_hit_shape(self):
        hit = NeighborhoodHit(
            symbol=_symbol(self.result, "createAuth"),
            relation="callee",
            hop=1,
        )
        self.assertEqual(hit.symbol.name, "createAuth")
        self.assertEqual(hit.relation, "callee")
        self.assertEqual(hit.hop, 1)


if __name__ == "__main__":
    unittest.main()