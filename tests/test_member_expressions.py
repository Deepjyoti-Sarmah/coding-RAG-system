import tempfile
import unittest
from pathlib import Path

from analysis.build_graph import build_graph
from analysis.languages import profile_for
from analysis.reference_extractor import extract_references
from analysis.symbol_extractor import extract_symbols
from models.entities.documents import Document
from models.entities.reference_kind import ReferenceKind
from models.entities.resolved_reference import ResolutionStatus
from models.entities.symbol_kind import SymbolKind
from models.relationships.relationship_kind import RelationshipKind
from parsing.registry import PARSER


def _make_document(content: str, relative_path: str = "f.ts") -> Document:
    return Document(
        document_id=f"doc-{relative_path}",
        absolute_path=f"/tmp/{relative_path}",
        relative_path=relative_path,
        file_name=relative_path,
        extension=".ts",
        language="typescript",
        size_bytes=len(content),
        line_count=len(content.splitlines()),
        content=content,
    )


def _build(*, files: dict[str, str]):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for name, content in files.items():
            (root / name).write_text(content, encoding="utf-8")
        return build_graph(str(root))


def _symbol(result, name: str, kind: SymbolKind | None = None):
    return next(
        s
        for s in result.symbols
        if s.name == name and (kind is None or s.kind == kind)
    )


def _resolved_for(result, owner_name: str, reference_name: str):
    owner = _symbol(result, owner_name)
    return [
        r
        for r in result.resolved_references
        if r.reference.owner_symbol_id == owner.symbol_id
        and r.reference.name == reference_name
    ]


def _calls_from(result, source_symbol_name: str) -> list[str]:
    source = _symbol(result, source_symbol_name)
    return [
        r.target_symbol_id
        for r in result.relationships
        if r.kind == RelationshipKind.CALLS
        and r.source_symbol_id == source.symbol_id
    ]


class TestMemberExpressionRepresentation(unittest.TestCase):
    def _extract_for_outer(self, content: str):
        doc = _make_document(content)
        tree = PARSER["typescript"].parse(doc)

        extracted = extract_symbols(tree=tree, document=doc)
        outer = next(e for e in extracted if e.symbol.name == "outer")

        return extract_references(
            owner_symbol=outer.symbol,
            owner_node=outer.node,
            profile=profile_for("typescript"),
        )

    def test_member_expression_produces_single_path_reference(self):
        refs = self._extract_for_outer(
            "function outer() {\n"
            "  auth.createAuth();\n"
            "  auth.client.createAuth();\n"
            "  this.method();\n"
            "  AuthService.staticMethod();\n"
            "  obj.a.b;\n"
            "  foo();\n"
            "}\n"
        )

        by_path = {ref.path: ref for ref in refs}

        self.assertEqual(by_path[("auth", "createAuth")].kind, ReferenceKind.CALL)
        self.assertEqual(
            by_path[("auth", "client", "createAuth")].kind,
            ReferenceKind.CALL,
        )
        self.assertEqual(by_path[("this", "method")].kind, ReferenceKind.CALL)
        self.assertEqual(
            by_path[("AuthService", "staticMethod")].kind,
            ReferenceKind.CALL,
        )
        self.assertEqual(by_path[("obj", "a", "b")].kind, ReferenceKind.MEMBER_ACCESS)
        self.assertEqual(by_path[("foo",)].kind, ReferenceKind.CALL)

        self.assertEqual(len(refs), 6)

    def test_object_and_property_parts_are_not_separate_references(self):
        refs = self._extract_for_outer(
            "function outer() {\n"
            "  auth.createAuth();\n"
            "}\n"
        )

        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0].path, ("auth", "createAuth"))
        self.assertNotIn(("auth",), [ref.path for ref in refs])
        self.assertNotIn(("createAuth",), [ref.path for ref in refs])


