import os
import tempfile
import time
import unittest
from pathlib import Path

from analysis.fingerprints import compute_content_hash
from indexing.diff import FileChange, scan_files
from models.file_state import FileState


def _state_from_scan(path: str, scanned) -> FileState:
    return FileState(
        relative_path=path,
        file_hash=compute_content_hash(scanned.content),
        size_bytes=scanned.size_bytes,
        mtime_ns=scanned.mtime_ns,
        last_indexed_at="now",
    )


class TestChangeDetection(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "a.ts").write_text(
            "export function login() {}\n", encoding="utf-8"
        )
        (self.root / "b.ts").write_text(
            "export const x = 1;\n", encoding="utf-8"
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_first_scan_is_all_new(self):
        scan = scan_files(str(self.root), {})

        self.assertEqual(scan.changes["a.ts"], FileChange.NEW)
        self.assertEqual(scan.changes["b.ts"], FileChange.NEW)
        self.assertIsNotNone(scan.current["a.ts"].content)

    def test_unchanged_scan_skips_content_reads(self):
        first = scan_files(str(self.root), {})
        states = {
            path: _state_from_scan(path, scanned)
            for path, scanned in first.current.items()
        }

        second = scan_files(str(self.root), states)

        self.assertEqual(second.changes["a.ts"], FileChange.UNCHANGED)
        self.assertEqual(second.changes["b.ts"], FileChange.UNCHANGED)
        self.assertIsNone(second.current["a.ts"].content)

    def test_touch_without_content_change_is_unchanged(self):
        first = scan_files(str(self.root), {})
        states = {
            path: _state_from_scan(path, scanned)
            for path, scanned in first.current.items()
        }

        future = time.time() + 10
        os.utime(self.root / "a.ts", (future, future))

        second = scan_files(str(self.root), states)

        self.assertEqual(second.changes["a.ts"], FileChange.UNCHANGED)
        self.assertIsNotNone(second.current["a.ts"].content)

    def test_edit_is_changed(self):
        first = scan_files(str(self.root), {})
        states = {
            path: _state_from_scan(path, scanned)
            for path, scanned in first.current.items()
        }

        (self.root / "a.ts").write_text(
            "export function login() { return 1; }\n", encoding="utf-8"
        )

        second = scan_files(str(self.root), states)

        self.assertEqual(second.changes["a.ts"], FileChange.CHANGED)
        self.assertEqual(second.changes["b.ts"], FileChange.UNCHANGED)

    def test_add_and_delete(self):
        first = scan_files(str(self.root), {})
        states = {
            path: _state_from_scan(path, scanned)
            for path, scanned in first.current.items()
        }

        (self.root / "c.ts").write_text(
            "export const y = 2;\n", encoding="utf-8"
        )
        (self.root / "a.ts").unlink()

        second = scan_files(str(self.root), states)

        self.assertEqual(second.changes["c.ts"], FileChange.NEW)
        self.assertEqual(second.changes["a.ts"], FileChange.DELETED)
        self.assertEqual(second.changes["b.ts"], FileChange.UNCHANGED)


if __name__ == "__main__":
    unittest.main()