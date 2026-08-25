import tempfile
import time
import unittest
from pathlib import Path

from indexing.watcher import _DebouncedReindexer


class TestDebouncedReindexer(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "a.ts").write_text(
            "export function createAuth() { return 1; }\n",
            encoding="utf-8",
        )
        self.db_path = str(self.root / ".ckg" / "index.sqlite")
        self.reports: list = []
        self.handler = _DebouncedReindexer(
            str(self.root),
            self.db_path,
            debounce_seconds=0.05,
            provider=None,
            on_report=self.reports.append,
        )

    def tearDown(self):
        if self.handler._timer is not None:
            self.handler._timer.cancel()
        self.tmp.cleanup()

    def _settle(self):
        timer = self.handler._timer
        if timer is not None:
            timer.join(timeout=5)

    def test_file_change_triggers_reindex(self):
        (self.root / "a.ts").write_text(
            "export function createAuth() { return 2; }\n",
            encoding="utf-8",
        )
        self.handler.on_any_event(_event(f"{self.root}/a.ts", is_directory=False))
        self._settle()

        self.assertEqual(len(self.reports), 1)
        self.assertEqual(self.reports[0].parsed_files, 1)

    def test_rapid_events_collapse_into_one_reindex(self):
        for i in range(5):
            (self.root / "a.ts").write_text(
                f"export function createAuth() {{ return {i}; }}\n",
                encoding="utf-8",
            )
            self.handler.on_any_event(_event(f"{self.root}/a.ts", is_directory=False))
            time.sleep(0.01)

        self._settle()

        self.assertEqual(len(self.reports), 1)

    def test_index_directory_events_are_ignored(self):
        self.handler.on_any_event(_event(f"{self.db_path}", is_directory=False))
        self.handler._timer.join(timeout=0) if self.handler._timer else None

        self.assertIsNone(self.handler._timer)

    def test_noop_change_reports_only_once(self):
        # First event: file is NEW, gets indexed, report fires.
        self.handler.on_any_event(_event(f"{self.root}/a.ts", is_directory=False))
        self._settle()
        self.assertEqual(len(self.reports), 1)

        # Second event with unchanged content: reindex parses nothing,
        # so no second report.
        self.handler.on_any_event(_event(f"{self.root}/a.ts", is_directory=False))
        self._settle()

        self.assertEqual(len(self.reports), 1)


def _event(src_path: str, *, is_directory: bool):
    from watchdog.events import FileModifiedEvent

    event = FileModifiedEvent(src_path)
    event.is_directory = is_directory
    return event


if __name__ == "__main__":
    unittest.main()
