import tempfile
import unittest
from pathlib import Path

from analysis.build_graph import build_graph
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


class TestDeclaresRelationship(unittest.TestCase):
    def test_class_declares_its_methods(self):
        result = _build(
            files={
                "service.ts": (
                    "export class AuthService {\n"
                    "    validateUser(name: string) { return this.tokenize(name); }\n"
                    "    tokenize(name: string) { return name; }\n"
                    "}\n"
                )
            }
        )

        self.assertEqual(
            _edges_of_kind(result, RelationshipKind.DECLARES),
            {("AuthService", "validateUser"), ("AuthService", "tokenize")},
        )

    def test_top_level_function_declares_nothing(self):
        result = _build(files={"auth.ts": "export function login() { return 1; }\n"})

        self.assertEqual(_edges_of_kind(result, RelationshipKind.DECLARES), set())

    def test_declares_is_traversable_on_the_graph(self):
        result = _build(
            files={
                "service.py": (
                    "class AuthService:\n"
                    "    def validate(self):\n"
                    "        return 1\n"
                )
            }
        )

        owner = _symbol_by_name(result, "AuthService")
        declared = result.graph.declares(owner.symbol_id)

        self.assertEqual([s.name for s in declared], ["validate"])

    def test_declares_edges_have_a_count_of_one(self):
        result = _build(
            files={
                "service.ts": (
                    "export class AuthService {\n"
                    "    tokenize(name: string) { return name; }\n"
                    "}\n"
                )
            }
        )

        declares = [
            r
            for r in result.relationships
            if r.kind == RelationshipKind.DECLARES
        ]

        self.assertEqual([r.count for r in declares], [1])


if __name__ == "__main__":
    unittest.main()