class TestNamespaceImportMemberCall(unittest.TestCase):
    def test_namespace_member_call_resolves_to_exported_symbol(self):
        result = _build(
            files={
                "auth.ts": "export function createAuth() {}\n",
                "api.ts": 'import * as auth from "./auth";\n'
                "function callIt() {\n"
                "  auth.createAuth();\n"
                "}\n",
            }
        )

        resolved = _resolved_for(result, "callIt", "createAuth")

        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0].status, ResolutionStatus.RESOLVED)
        self.assertEqual(resolved[0].target_symbol.name, "createAuth")
        self.assertEqual(resolved[0].target_symbol.relative_path, "auth.ts")

        calls = _calls_from(result, "callIt")

        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], resolved[0].target_symbol.symbol_id)

    def test_deep_path_is_not_guessed(self):
        result = _build(
            files={
                "auth.ts": "export function createAuth() {}\n",
                "api.ts": 'import * as auth from "./auth";\n'
                "function callIt() {\n"
                "  auth.client.createAuth();\n"
                "}\n",
            }
        )

        resolved = _resolved_for(result, "callIt", "createAuth")

        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0].status, ResolutionStatus.UNRESOLVED)
        self.assertIsNone(resolved[0].target_symbol)
        self.assertEqual(_calls_from(result, "callIt"), [])


class TestThisMemberCall(unittest.TestCase):
    def test_this_method_resolves_to_class_method(self):
        result = _build(
            files={
                "auth.ts": "class AuthService {\n"
                "  login() {\n"
                "    this.logout();\n"
                "  }\n"
                "  logout() {}\n"
                "}\n",
            }
        )

        login = _symbol(result, "login", SymbolKind.METHOD)
        logout = _symbol(result, "logout", SymbolKind.METHOD)

        resolved = _resolved_for(result, "login", "logout")

        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0].status, ResolutionStatus.RESOLVED)
        self.assertEqual(resolved[0].target_symbol.symbol_id, logout.symbol_id)

        calls = _calls_from(result, "login")

        self.assertEqual(calls, [logout.symbol_id])
        self.assertEqual(logout.parent_symbol_id, login.parent_symbol_id)

    def test_duplicate_class_methods_are_ambiguous(self):
        result = _build(
            files={
                "auth.ts": "class AuthService {\n"
                "  m() {}\n"
                "  m() {}\n"
                "  run() {\n"
                "    this.m();\n"
                "  }\n"
                "}\n",
            }
        )

        resolved = _resolved_for(result, "run", "m")

        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0].status, ResolutionStatus.AMBIGUOUS)
        self.assertIsNone(resolved[0].target_symbol)
        self.assertEqual(_calls_from(result, "run"), [])


class TestClassMemberCall(unittest.TestCase):
    def test_class_static_method_call_resolves_to_class_member(self):
        result = _build(
            files={
                "auth.ts": "class AuthService {\n"
                "  static create() {}\n"
                "}\n"
                "function outer() {\n"
                "  AuthService.create();\n"
                "}\n",
            }
        )

        create = _symbol(result, "create", SymbolKind.METHOD)

        resolved = _resolved_for(result, "outer", "create")

        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0].status, ResolutionStatus.RESOLVED)
        self.assertEqual(resolved[0].target_symbol.symbol_id, create.symbol_id)

        calls = _calls_from(result, "outer")

        self.assertEqual(calls, [create.symbol_id])


class TestUnresolvedMemberCalls(unittest.TestCase):
    def test_member_on_unknown_object_is_unresolved(self):
        result = _build(
            files={
                "api.ts": "function callIt(obj) {\n"
                "  obj.method();\n"
                "}\n",
            }
        )

        resolved = _resolved_for(result, "callIt", "method")

        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0].status, ResolutionStatus.UNRESOLVED)
        self.assertIsNone(resolved[0].target_symbol)
        self.assertEqual(_calls_from(result, "callIt"), [])

    def test_member_property_does_not_fall_back_to_module_scope(self):
        result = _build(
            files={
                "api.ts": "function createAuth() {}\n"
                "function outer() {\n"
                "  auth.createAuth();\n"
                "}\n",
            }
        )

        resolved = _resolved_for(result, "outer", "createAuth")

        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0].status, ResolutionStatus.UNRESOLVED)
        self.assertIsNone(resolved[0].target_symbol)
        self.assertEqual(_calls_from(result, "outer"), [])

    def test_member_access_is_not_a_call_relationship(self):
        result = _build(
            files={
                "api.ts": "function outer(obj) {\n"
                "  const f = obj.method;\n"
                "}\n",
            }
        )

        resolved = _resolved_for(result, "f", "method")

        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0].status, ResolutionStatus.UNRESOLVED)
        self.assertEqual(resolved[0].reference.kind, ReferenceKind.MEMBER_ACCESS)
        self.assertEqual(_calls_from(result, "f"), [])


if __name__ == "__main__":
    unittest.main()
