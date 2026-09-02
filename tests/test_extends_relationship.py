import tempfile
import unittest
from pathlib import Path

from analysis.build_graph import build_graph
from models.entities.reference_kind import ReferenceKind
from models.entities.resolved_reference import ResolutionStatus
from models.relationships.relationship_kind import RelationshipKind


def _build(*, files: dict[str, str]):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for name, content in files.items():
            (root / name).write_text(content, encoding="utf-8")
        return build_graph(str(root))


def _symbol_by_name(result, name: str):
    return next(s for s in result.symbols if s.name == name)


def _edges_of_kind(result, kind: RelationshipKind) -> set[tuple[str, str]]:
    names = {s.symbol_id: s.name for s in result.symbols}
    return {
        (names[r.source_symbol_id], names[r.target_symbol_id])
        for r in result.relationships
        if r.kind == kind
    }


def _heritage_references(result, owner_symbol_name: str):
    owner = _symbol_by_name(result, owner_symbol_name)
    return [
        r
        for r in result.resolved_references
        if r.reference.owner_symbol_id == owner.symbol_id
        and r.reference.kind == ReferenceKind.EXTENDS
    ]


class TestExtendsExtraction(unittest.TestCase):
    def test_heritage_identifier_is_extracted_as_extends_reference(self):
        result = _build(
            files={"a.ts": "class Base {}\nclass Child extends Base {}\n"}
        )

        refs = _heritage_references(result, "Child")

        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0].reference.path, ("Base",))

    def test_class_declaration_without_heritage_extracts_nothing(self):
        result = _build(files={"a.ts": "class Lone {}\n"})

        for symbol in result.symbols:
            self.assertEqual(_heritage_references(result, symbol.name), [])

    def test_type_identifier_outside_a_heritage_clause_is_now_has_type(self):
        result = _build(
            files={
                "a.ts": "interface Shape {}\n"
                "function area(s: Shape): Shape { return s }\n"
            }
        )

        area = _symbol_by_name(result, "area")

        shape_refs = [
            r
            for r in result.resolved_references
            if r.reference.name == "Shape"
            and r.reference.owner_symbol_id == area.symbol_id
        ]

        # Now HAS_TYPE/RETURNS are modeled with guard (max 20 per function)
        self.assertGreater(len(shape_refs), 0)
        kinds = {r.reference.kind for r in shape_refs}
        self.assertTrue(ReferenceKind.HAS_TYPE in kinds or ReferenceKind.RETURNS in kinds)
        # Should resolve to Shape interface
        self.assertTrue(any(r.target_symbol is not None and r.target_symbol.name == "Shape" for r in shape_refs))

    def test_interface_heritage_is_extracted_as_extends_reference(self):
        result = _build(
            files={"a.ts": "interface Base {}\ninterface Child extends Base {}\n"}
        )

        refs = _heritage_references(result, "Child")

        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0].reference.path, ("Base",))


class TestInterfaceExtends(unittest.TestCase):
    def test_interface_extends_emits_edge(self):
        result = _build(
            files={"a.ts": "interface Base {}\ninterface Child extends Base {}\n"}
        )

        self.assertEqual(
            _edges_of_kind(result, RelationshipKind.EXTENDS),
            {("Child", "Base")},
        )

    def test_interface_extending_two_interfaces_emits_two_edges(self):
        result = _build(
            files={
                "a.ts": "interface A {}\ninterface B {}\n"
                "interface C extends A, B {}\n"
            }
        )

        self.assertEqual(
            _edges_of_kind(result, RelationshipKind.EXTENDS),
            {("C", "A"), ("C", "B")},
        )


class TestExtendsRelationship(unittest.TestCase):
    def test_same_file_extends_emits_edge_from_subclass_to_base(self):
        result = _build(
            files={"a.ts": "class Base {}\nclass Child extends Base {}\n"}
        )

        edges = _edges_of_kind(result, RelationshipKind.EXTENDS)

        self.assertEqual(edges, {("Child", "Base")})

    def test_cross_file_imported_base_emits_edge(self):
        result = _build(
            files={
                "base.ts": "export class Base {}\n",
                "child.ts": 'import { Base } from "./base";\n'
                "class Child extends Base {}\n",
            }
        )

        base = _symbol_by_name(result, "Base")

        self.assertEqual(
            _edges_of_kind(result, RelationshipKind.EXTENDS),
            {("Child", "Base")},
        )
        edge = next(
            r
            for r in result.relationships
            if r.kind == RelationshipKind.EXTENDS
        )
        self.assertEqual(edge.target_symbol_id, base.symbol_id)

    def test_two_subclasses_produce_two_distinct_edges(self):
        result = _build(
            files={
                "a.ts": "class Base {}\n"
                "class First extends Base {}\n"
                "class Second extends Base {}\n"
                "const first = new First();\n",
            }
        )

        edges = _edges_of_kind(result, RelationshipKind.EXTENDS)

        self.assertEqual(
            edges,
            {("First", "Base"), ("Second", "Base")},
        )

    def test_call_edges_are_unchanged(self):
        result = _build(
            files={
                "a.ts": "function helper() {}\n"
                "function caller() {\n  helper();\n}\n",
            }
        )

        self.assertEqual(
            _edges_of_kind(result, RelationshipKind.CALLS),
            {("caller", "helper")},
        )


class TestExtendsNoGuessing(unittest.TestCase):
    def test_unknown_base_resolves_unresolved_without_edge(self):
        result = _build(files={"a.ts": "class Child extends Missing {}\n"})

        refs = _heritage_references(result, "Child")

        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0].status, ResolutionStatus.UNRESOLVED)
        self.assertIsNone(refs[0].target_symbol)
        self.assertEqual(_edges_of_kind(result, RelationshipKind.EXTENDS), set())

    def test_ambiguous_base_resolves_ambiguous_without_edge(self):
        result = _build(
            files={
                "a.ts": "export class Dup {}\n",
                "b.ts": "export class Dup {}\n",
                "c.ts": 'import { Dup } from "./a";\n'
                'import { Dup } from "./b";\n'
                "class Child extends Dup {}\n",
            }
        )

        refs = _heritage_references(result, "Child")

        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0].status, ResolutionStatus.AMBIGUOUS)
        self.assertIsNone(refs[0].target_symbol)
        self.assertEqual(_edges_of_kind(result, RelationshipKind.EXTENDS), set())

    def test_module_scope_symbol_shadows_imported_base(self):
        result = _build(
            files={
                "base.ts": "export class Base {}\n",
                "child.ts": 'import { Base } from "./base";\n'
                "class Base {}\n"
                "class Child extends Base {}\n",
            }
        )

        local_base = next(
            s
            for s in result.symbols
            if s.name == "Base" and s.relative_path == "child.ts"
        )
        edge = next(
            r
            for r in result.relationships
            if r.kind == RelationshipKind.EXTENDS
        )

        self.assertEqual(edge.target_symbol_id, local_base.symbol_id)


if __name__ == "__main__":
    unittest.main()
