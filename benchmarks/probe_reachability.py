"""Probe whether hard-task fixture files are reachable via prompt-only search.

For each task in a manifest, this script:
  1. Indexes the task's fixture repo into a fresh temp CKG index.
  2. Runs `ckg search` with the query set to EXACTLY task["prompt"] at top-k 10.
  3. Reports whether each of the task's expected_files shows up in the top-10
     results, and at what rank.

This exists to catch a specific class of bad "hard" task: one where a human
validated reachability by searching for the *answer* (the expected symbol or
file name) rather than the actual task prompt. That's circular — it proves
the index can find a file named X when you search for X, not that an agent
working only from the task prompt could ever get there. To make that mistake
structurally impossible, the query passed to search is asserted to be
identical to task["prompt"]; there is no alternate/fallback query path.

Usage:
    uv run python benchmarks/probe_reachability.py \
        [--manifest evaluation/tasks_hard.json] [--top-k 10] [--out report.json]
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


def _embeddings_active() -> bool:
    """Best-effort check for whether the vector/embedding path is available.

    Mirrors ckg.cli._detect_provider's own checks (Ollama reachable, or the
    'local' extra's sentence-transformers importable) without importing the
    heavier ckg.cli module just for this.
    """
    if importlib.util.find_spec("sentence_transformers") is not None:
        return True
    try:
        from embeddings.ollama_provider import ollama_available

        return bool(ollama_available())
    except Exception:  # noqa: BLE001 -- best-effort probe, never fatal
        return False


def _index_fixture(fixture_root: Path, db_path: Path) -> None:
    """Index fixture_root into db_path using the CLI's --db override."""
    proc = subprocess.run(
        [sys.executable, "-m", "ckg.cli", "--db", str(db_path), "index", str(fixture_root)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=420,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"indexing {fixture_root} failed (exit {proc.returncode}): {proc.stderr[-2000:]}"
        )


def _search_top_k(db_path: Path, query: str, task_prompt: str, top_k: int) -> list[str]:
    """Run ckg search with query, returning the relative_path of each hit in rank order.

    Hard constraint: query MUST be exactly the task's prompt. This assertion
    is the whole point of this script — do not remove it, and do not add any
    code path that could route a different string here.
    """
    assert query == task_prompt, (
        "probe_reachability must search using the task prompt verbatim; "
        "using an expected file/symbol name as the query would make "
        "reachability results circular and meaningless."
    )

    from ckg.cli import cmd_search, resolve_provider

    provider = None
    try:
        provider = resolve_provider(str(db_path), use_vector=True)
    except Exception:  # noqa: BLE001 -- fall back to FTS+graph-only search
        provider = None

    retrieval = cmd_search(str(db_path), query, provider=provider, top_k=top_k)
    paths: list[str] = []
    for candidate in retrieval.candidates:
        p = candidate.relative_path
        if p not in paths:
            paths.append(p)
    return paths


def _resolve_fixture_path(fixture: str) -> Path:
    """Resolve a task's `fixture` field to an absolute repo path on disk."""
    candidate = REPO_ROOT / fixture
    if candidate.exists():
        return candidate
    # Some manifests store fixture as "local_x/x"; try repo-root-relative as-is.
    raise FileNotFoundError(f"fixture path not found on disk: {candidate}")


def _file_hit(expected: str, found_paths: list[str]) -> tuple[bool, int | None]:
    """Return (hit, 1-based rank) using the same matching semantics as ab_metrics._file_matches."""

    def norm(p: str) -> str:
        return p.removeprefix("fastapi/")

    expected_n = norm(expected)
    for idx, f in enumerate(found_paths, start=1):
        f_n = norm(f)
        if f_n == expected_n:
            return True, idx
        if "/" not in expected_n:
            if "/" not in f_n and f_n == expected_n:
                return True, idx
        else:
            if f_n.endswith("/" + expected_n):
                return True, idx
    return False, None


def probe_task(task: dict, top_k: int, db_cache: dict[str, Path], tmp_root: Path) -> dict:
    fixture = task["fixture"]
    if fixture not in db_cache:
        fixture_path = _resolve_fixture_path(fixture)
        db_path = tmp_root / (fixture.replace("/", "_")) / "index.sqlite"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        _index_fixture(fixture_path, db_path)
        db_cache[fixture] = db_path
    db_path = db_cache[fixture]

    prompt = task["prompt"]
    found_paths = _search_top_k(db_path, prompt, prompt, top_k)

    file_results = []
    for expected in task["expected_files"]:
        hit, rank = _file_hit(expected, found_paths)
        file_results.append({"expected_file": expected, "hit": hit, "rank": rank})

    return {
        "task_id": task["id"],
        "fixture": fixture,
        "top_k": top_k,
        "search_results": found_paths,
        "expected_files": file_results,
        "all_reachable": all(r["hit"] for r in file_results),
    }


def _print_report(reports: list[dict], embeddings_active: bool) -> None:
    print(f"embeddings_active: {embeddings_active}")
    print()
    by_fixture: dict[str, list[dict]] = {}
    for r in reports:
        by_fixture.setdefault(r["fixture"], []).append(r)

    for fixture, rows in by_fixture.items():
        print(f"=== {fixture} ===")
        for r in rows:
            status = "REACHABLE" if r["all_reachable"] else "NOT REACHABLE"
            print(f"  {r['task_id']}: {status}")
            for fr in r["expected_files"]:
                mark = f"HIT (rank {fr['rank']})" if fr["hit"] else "MISS"
                print(f"    {fr['expected_file']}: {mark}")
        print()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default="evaluation/tasks_hard.json")
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)

    manifest_path = Path(args.manifest)
    if not manifest_path.is_absolute():
        manifest_path = REPO_ROOT / manifest_path
    tasks = json.loads(manifest_path.read_text())

    embeddings_active = _embeddings_active()

    reports = []
    db_cache: dict[str, Path] = {}
    with tempfile.TemporaryDirectory(prefix="ckg-probe-") as tmp:
        tmp_root = Path(tmp)
        for task in tasks:
            reports.append(probe_task(task, args.top_k, db_cache, tmp_root))

    _print_report(reports, embeddings_active)

    unreachable = [r["task_id"] for r in reports if not r["all_reachable"]]
    if unreachable:
        print(f"UNREACHABLE TASKS: {unreachable}")

    if args.out:
        out_path = Path(args.out)
        out_path.write_text(
            json.dumps(
                {"embeddings_active": embeddings_active, "results": reports}, indent=2
            )
        )
        print(f"wrote {out_path}")

    return 1 if unreachable else 0


if __name__ == "__main__":
    raise SystemExit(main())
