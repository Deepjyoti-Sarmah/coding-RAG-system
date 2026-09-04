"""Tests for P5-4d dollar conversion — dated table, aggregate-based math."""

import json
import tempfile
import unittest
from pathlib import Path

from retrieval.pricing import (
    DEFAULT_MODEL,
    PRICE_DATE,
    PRICING,
    dollars_saved,
    resolve_pricing,
)


class TestPricing(unittest.TestCase):
    def test_table_is_dated_and_default_sonnet(self):
        self.assertEqual(DEFAULT_MODEL, "sonnet")
        self.assertRegex(PRICE_DATE, r"^\d{4}-\d{2}-\d{2}$")
        # As-of rates; if these change, update PRICE_DATE in the same commit.
        self.assertEqual(resolve_pricing("sonnet"), (2.00, 10.00))
        self.assertEqual(resolve_pricing("opus"), (5.00, 25.00))
        self.assertEqual(resolve_pricing("haiku"), (1.00, 5.00))
        self.assertIn("sonnet", PRICING)

    def test_resolve_is_case_insensitive_and_rejects_unknown(self):
        self.assertEqual(resolve_pricing("Sonnet"), resolve_pricing("sonnet"))
        with self.assertRaises(ValueError):
            resolve_pricing("gpt-4o")

    def test_dollars_from_aggregate_tokens_input_only(self):
        # 10k tokens saved at sonnet $2/1M input => $0.02, regardless of output price.
        self.assertAlmostEqual(dollars_saved(10_000, "sonnet"), 0.02, delta=1e-9)
        self.assertAlmostEqual(dollars_saved(0, "sonnet"), 0.0, delta=1e-12)


class TestSavingsSummary(unittest.TestCase):
    def _write_results(self, tmp: Path) -> None:
        tmp.joinpath("demo.json").write_text(
            json.dumps(
                {
                    "repo": "https://example.com/repo",
                    "token_budget": 800,
                    "total_questions": 2,
                    "mean_baseline_tokens": 2000,
                    "mean_context_tokens": 800,
                    "mean_savings_pct": 0.5,
                    "aggregate_savings_pct": 0.6,
                    "mean_recall_at_10": 1.0,
                    "questions": [],
                    "buckets": {
                        "<1k": {
                            "count": 0,
                            "mean_baseline_tokens": None,
                            "mean_context_tokens": None,
                            "aggregate_savings_pct": None,
                            "mean_recall_at_10": None,
                        },
                        ">4k": {
                            "count": 1,
                            "mean_baseline_tokens": 3500,
                            "mean_context_tokens": 800,
                            "aggregate_savings_pct": 1.0 - 800 / 3500,
                            "mean_recall_at_10": 1.0,
                        },
                    },
                }
            ),
            encoding="utf-8",
        )

    def test_rows_carry_model_price_date_and_null_buckets(self):
        from symbolgraph.cli import cmd_savings

        with tempfile.TemporaryDirectory() as tmp:
            self._write_results(Path(tmp))
            rows = cmd_savings(tmp, model="sonnet")
            overall = [r for r in rows if r["bucket"] is None]
            self.assertEqual(len(overall), 1)
            row = overall[0]
            self.assertEqual(row["budget"], 800)
            self.assertAlmostEqual(row["aggregate_pct"], 0.6, delta=1e-9)
            self.assertAlmostEqual(row["tokens_saved"], 1200, delta=1e-9)
            self.assertAlmostEqual(row["dollars_saved"], 1200 * 2.0 / 1e6, delta=1e-12)
            self.assertEqual(row["model"], "sonnet")
            self.assertEqual(row["price_date"], PRICE_DATE)
            self.assertEqual(row["price_in_per_1m"], 2.0)
            # Empty bucket reports null, not 0.0.
            empty = next(r for r in rows if r["bucket"] == "<1k")
            self.assertIsNone(empty["aggregate_pct"])
            self.assertIsNone(empty["tokens_saved"])
            self.assertIsNone(empty["dollars_saved"])
            # Populated bucket is aggregate-weighted.
            big = next(r for r in rows if r["bucket"] == ">4k")
            self.assertAlmostEqual(big["aggregate_pct"], 1.0 - 800 / 3500, delta=1e-9)

    def test_missing_dir_returns_no_rows(self):
        from symbolgraph.cli import cmd_savings

        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(cmd_savings(str(Path(tmp) / "absent"), model="sonnet"), [])


class TestSavingsCommand(unittest.TestCase):
    def test_savings_command_human_and_json(self):
        import contextlib
        import io

        from symbolgraph.cli import main

        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "demo.json").write_text(
                json.dumps(
                    {
                        "repo": "https://example.com/repo",
                        "token_budget": 800,
                        "total_questions": 1,
                        "mean_baseline_tokens": 2000,
                        "mean_context_tokens": 800,
                        "mean_savings_pct": 0.6,
                        "aggregate_savings_pct": 0.6,
                        "mean_recall_at_10": 1.0,
                        "questions": [],
                    }
                ),
                encoding="utf-8",
            )
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = main(["savings", "--results-dir", tmp])
            self.assertEqual(rc, 0)
            self.assertIn("60.0% aggregate", buf.getvalue())

            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = main(["savings", "--results-dir", tmp, "--json"])
            self.assertEqual(rc, 0)
            rows = json.loads(buf.getvalue())
            self.assertEqual(rows[0]["budget"], 800)

    def test_savings_command_no_results_is_exit_1(self):
        import contextlib
        import io

        from symbolgraph.cli import main

        with tempfile.TemporaryDirectory() as tmp:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = main(["savings", "--results-dir", str(Path(tmp) / "absent")])
            self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
