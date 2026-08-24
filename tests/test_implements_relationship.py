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


class TestImplementsExtraction(unittest.TestCase):
    def test_implements_target_is_extracted_as_implements_reference(self):
        result = _build(
            files={
                "a.ts": "interface Shape {}\nclass Impl implements Shape {}\n"
            }
        )

        impl = _symbol_by_name(result, "Impl")

        refs = [
            r
            for r in result.resolved_references
            if r.reference.owner_symbol_id == impl.symbol_id
            and r.reference.kind == ReferenceKind.IMPLEMENTS
        ]

        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0].reference.path, ("Shape",))


class TestImplementsRelationship(unittest.TestCase):
    def test_resolved_implements_emits_edge_from_the_class(self):
        result = _build(
            files={
                "a.ts": "interface Shape {}\nclass Impl implements Shape {}\n"
            }
        )

        self.assertEqual(
            _edges_of_kind(result, RelationshipKind.IMPLEMENTS),
            {("Impl", "Shape")},
        )

    def test_two_implemented_interfaces_emit_two_edges(self):
        result = _build(
            files={
                "a.ts": "interface A {}\ninterface B {}\n"
                "class Impl implements A, B {}\n"
            }
        )

        self.assertEqual(
            _edges_of_kind(result, RelationshipKind.IMPLEMENTS),
            {("Impl", "A"), ("Impl", "B")},
        )

    def test_extends_and_implements_emit_both_edge_kinds(self):
        result = _build(
            files={
                "a.ts": "class Base {}\ninterface Shape {}\n"
                "class Impl extends Base implements Shape {}\n"
            }
        )

        self.assertEqual(
            _edges_of_kind(result, RelationshipKind.EXTENDS),
            {("Impl", "Base")},
        )
        self.assertEqual(
            _edges_of_kind(result, RelationshipKind.IMPLEMENTS),
            {("Impl", "Shape")},
        )

    def test_cross_file_imported_interface_emits_edge(self):
        result = _build(
            files={
                "shapes.ts": "export interface Shape {}\n",
                "impl.ts": 'import { Shape } from "./shapes";\n'
                "class Impl implements Shape {}\n",
            }
        )

        self.assertEqual(
            _edges_of_kind(result, RelationshipKind.IMPLEMENTS),
            {("Impl", "Shape")},
        )

    def test_unresolved_target_records_status_and_emits_no_edge(self):
        result = _build(files={"a.ts": "class Impl implements Missing {}\n"})

        impl = _symbol_by_name(result, "Impl")

        refs = [
            r
            for r in result.resolved_references
            if r.reference.owner_symbol_id == impl.symbol_id
            and r.reference.kind == ReferenceKind.IMPLEMENTS
        ]

        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0].status, ResolutionStatus.UNRESOLVED)
        self.assertEqual(_edges_of_kind(result, RelationshipKind.IMPLEMENTS), set())

    def test_implements_edge_is_not_reported_as_a_call(self):
        result = _build(
            files={
                "a.ts": "interface Shape {}\nclass Impl implements Shape {}\n"
            }
        )

        shape = _symbol_by_name(result, "Shape")
        impl = _symbol_by_name(result, "Impl")

        self.assertEqual(result.graph.callers_of(shape.symbol_id), [])
        self.assertEqual(result.graph.callees_of(impl.symbol_id), [])


if __name__ == "__main__":
    unittest.main()
