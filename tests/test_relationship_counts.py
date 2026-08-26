import tempfile
import unittest
from pathlib import Path

from analysis.build_graph import build_graph
from models.relationships.relationship_kind import RelationshipKind
from storage.index_store import load_index, persist_index


def _write(root: Path, files: dict[str, str]) -> None:
    for name, content in files.items():
        (root / name).write_text(content, encoding="utf-8")


CALLED_THRICE = {
    "auth.ts": (
        "export function createAuth() { return 1; }\n"
        "export function login() {\n"
        "    createAuth();\n"
        "    createAuth();\n"
        "    createAuth();\n"
        "    return 1;\n"
        "}\n"
    )
}


def _calls_edge(result, source_name: str, target_name: str):
    names = {s.symbol_id: s.name for s in result.symbols}
    return next(
        r
        for r in result.relationships
        if r.kind == RelationshipKind.CALLS
        and names[r.source_symbol_id] == source_name
        and names[r.target_symbol_id] == target_name
    )


class TestRelationshipCounts(unittest.TestCase):
    def test_repeated_calls_fold_into_one_edge_with_a_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, CALLED_THRICE)
            result = build_graph(str(root))

        edge = _calls_edge(result, "login", "createAuth")

        self.assertEqual(edge.count, 3)

        matching = [
            r
            for r in result.relationships
            if r.key == edge.key
        ]
        self.assertEqual(len(matching), 1, "duplicates must fold, not accumulate rows")

    def test_graph_holds_the_same_single_edge(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, CALLED_THRICE)
            result = build_graph(str(root))

        edges = [
            r
            for r in result.graph.relationships()
            if r.kind == RelationshipKind.CALLS
        ]

        self.assertEqual([r.count for r in edges], [3])

    def test_count_round_trips_through_sqlite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, CALLED_THRICE)
            result = build_graph(str(root))

            db_path = str(root / "index.sqlite")
            persist_index(db_path, result)
            loaded = load_index(db_path)

        self.assertEqual(_calls_edge(loaded, "login", "createAuth").count, 3)

    def test_reindexing_does_not_inflate_counts(self):
        """Counts must be replaced on re-index, not added to.

        `relationship_repository.insert_many` upserts with
        `count = count + excluded.count`, which is only correct because
        `_clear_analysis_tables` empties the table first. Neither call site
        shows the other, so pin the invariant here.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, CALLED_THRICE)
            db_path = str(root / "index.sqlite")

            persist_index(db_path, build_graph(str(root)))
            first = _calls_edge(load_index(db_path), "login", "createAuth").count

            persist_index(db_path, build_graph(str(root)))
            second = _calls_edge(load_index(db_path), "login", "createAuth").count

        self.assertEqual(first, 3)
        self.assertEqual(second, first)

    def test_graph_does_not_mutate_the_builder_counts(self):
        """Folding into the graph must not touch `BuildResult.relationships`."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, CALLED_THRICE)
            result = build_graph(str(root))

        edge = _calls_edge(result, "login", "createAuth")

        result.graph.add_relationships(result.relationships)

        self.assertEqual(edge.count, 3)


if __name__ == "__main__":
    unittest.main()
