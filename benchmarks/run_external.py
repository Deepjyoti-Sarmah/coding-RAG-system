#!/usr/bin/env python3
"""Clone a real repo, index its source_dir, and run file-level retrieval evaluation.

Pin each repo to a commit SHA and record it in the output; CCE's runner
clones HEAD, so its numbers drift.

Usage:
  python benchmarks/run_external.py --repo https://github.com/expressjs/express.git --source-dir lib --queries benchmarks/express_queries.json [--commit abc123] [--output benchmarks/results/express.json]
"""
import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# Ensure repo root is on sys.path for imports when run as script
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.external import load_external_questions, run_external_evaluation


def _git(cmd: list[str], cwd: Path | None = None) -> str:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=True)
    return result.stdout.strip()


def clone_repo(repo_url: str, dest: Path, commit: str | None = None) -> str:
    _git(["git", "clone", "--depth", "1", repo_url, str(dest)])
    if commit:
        # Fetch the specific commit if shallow clone didn't contain it
        try:
            _git(["git", "fetch", "--depth", "1", "origin", commit], cwd=dest)
            _git(["git", "checkout", commit], cwd=dest)
        except subprocess.CalledProcessError:
            # Fallback: fetch all and try again
            _git(["git", "fetch", "origin"], cwd=dest)
            _git(["git", "checkout", commit], cwd=dest)
        # Verify
        actual = _git(["git", "rev-parse", "HEAD"], cwd=dest)
        return actual
    else:
        actual = _git(["git", "rev-parse", "HEAD"], cwd=dest)
        return actual


def main() -> int:
    parser = argparse.ArgumentParser(description="Run external file-level benchmark")
    parser.add_argument("--repo", required=True, help="Clone URL")
    parser.add_argument("--source-dir", required=True, help="Source directory relative to repo root (e.g., lib, fastapi, .)")
    parser.add_argument("--queries", required=True, help="Path to query JSON (CCE format)")
    parser.add_argument("--commit", default=None, help="Commit SHA to pin (default: HEAD)")
    parser.add_argument("--output", default=None, help="Output JSON path")
    parser.add_argument("--no-embed", action="store_true", help="Disable vector search (default: enabled)")
    args = parser.parse_args()

    repo_url = args.repo
    source_dir = args.source_dir
    queries_path = args.queries
    commit = args.commit
    output = args.output

    questions = load_external_questions(queries_path)
    print(f"Loaded {len(questions)} queries from {queries_path}", file=sys.stderr)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        clone_dest = tmp_path / "repo"
        print(f"Cloning {repo_url} ...", file=sys.stderr)
        actual_commit = clone_repo(repo_url, clone_dest, commit=commit)
        print(f"Cloned at {actual_commit}", file=sys.stderr)

        # Resolve source_dir relative to clone
        if source_dir == ".":
            repo_dir = clone_dest
        else:
            repo_dir = clone_dest / source_dir
            if not repo_dir.exists():
                print(f"source_dir {source_dir} does not exist in {clone_dest}", file=sys.stderr)
                return 1

        # Use a DB inside tmp
        db_path = str(tmp_path / "index.sqlite")

        provider = None
        if not args.no_embed:
            try:
                from embeddings.local_provider import LocalEmbeddingProvider

                print("Loading embedding model all-MiniLM-L6-v2 ...", file=sys.stderr)
                provider = LocalEmbeddingProvider()
            except Exception as e:
                print(f"Failed to load embedding model: {e}", file=sys.stderr)
                provider = None

        print(f"Indexing {repo_dir} ...", file=sys.stderr)
        report = run_external_evaluation(
            repo_dir,
            questions,
            provider=provider,
            db_path=db_path,
        )
        report.repo = repo_url
        report.source_dir = source_dir
        report.commit = actual_commit

        # Build output dict
        output_data = {
            "repo": repo_url,
            "source_dir": source_dir,
            "commit": actual_commit,
            "queries_file": str(queries_path),
            "total_questions": report.total_questions,
            "mean_precision_at_10": report.mean_precision_at_10,
            "mean_recall_at_10": report.mean_recall_at_10,
            "mean_reciprocal_rank": report.mean_reciprocal_rank,
            "p50_latency_seconds": report.p50_latency_seconds,
            "p95_latency_seconds": report.p95_latency_seconds,
            "index_seconds": report.index_seconds,
            "questions": [
                {
                    "query": r.query,
                    "expected_files": sorted(r.expected_files),
                    "ranked_files": r.ranked_files,
                    "precision_at_10": r.precision_at_10,
                    "recall_at_10": r.recall_at_10,
                    "reciprocal_rank": r.reciprocal_rank,
                    "latency_seconds": r.latency_seconds,
                    "category": r.category,
                }
                for r in report.questions
            ],
        }

        # Print summary to stderr
        print(f"\nResults for {repo_url} @ {actual_commit[:8]} ({source_dir})", file=sys.stderr)
        print(f"  Questions: {report.total_questions}", file=sys.stderr)
        print(f"  P@10: {report.mean_precision_at_10:.3f}", file=sys.stderr)
        print(f"  R@10: {report.mean_recall_at_10:.3f}", file=sys.stderr)
        print(f"  MRR: {report.mean_reciprocal_rank:.3f}", file=sys.stderr)
        print(f"  p50 latency: {report.p50_latency_seconds*1000:.1f} ms", file=sys.stderr)
        print(f"  p95 latency: {report.p95_latency_seconds*1000:.1f} ms", file=sys.stderr)
        print(f"  Index time: {report.index_seconds:.1f} s", file=sys.stderr)

        if output:
            Path(output).parent.mkdir(parents=True, exist_ok=True)
            Path(output).write_text(json.dumps(output_data, indent=2), encoding="utf-8")
            print(f"Wrote {output}", file=sys.stderr)
        else:
            print(json.dumps(output_data, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
