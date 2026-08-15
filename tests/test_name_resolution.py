import tempfile
import unittest
from pathlib import Path

from analysis.build_graph import build_graph
from models.entities.resolved_reference import ResolutionStatus


def _build(root: Path):
    return build_graph(str(root))


def _symbol_by_name(result, name: str):
    return next(s for s in result.symbols if s.name == name)


def _resolved_for(result, symbol_name: str, reference_name: str):
    owner = _symbol_by_name(result, symbol_name)
    return [
        r
        for r in result.resolved_references
        if r.reference.owner_symbol_id == owner.symbol_id
        and r.reference.name == reference_name
    ]


class TestScopeResolution(unittest.TestCase):
    def test_reference_climbs_inner_to_module(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.ts").write_text(
                "function login() {}\n"
                "function outer() {\n"
                "  function inner() {\n"
                "    login();\n"
                "  }\n"
                "}\n",
                encoding="utf-8",
            )

            result = _build(root)
            resolved = _resolved_for(result, "inner", "login")

            self.assertEqual(len(resolved), 1)
            self.assertEqual(resolved[0].status, ResolutionStatus.RESOLVED)
            self.assertEqual(
                resolved[0].target_symbol.name,
                "login",
            )

    def test_local_variable_shadows_module_variable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.ts").write_text(
                "const login = globalLogin;\n"
                "function outer() {\n"
                "  const login = localLogin;\n"
                "  login();\n"
                "}\n",
                encoding="utf-8",
            )

            result = _build(root)
            outer = _symbol_by_name(result, "outer")
            local_login = next(
                s
                for s in result.symbols
                if s.name == "login" and s.parent_symbol_id == outer.symbol_id
            )

            resolved = _resolved_for(result, "outer", "login")

            self.assertEqual(len(resolved), 1)
            self.assertEqual(resolved[0].status, ResolutionStatus.RESOLVED)
            self.assertEqual(resolved[0].target_symbol.symbol_id, local_login.symbol_id)

    def test_module_scope_is_restricted_to_document(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.ts").write_text(
                "export function login() {}\n"
                "function outer() {\n"
                "  login();\n"
                "}\n",
                encoding="utf-8",
            )
            (root / "b.ts").write_text(
                "export function login() {}\n",
                encoding="utf-8",
            )

            result = _build(root)
            a_login = next(
                s
                for s in result.symbols
                if s.name == "login" and s.relative_path == "a.ts"
            )
            outer = _symbol_by_name(result, "outer")

            resolved = _resolved_for(result, "outer", "login")

            self.assertEqual(len(resolved), 1)
            self.assertEqual(resolved[0].status, ResolutionStatus.RESOLVED)
            self.assertEqual(resolved[0].target_symbol.symbol_id, a_login.symbol_id)

    def test_ambiguous_module_scope_is_not_guessed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.ts").write_text(
                "const login = 1;\n"
                "const login = 2;\n"
                "function outer() {\n"
                "  login();\n"
                "}\n",
                encoding="utf-8",
            )

            result = _build(root)
            resolved = _resolved_for(result, "outer", "login")

            self.assertEqual(len(resolved), 1)
            self.assertEqual(resolved[0].status, ResolutionStatus.AMBIGUOUS)
            self.assertIsNone(resolved[0].target_symbol)


class TestUnresolvedReferences(unittest.TestCase):
    def test_unknown_name_is_unresolved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.ts").write_text(
                "function outer() {\n"
                "  unknownName();\n"
                "}\n",
                encoding="utf-8",
            )

            result = _build(root)
            resolved = _resolved_for(result, "outer", "unknownName")

            self.assertEqual(len(resolved), 1)
            self.assertEqual(resolved[0].status, ResolutionStatus.UNRESOLVED)
            self.assertIsNone(resolved[0].target_symbol)

    def test_unresolved_call_has_no_relationship(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.ts").write_text(
                "function outer() {\n"
                "  unknownName();\n"
                "}\n",
                encoding="utf-8",
            )

            result = _build(root)
            outer = _symbol_by_name(result, "outer")

            calls = [
                r
                for r in result.relationships
                if r.source_symbol_id == outer.symbol_id
            ]

            self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()