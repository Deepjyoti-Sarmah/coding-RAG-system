import tempfile
import unittest
from pathlib import Path

from analysis.build_graph import build_graph
from models.entities.resolved_reference import ResolutionStatus
from models.entities.symbol_kind import SymbolKind


def _build(*, files: dict[str, str]):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for name, content in files.items():
            (root / name).write_text(content, encoding="utf-8")
        return build_graph(str(root))


def _symbol_by_name(result, name: str):
    return next(s for s in result.symbols if s.name == name)


def _signature_hash(source: str, name: str) -> str:
    return _symbol_by_name(_build(files={"a.ts": source}), name).signature_hash


class TestTypeLevelSymbolExtraction(unittest.TestCase):
    def test_interface_becomes_a_symbol(self):
        result = _build(files={"a.ts": "interface Shape { area(): number }\n"})

        shape = _symbol_by_name(result, "Shape")

        self.assertEqual(shape.kind, SymbolKind.INTERFACE)
        self.assertEqual(shape.qualified_name, "Shape")

    def test_type_alias_becomes_a_symbol(self):
        result = _build(files={"a.ts": "type Id = string\n"})

        alias = _symbol_by_name(result, "Id")

        self.assertEqual(alias.kind, SymbolKind.TYPE_ALIAS)
        self.assertEqual(alias.qualified_name, "Id")

    def test_generic_type_alias_becomes_a_symbol(self):
        result = _build(
            files={"a.ts": "type Callback<T> = (value: T) => void\n"}
        )

        alias = _symbol_by_name(result, "Callback")

        self.assertEqual(alias.kind, SymbolKind.TYPE_ALIAS)

    def test_interface_members_are_not_extracted_as_child_symbols(self):
        result = _build(
            files={"a.ts": "interface Shape { area(): number; name: string }\n"}
        )

        shape = _symbol_by_name(result, "Shape")

        self.assertEqual(
            [s for s in result.symbols if s.parent_symbol_id == shape.symbol_id],
            [],
        )

    def test_interface_member_names_are_not_extracted_as_references(self):
        # Regression: member names are property_identifier nodes, so they
        # were extracted as identifier references and left permanently
        # unresolved — which also invalidated importers on any edit.
        result = _build(
            files={"a.ts": "interface Shape { area(): number; name: string }\n"}
        )

        self.assertEqual(
            [
                r.reference.name
                for r in result.resolved_references
                if r.reference.name in ("area", "name")
            ],
            [],
        )

    def test_stable_key_records_the_type_level_kind(self):
        result = _build(files={"a.ts": "interface Shape {}\ntype Id = string\n"})

        self.assertTrue(
            _symbol_by_name(result, "Shape").stable_key.endswith("|interface")
        )
        self.assertTrue(
            _symbol_by_name(result, "Id").stable_key.endswith("|type_alias")
        )


class TestTypeLevelExports(unittest.TestCase):
    def test_export_interface_produces_an_export_row(self):
        result = _build(files={"a.ts": "export interface Point { x: number }\n"})

        self.assertEqual(
            [(e.exported_name, e.symbol_name) for e in result.exports],
            [("Point", "Point")],
        )

    def test_export_type_alias_produces_an_export_row(self):
        result = _build(files={"a.ts": 'export type Status = "on" | "off"\n'})

        self.assertEqual(
            [(e.exported_name, e.symbol_name) for e in result.exports],
            [("Status", "Status")],
        )


class TestTypeLevelImportResolution(unittest.TestCase):
    def test_imported_interface_resolves_to_the_interface_symbol(self):
        result = _build(
            files={
                "shapes.ts": "export interface Shape {}\n",
                "impl.ts": 'import { Shape } from "./shapes";\n'
                "class Impl implements Shape {}\n",
            }
        )

        resolved = next(
            r
            for r in result.resolved_import_references
            if r.import_reference.imported_name == "Shape"
        )

        self.assertIsNotNone(resolved.target_symbol)
        self.assertEqual(resolved.target_symbol.kind, SymbolKind.INTERFACE)

    def test_missing_type_export_stays_unresolved(self):
        result = _build(
            files={
                "shapes.ts": "interface Shape {}\n",
                "impl.ts": 'import { Shape } from "./shapes";\n'
                "class Impl implements Shape {}\n",
            }
        )

        impl = _symbol_by_name(result, "Impl")

        heritage = next(
            r
            for r in result.resolved_references
            if r.reference.owner_symbol_id == impl.symbol_id
        )

        self.assertEqual(heritage.status, ResolutionStatus.UNRESOLVED)
        self.assertEqual(result.relationships, [])


class TestTypeLevelSignatures(unittest.TestCase):
    def test_interface_signature_is_deterministic_across_builds(self):
        source = "interface Shape { area(): number; name: string }\n"

        self.assertEqual(
            _signature_hash(source, "Shape"),
            _signature_hash(source, "Shape"),
        )

    def test_member_rename_changes_the_interface_signature(self):
        self.assertNotEqual(
            _signature_hash("interface S { area(): number }\n", "S"),
            _signature_hash("interface S { size(): number }\n", "S"),
        )

    def test_member_type_change_changes_the_interface_signature(self):
        self.assertNotEqual(
            _signature_hash("interface S { name: string }\n", "S"),
            _signature_hash("interface S { name: number }\n", "S"),
        )

    def test_formatting_only_edit_keeps_the_interface_signature(self):
        self.assertEqual(
            _signature_hash("interface S { area(): number }\n", "S"),
            _signature_hash(
                "// a comment\ninterface S {\n  area(): number\n}\n", "S"
            ),
        )

    def test_member_order_does_not_change_the_interface_signature(self):
        self.assertEqual(
            _signature_hash("interface S { a: string; b: number }\n", "S"),
            _signature_hash("interface S { b: number; a: string }\n", "S"),
        )

    def test_interface_heritage_is_part_of_the_signature(self):
        self.assertNotEqual(
            _signature_hash("interface A {}\ninterface S extends A {}\n", "S"),
            _signature_hash("interface A {}\ninterface S {}\n", "S"),
        )

    def test_type_alias_signature_tracks_the_right_hand_side(self):
        self.assertNotEqual(
            _signature_hash("type Id = string\n", "Id"),
            _signature_hash("type Id = number\n", "Id"),
        )


if __name__ == "__main__":
    unittest.main()
