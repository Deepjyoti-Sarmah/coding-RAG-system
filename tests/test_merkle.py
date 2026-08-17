import tempfile
import unittest
from pathlib import Path

from analysis.fingerprints import compute_content_hash
from indexing.merkle import NodeKind, compute_merkle_tree


def _write(root: Path, files: dict[str, str]) -> None:
    for relative_path, content in files.items():
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


FIXTURE = {
    "src/auth.ts": "export function login() {}\n",
    "src/api.ts": "export const x = 1;\n",
    "lib/util.ts": "export function format() {}\n",
    "package.json": '{ "name": "fixture" }\n',
}


class TestMerkleTree(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _write(self.root, FIXTURE)

    def tearDown(self):
        self.tmp.cleanup()

    def test_file_leaf_is_content_hash(self):
        tree = compute_merkle_tree(str(self.root))

        self.assertEqual(
            tree.node_hash("src/auth.ts"),
            compute_content_hash(FIXTURE["src/auth.ts"]),
        )
        self.assertEqual(
            tree.node_hash("package.json"),
            compute_content_hash(FIXTURE["package.json"]),
        )
        self.assertEqual(
            tree.nodes["src/auth.ts"].kind,
            NodeKind.FILE,
        )

    def test_directory_nodes_are_directory_kind(self):
        tree = compute_merkle_tree(str(self.root))

        self.assertEqual(tree.nodes["src"].kind, NodeKind.DIRECTORY)
        self.assertEqual(tree.nodes["lib"].kind, NodeKind.DIRECTORY)
        self.assertEqual(tree.nodes[""].kind, NodeKind.DIRECTORY)

    def test_deterministic_across_runs(self):
        first = compute_merkle_tree(str(self.root))
        second = compute_merkle_tree(str(self.root))

        self.assertEqual(first.root_hash, second.root_hash)
        self.assertEqual(first.node_hash("src"), second.node_hash("src"))
        self.assertEqual(first.node_hash("lib"), second.node_hash("lib"))

    def test_change_one_file_changes_only_ancestors(self):
        before = compute_merkle_tree(str(self.root))

        _write(
            self.root,
            {"src/auth.ts": "export function login() { return 1; }\n"},
        )
        after = compute_merkle_tree(str(self.root))

        self.assertNotEqual(
            after.node_hash("src/auth.ts"),
            before.node_hash("src/auth.ts"),
        )
        self.assertNotEqual(after.node_hash("src"), before.node_hash("src"))
        self.assertNotEqual(after.root_hash, before.root_hash)
        self.assertEqual(after.node_hash("lib"), before.node_hash("lib"))
        self.assertEqual(
            after.node_hash("src/api.ts"),
            before.node_hash("src/api.ts"),
        )

    def test_add_file_changes_affected_subtree_only(self):
        before = compute_merkle_tree(str(self.root))

        _write(self.root, {"src/new.ts": "export const y = 2;\n"})
        after = compute_merkle_tree(str(self.root))

        self.assertNotEqual(after.node_hash("src"), before.node_hash("src"))
        self.assertNotEqual(after.root_hash, before.root_hash)
        self.assertEqual(after.node_hash("lib"), before.node_hash("lib"))

    def test_delete_file_changes_affected_subtree_only(self):
        before = compute_merkle_tree(str(self.root))

        (self.root / "src/api.ts").unlink()
        after = compute_merkle_tree(str(self.root))

        self.assertNotEqual(after.node_hash("src"), before.node_hash("src"))
        self.assertNotEqual(after.root_hash, before.root_hash)
        self.assertEqual(after.node_hash("lib"), before.node_hash("lib"))

    def test_hash_is_independent_of_creation_order(self):
        first_root = Path(self.tmp.name) / "first"
        second_root = Path(self.tmp.name) / "second"

        _write(first_root, FIXTURE)
        _write(
            second_root,
            {
                "package.json": FIXTURE["package.json"],
                "lib/util.ts": FIXTURE["lib/util.ts"],
                "src/api.ts": FIXTURE["src/api.ts"],
                "src/auth.ts": FIXTURE["src/auth.ts"],
            },
        )

        self.assertEqual(
            compute_merkle_tree(str(first_root)).root_hash,
            compute_merkle_tree(str(second_root)).root_hash,
        )

    def test_single_file_root_hashes_content(self):
        (self.root / "standalone.ts").write_text("export const z = 1;\n")

        tree = compute_merkle_tree(str(self.root / "standalone.ts"))

        self.assertEqual(
            tree.root_hash,
            compute_content_hash("export const z = 1;\n"),
        )
        self.assertEqual(tree.nodes[""].kind, NodeKind.FILE)


if __name__ == "__main__":
    unittest.main()