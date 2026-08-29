#!/usr/bin/env python3
"""Diagnostic-only index coverage audit for CKG.

Reuses the real ingestion/analysis pipeline (ingestion.loader,
analysis.build_graph, chunking.symbol_chunker) rather than
reimplementing it, so results cannot disagree with production
indexing behavior. Makes no changes to that pipeline.

For a given repo (optionally scoped to a --source-dir), reports:
  - files walked
  - files skipped, broken out by reason (excluded dir, extension,
    size, ignore rules, read error)
  - documents created
  - documents yielding zero symbols
  - documents yielding zero chunks
  - per-file symbol/chunk counts (--verbose or --json)

--check <comma-separated relative paths> answers, for each named
file (relative to the audited root), which stage lost it: never
walked / skipped (with reason) / no symbols / no chunks / indexed
fine.

Usage:
  python benchmarks/audit_coverage.py /path/to/repo --source-dir fastapi
  python benchmarks/audit_coverage.py /path/to/repo --check middleware/cors.py,routing.py
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Unconditional: a stale editable-install copy of config.py can sit ahead
# of ROOT in sys.path even when ROOT is technically already present
# further back - see benchmarks/run_external.py for the full story.
sys.path.insert(0, str(ROOT))

from config import INCLUDE_EXTENSIONS, MAX_FILE_SIZE_BYTES  # noqa: E402
from ingestion.ignore_rules import load_ignore_rules  # noqa: E402
from ingestion.loader import is_inside_excluded_dir, should_skip_file  # noqa: E402
from analysis.build_graph import build_graph  # noqa: E402


SKIP_REASONS = ("excluded_dir", "extension", "size", "ignore_rules")


@dataclass
class WalkResult:
    files_walked: int = 0
    skipped: dict[str, int] = field(
        default_factory=lambda: {reason: 0 for reason in SKIP_REASONS}
    )
    skipped_paths: dict[str, list[str]] = field(
        default_factory=lambda: {reason: [] for reason in SKIP_REASONS}
    )
    kept: list[tuple[Path, str]] = field(default_factory=list)


def classify_walk(root_path: Path) -> WalkResult:
    """Walk root_path exactly as ingestion.loader.iter_repo_files does,
    but record *why* each dropped file was dropped.

    Mirrors iter_repo_files' check order (excluded dir -> should_skip_file
    -> ignore rules) using the loader's own predicates, so the skip
    decision itself is never reimplemented — only the reason label is
    derived locally (should_skip_file conflates extension/size into one
    bool).
    """
    result = WalkResult()

    is_single_file = root_path.is_file()
    ignore_rules = None if is_single_file else load_ignore_rules(root_path)
    files = [root_path] if is_single_file else root_path.rglob("*")

    for file_path in files:
        if not file_path.is_file():
            continue

        result.files_walked += 1

        relative_path = (
            file_path.name
            if is_single_file
            else str(file_path.relative_to(root_path))
        )

        if is_inside_excluded_dir(file_path):
            result.skipped["excluded_dir"] += 1
            result.skipped_paths["excluded_dir"].append(relative_path)
            continue

        if should_skip_file(file_path):
            reason = (
                "extension"
                if file_path.suffix.lower() not in INCLUDE_EXTENSIONS
                else "size"
            )
            result.skipped[reason] += 1
            result.skipped_paths[reason].append(relative_path)
            continue

        if ignore_rules is not None and ignore_rules.is_ignored(relative_path):
            result.skipped["ignore_rules"] += 1
            result.skipped_paths["ignore_rules"].append(relative_path)
            continue

        result.kept.append((file_path, relative_path))

    return result


def audit(root: Path, *, verbose: bool = False) -> dict:
    walk = classify_walk(root)

    build_result = build_graph(str(root))
    documents = build_result.documents

    doc_relpaths = {d.relative_path for d in documents}
    kept_relpaths = {rel for _, rel in walk.kept}
    read_error_relpaths = sorted(kept_relpaths - doc_relpaths)

    symbol_count: dict[str, int] = defaultdict(int)
    for s in build_result.symbols:
        symbol_count[s.document_id] += 1

    chunk_count: dict[str, int] = defaultdict(int)
    for c in build_result.chunks:
        chunk_count[c.relative_path] += 1

    zero_symbol_docs = sorted(
        d.relative_path for d in documents if symbol_count[d.document_id] == 0
    )
    zero_chunk_docs = sorted(
        d.relative_path for d in documents if chunk_count[d.relative_path] == 0
    )

    per_file = {
        d.relative_path: {
            "symbols": symbol_count[d.document_id],
            "chunks": chunk_count[d.relative_path],
        }
        for d in documents
    }

    report = {
        "root": str(root),
        "files_walked": walk.files_walked,
        "skipped": dict(walk.skipped),
        "skipped_total": sum(walk.skipped.values()),
        "documents_created": len(documents),
        "documents_read_error": len(read_error_relpaths),
        "documents_zero_symbols": len(zero_symbol_docs),
        "documents_zero_chunks": len(zero_chunk_docs),
        "total_symbols": len(build_result.symbols),
        "total_chunks": len(build_result.chunks),
    }

    if verbose:
        report["skipped_paths"] = dict(walk.skipped_paths)
        report["read_error_paths"] = read_error_relpaths
        report["zero_symbol_paths"] = zero_symbol_docs
        report["zero_chunk_paths"] = zero_chunk_docs
        report["per_file"] = per_file

    return {
        "_walk": walk,
        "_build_result": build_result,
        "_doc_relpaths": doc_relpaths,
        "_symbol_count": symbol_count,
        "_chunk_count": chunk_count,
        "report": report,
    }


def check_file(state: dict, root: Path, relpath: str) -> str:
    walk: WalkResult = state["_walk"]
    doc_relpaths: set[str] = state["_doc_relpaths"]
    build_result = state["_build_result"]
    symbol_count = state["_symbol_count"]
    chunk_count = state["_chunk_count"]

    file_path = root / relpath

    if not file_path.exists() or not file_path.is_file():
        return "never walked (file does not exist under root)"

    for reason in SKIP_REASONS:
        if relpath in walk.skipped_paths[reason]:
            return f"skipped: {reason}"

    kept_relpaths = {rel for _, rel in walk.kept}
    if relpath not in kept_relpaths:
        return "never walked (not found during rglob traversal)"

    if relpath not in doc_relpaths:
        return "read_error (failed to decode/read as utf-8)"

    doc = next(d for d in build_result.documents if d.relative_path == relpath)

    n_symbols = symbol_count[doc.document_id]
    if n_symbols == 0:
        return "no_symbols (document parsed, zero symbols extracted)"

    n_chunks = chunk_count[relpath]
    if n_chunks == 0:
        return f"no_chunks (symbols={n_symbols}, but zero chunks built)"

    return f"indexed fine (symbols={n_symbols}, chunks={n_chunks})"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("repo_path", help="Path to a repo checkout on disk")
    parser.add_argument("--source-dir", default=None, help="Subdirectory relative to repo_path to audit")
    parser.add_argument("--verbose", action="store_true", help="Include per-file symbol/chunk counts and path lists")
    parser.add_argument("--json", default=None, help="Write full report as JSON to this path")
    parser.add_argument("--check", default=None, help="Comma-separated relative paths to diagnose stage-by-stage")
    args = parser.parse_args()

    root = Path(args.repo_path).resolve()
    if args.source_dir:
        root = root / args.source_dir
    root = root.resolve()

    if not root.exists():
        print(f"error: {root} does not exist", file=sys.stderr)
        return 1

    state = audit(root, verbose=args.verbose or bool(args.json))
    report = state["report"]

    print(f"root: {root}")
    print(f"files walked: {report['files_walked']}")
    print(f"skipped ({report['skipped_total']} total):")
    for reason in SKIP_REASONS:
        print(f"  {reason}: {report['skipped'][reason]}")
    print(f"documents created: {report['documents_created']}")
    print(f"documents read error (kept by walk, failed to load): {report['documents_read_error']}")
    print(f"documents with zero symbols: {report['documents_zero_symbols']}")
    print(f"documents with zero chunks: {report['documents_zero_chunks']}")
    print(f"total symbols: {report['total_symbols']}")
    print(f"total chunks: {report['total_chunks']}")

    if args.verbose:
        print()
        print("zero-symbol files:")
        for p in report["zero_symbol_paths"]:
            print(f"  {p}")

    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"\nWrote {args.json}", file=sys.stderr)

    if args.check:
        print()
        print("--check results:")
        for relpath in args.check.split(","):
            relpath = relpath.strip()
            if not relpath:
                continue
            stage = check_file(state, root, relpath)
            print(f"  {relpath}: {stage}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
