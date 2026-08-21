"""Full build and incremental rebuild must produce the same semantics.

Both paths run the pass sequence defined in `analysis.pipeline`. These
tests pin that equivalence: reaching a repository state in one shot and
reaching it through a series of incremental edits must yield the same
symbols, relationships and resolutions.

Comparisons go through `stable_key` rather than `symbol_id`, because
entity ids are UUIDs and are only stable within a single index lineage.
"""

import tempfile
import unittest
from pathlib import Path

from indexing.indexer import reindex_index
from storage.index_store import load_index

AUTH = "export function createAuth() { return 1; }\n"
API = (
    'import { createAuth } from "./auth";\n'
    "export function run() { return createAuth(); }\n"
)
UTIL = (
    'import { run } from "./api";\n'
    "export function boot() { return run(); }\n"
)


def _symbol_keys(result) -> set[str]:
    return {symbol.stable_key for symbol in result.symbols}


def _relationship_keys(result) -> set[tuple[str, str, str]]:
    keys_by_id = {s.symbol_id: s.stable_key for s in result.symbols}

    return {
        (
            keys_by_id.get(r.source_symbol_id, r.source_symbol_id),
            keys_by_id.get(r.target_symbol_id, r.target_symbol_id),
            r.kind.value,
        )
        for r in result.relationships
    }


def _resolution_statuses(result) -> set[tuple[str, str]]:
    return {
        (resolved.reference.name, resolved.status.value)
        for resolved in result.resolved_references
    }


def _import_targets(result) -> set[tuple[str, str]]:
    return {
        (
            resolved.import_reference.local_name,
            resolved.target_document.relative_path,
        )
        for resolved in result.resolved_import_references
    }


class TestFullAndIncrementalParity(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _index_in_one_shot(self, files: dict[str, str]):
        repo = self.root / "full"
        repo.mkdir()

        for name, content in files.items():
            (repo / name).write_text(content, encoding="utf-8")

        db_path = str(self.root / "full.sqlite")
        reindex_index(db_path, str(repo))

        return load_index(db_path)

    def _index_incrementally(self, steps: list[dict[str, str]]):
        repo = self.root / "incremental"
        repo.mkdir()
        db_path = str(self.root / "incremental.sqlite")

        for step in steps:
            for name, content in step.items():
                (repo / name).write_text(content, encoding="utf-8")

            reindex_index(db_path, str(repo))

        return load_index(db_path)

    def _assert_equivalent(self, full, incremental):
        self.assertEqual(_symbol_keys(incremental), _symbol_keys(full))
        self.assertEqual(
            _relationship_keys(incremental), _relationship_keys(full)
        )
        self.assertEqual(
            _resolution_statuses(incremental), _resolution_statuses(full)
        )
        self.assertEqual(_import_targets(incremental), _import_targets(full))

    def test_files_added_one_at_a_time_match_a_single_full_build(self):
        files = {"auth.ts": AUTH, "api.ts": API, "util.ts": UTIL}

        full = self._index_in_one_shot(files)
        incremental = self._index_incrementally(
            [{"auth.ts": AUTH}, {"api.ts": API}, {"util.ts": UTIL}]
        )

        self._assert_equivalent(full, incremental)

    def test_importer_added_before_its_dependency_matches_full_build(self):
        files = {"auth.ts": AUTH, "api.ts": API}

        full = self._index_in_one_shot(files)
        # The importer is indexed while its target is still missing, so
        # its import starts unresolved and must be repaired when the
        # dependency arrives.
        incremental = self._index_incrementally(
            [{"api.ts": API}, {"auth.ts": AUTH}]
        )

        self._assert_equivalent(full, incremental)

    def test_edited_file_converges_on_the_full_build(self):
        final_auth = "export function createAuth() { return 99; }\n"
        files = {"auth.ts": final_auth, "api.ts": API}

        full = self._index_in_one_shot(files)
        incremental = self._index_incrementally(
            [{"auth.ts": AUTH, "api.ts": API}, {"auth.ts": final_auth}]
        )

        self._assert_equivalent(full, incremental)


if __name__ == "__main__":
    unittest.main()
