import argparse
import json
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

from embeddings.provider import EmbeddingProvider
from evaluation.runner import EvaluationReport, run_evaluation
from indexing.embedding_queue import queue_status, run_embedding_worker
from indexing.indexer import IndexRunReport, reindex_index
from models.entities.import_references import ImportReference
from models.entities.resolved_import_reference import ResolvedImportReference
from retrieval.context_builder import ContextPack
from retrieval.hybrid_retriever import HybridRetrieval
from retrieval.index_queries import (
    build_context_pack_from_index,
    build_hybrid_retriever,
)
from storage.index_store import count_rows, current_generation

DEFAULT_DB_DIRNAME = ".ckg"
DEFAULT_DB_FILENAME = "index.sqlite"


def _get_version() -> str:
    try:
        from importlib.metadata import version as _pkg_version

        return _pkg_version("code-knowledge-graph")
    except Exception:
        pass
    # fallback for source checkouts without installed metadata
    try:
        import tomllib  # Python 3.11+

        pyproject = Path(__file__).with_name("pyproject.toml")
        if pyproject.exists():
            with pyproject.open("rb") as fh:
                data = tomllib.load(fh)
                return data.get("project", {}).get("version", "0.0.0+source")
    except Exception:
        pass
    return "0.0.0+source"


def _is_tty() -> bool:
    try:
        return sys.stderr.isatty()
    except Exception:
        return False


def _emit_progress(message: str) -> None:
    if _is_tty():
        print(message, file=sys.stderr)


def default_db_path(root: str) -> str:
    return str(Path(root) / DEFAULT_DB_DIRNAME / DEFAULT_DB_FILENAME)


def has_embeddings(db_path: str) -> bool:
    return count_rows(db_path)["embeddings"] > 0


# ---- commands (pure, testable independently of argument parsing) ----


def cmd_index(
    root: str,
    db_path: str,
    *,
    provider: EmbeddingProvider | None = None,
) -> IndexRunReport:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    if _is_tty():
        print(f"Indexing {root}...", file=sys.stderr)

    report = reindex_index(db_path, root, on_progress=_emit_progress if _is_tty() else None)

    if _is_tty():
        print(f"Parsed {report.parsed_files} files...", file=sys.stderr)

    if provider is not None:
        # drain embeddings in batches so large repos emit periodic progress
        # instead of appearing hung; suppress when stderr is not a TTY
        total = 0
        batch_size = 50
        while True:
            batch_report = run_embedding_worker(
                db_path, provider, limit=batch_size, on_progress=_emit_progress if _is_tty() else None
            )
            if batch_report.claimed == 0:
                break
            total += batch_report.done
            if _is_tty():
                print(f"Embedded {total} chunks...", file=sys.stderr)
            if batch_report.claimed < batch_size:
                # check if any pending remain; if not, break, else continue
                try:
                    pending = queue_status(db_path)
                    runnable = pending.get("PENDING", 0) + max(0, pending.get("FAILED", 0) - pending.get("exhausted", 0))
                    if runnable == 0:
                        break
                except Exception:
                    break

    return report


def cmd_status(db_path: str) -> dict[str, object]:
    from storage.index_store import count_rows

    counts = count_rows(db_path)

    return {
        "generation": current_generation(db_path),
        "documents": counts["documents"],
        "symbols": counts["symbols"],
        "chunks": counts["chunks"],
        "embeddings": counts["embeddings"],
        "embedding_jobs": queue_status(db_path),
    }


def cmd_search(
    db_path: str,
    query: str,
    *,
    provider: EmbeddingProvider | None = None,
    top_k: int = 5,
) -> HybridRetrieval:
    retriever = build_hybrid_retriever(db_path, provider=provider)
    return retriever.retrieve(query, top_k=top_k)


def cmd_definition(db_path: str, name: str) -> HybridRetrieval:
    retriever = build_hybrid_retriever(db_path)
    return retriever.retrieve(f"where is {name} defined")


def cmd_callers(db_path: str, name: str) -> HybridRetrieval:
    retriever = build_hybrid_retriever(db_path)
    return retriever.retrieve(f"who calls {name}")


def cmd_callees(db_path: str, name: str) -> HybridRetrieval:
    retriever = build_hybrid_retriever(db_path)
    return retriever.retrieve(f"what does {name} call")


def cmd_imports(
    db_path: str,
    relative_path: str,
) -> list[tuple[ImportReference, ResolvedImportReference | None]]:
    from storage.index_store import load_imports_for_path

    return load_imports_for_path(db_path, relative_path)


def cmd_context(
    db_path: str,
    query: str,
    *,
    token_budget: int,
    provider: EmbeddingProvider | None = None,
    top_k: int = 5,
) -> ContextPack:
    return build_context_pack_from_index(
        db_path,
        query,
        token_budget=token_budget,
        provider=provider,
        top_k=top_k,
    )


def cmd_eval(
    *, provider: EmbeddingProvider | None = None, top_k: int = 5
) -> EvaluationReport:
    return run_evaluation(provider=provider, top_k=top_k)


def cmd_watch(
    root: str,
    db_path: str,
    *,
    provider: EmbeddingProvider | None = None,
    debounce_seconds: float = 0.5,
    embed_limit: int | None = 200,
) -> None:
    from indexing.watcher import watch_repository

    watch_repository(
        root,
        db_path,
        provider=provider,
        debounce_seconds=debounce_seconds,
        embed_limit=embed_limit,
        on_report=lambda report: _print_index_report(report, db_path),
    )


def resolve_provider(db_path: str, *, use_vector: bool) -> EmbeddingProvider | None:
    if not use_vector or not has_embeddings(db_path):
        return None

    from embeddings.local_provider import LocalEmbeddingProvider

    return LocalEmbeddingProvider()


def _ensure_mcp_entry(path: Path, container_key: str) -> str:
    entry: dict[str, object] = {"command": "ckg-mcp"}
    if path.exists():
        # An unreadable or non-object config is the user's file, not ours to
        # replace: rewriting it would silently discard whatever they had.
        text = path.read_text(encoding="utf-8")

        try:
            data: dict = json.loads(text) if text.strip() else {}
        except json.JSONDecodeError as error:
            raise ValueError(f"{path} is not valid JSON: {error}") from error

        if not isinstance(data, dict):
            raise ValueError(f"{path} must contain a JSON object")

        # check if already configured under any common container
        for key in (container_key, "mcpServers", "servers", "mcp"):
            container = data.get(key)
            if isinstance(container, dict) and "ckg" in container:
                return "already configured"
        container = data.get(container_key)
        if not isinstance(container, dict):
            data[container_key] = {}
            container = data[container_key]
        if "ckg" in container:
            return "already configured"
        container["ckg"] = entry
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        return "written"
    else:
        data = {container_key: {"ckg": entry}}
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        return "written"


def cmd_init(root: str = ".") -> dict[str, str]:
    root_path = Path(root)
    targets: list[tuple[Path, str]] = []
    # default always .mcp.json
    targets.append((root_path / ".mcp.json", "mcpServers"))
    if (root_path / ".vscode").is_dir():
        targets.append((root_path / ".vscode" / "mcp.json", "mcpServers"))
    if (root_path / ".cursor").is_dir():
        targets.append((root_path / ".cursor" / "mcp.json", "mcpServers"))
    if (root_path / "opencode.json").is_file():
        targets.append((root_path / "opencode.json", "mcp"))
    results: dict[str, str] = {}
    for path, container_key in targets:
        status = _ensure_mcp_entry(path, container_key)
        results[str(path)] = status
    return results


def cmd_embed(
    db_path: str,
    *,
    provider: EmbeddingProvider | None = None,
    limit: int | None = None,
):
    if provider is None:
        from embeddings.local_provider import LocalEmbeddingProvider

        provider = LocalEmbeddingProvider()
    if limit is None:
        # when no explicit limit, drain in batches with periodic progress
        total = 0
        batch_size = 50
        last_report = None
        while True:
            batch_report = run_embedding_worker(
                db_path, provider, limit=batch_size, on_progress=_emit_progress if _is_tty() else None
            )
            if batch_report.claimed == 0:
                if last_report is None:
                    return batch_report
                break
            last_report = batch_report
            total += batch_report.done
            if _is_tty():
                print(f"Embedded {total} chunks...", file=sys.stderr)
            # peek queue to decide continuation
            try:
                pending = queue_status(db_path)
                runnable = pending.get("PENDING", 0) + max(0, pending.get("FAILED", 0) - pending.get("exhausted", 0))
                if runnable == 0:
                    break
            except Exception:
                break
        return last_report if last_report is not None else batch_report
    return run_embedding_worker(db_path, provider, limit=limit, on_progress=_emit_progress if _is_tty() else None)


def _background_lock_path(db_path: str) -> Path:
    return Path(db_path).parent / f".{Path(db_path).name}.embed.lock"


def _try_acquire_embed_lock(db_path: str, lease: int = 300) -> bool:
    lock = _background_lock_path(db_path)
    now = time.time()
    if lock.exists():
        try:
            mtime = lock.stat().st_mtime
            if now - mtime < lease:
                return False
            lock.unlink()
        except OSError:
            return False
    try:
        lock.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        return True
    except FileExistsError:
        return False
    except OSError:
        return False


def _maybe_spawn_background_embed(db_path: str) -> None:
    # skip when queue empty (common after first run due to hash reuse)
    try:
        counts = queue_status(db_path)
        pending = counts.get("PENDING", 0)
        failed = counts.get("FAILED", 0)
        exhausted = counts.get("exhausted", 0)
        runnable = pending + max(0, failed - exhausted)
        if runnable == 0:
            return
    except Exception:  # noqa: BLE001
        return
    if not _try_acquire_embed_lock(db_path):
        return
    code = (
        "import sys\n"
        "from pathlib import Path\n"
        "db_path=sys.argv[1]\n"
        "lock=Path(db_path).parent / f'.{Path(db_path).name}.embed.lock'\n"
        "try:\n"
        "    from embeddings.local_provider import LocalEmbeddingProvider\n"
        "    from indexing.embedding_queue import run_embedding_worker\n"
        "    provider=LocalEmbeddingProvider()\n"
        "    run_embedding_worker(db_path, provider)\n"
        "except Exception:\n"
        "    pass\n"
        "finally:\n"
        "    try:\n"
        "        lock.unlink()\n"
        "    except Exception:\n"
        "        pass\n"
    )
    try:
        subprocess.Popen(
            [sys.executable, "-c", code, db_path],
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
        )
    except Exception:  # noqa: BLE001
        try:
            _background_lock_path(db_path).unlink()
        except Exception:  # noqa: BLE001, S110
            pass


# ---- output formatting ----


def _print_index_report(report: IndexRunReport, db_path: str) -> None:
    counts: dict[str, int] = {}
    for change in report.changes.values():
        counts[change.value] = counts.get(change.value, 0) + 1

    print(f"Indexed into {db_path}")
    print(f"  parsed files:        {report.parsed_files}")
    print(f"  resolved references: {report.resolved_references}")
    for kind in ("new", "changed", "unchanged", "deleted"):
        if kind in counts:
            print(f"  {kind}: {counts[kind]}")


def _print_status(status: dict, *, oneline: bool = False) -> None:
    if oneline:
        jobs = status["embedding_jobs"]
        pending = jobs.get("PENDING", 0) + jobs.get("FAILED", 0) - jobs.get("exhausted", 0)
        pending = max(0, pending)
        print(f"symbols {status['symbols']} chunks {status['chunks']} pending {pending} gen {status['generation']}")
        return
    print(f"generation: {status['generation']}")
    print(f"documents:  {status['documents']}")
    print(f"symbols:    {status['symbols']}")
    print(f"chunks:     {status['chunks']}")
    chunks = status["chunks"]
    embeddings = status["embeddings"]
    if chunks:
        pct = (embeddings / chunks * 100) if chunks else 0
        if embeddings < chunks:
            print(f"embeddings: {embeddings}/{chunks} ({pct:.0f}%) — run `ckg embed` to enable vector search")
        else:
            print(f"embeddings: {embeddings}/{chunks} ({pct:.0f}%)")
    else:
        print(f"embeddings: {embeddings}")

    jobs = status["embedding_jobs"]
    if jobs:
        job_summary = ", ".join(f"{k}={v}" for k, v in sorted(jobs.items()))
        print(f"embedding queue: {job_summary}")
        pending = jobs.get("PENDING", 0) + jobs.get("FAILED", 0) - jobs.get("exhausted", 0)
        if pending > 0 and embeddings < chunks:
            print(f"vector search degraded: {pending} chunks pending embedding — run `ckg embed`")


def _print_embed_report(report) -> None:
    print(f"embeddings: claimed={report.claimed} done={report.done} reused={report.reused} stale={report.stale} failed={report.failed}")


def _print_candidates(retrieval: HybridRetrieval) -> None:
    if not retrieval.candidates:
        print("No results.")
        return

    for candidate in retrieval.candidates:
        sources = ",".join(candidate.sources)
        print(
            f"{candidate.qualified_name or candidate.symbol_name} "
            f"({candidate.symbol_kind}) — {candidate.relative_path} "
            f"[score={candidate.score:.3f} sources={sources}]"
        )


def _print_imports(
    imports: list[tuple[ImportReference, ResolvedImportReference | None]],
) -> None:
    if not imports:
        print("No imports found.")
        return

    for import_reference, resolved in imports:
        target = "unresolved"

        if resolved is not None:
            target = resolved.target_document.relative_path
            if resolved.target_symbol is not None:
                target += f"::{resolved.target_symbol.name}"

        print(
            f"{import_reference.local_name} <- {import_reference.imported_name} "
            f'from "{import_reference.module_path}" -> {target}'
        )


def _print_context_pack(pack: ContextPack) -> None:
    print(f"context for: {pack.query}")
    print(f"tokens: {pack.total_tokens}/{pack.token_budget}")

    for label, entries in (
        ("primary", pack.primary_definitions),
        ("supporting", pack.supporting_definitions),
    ):
        for entry in entries:
            print(
                f"\n[{label}] {entry.qualified_name} ({entry.symbol_kind}) — {entry.location}"
            )
            if entry.source:
                print(entry.source)

    if pack.relationships:
        print("\nrelationships:")
        for relationship in pack.relationships:
            print(f"  {relationship}")


def _print_eval_report(report: EvaluationReport) -> None:
    print("Benchmark: fixed evaluation repo (tests/fixtures/evaluation_repo)\n")

    for question in report.questions:
        correct = (
            "-"
            if question.correct is None
            else ("PASS" if question.correct else "FAIL")
        )
        print(
            f"[{question.category:10}] {correct:4} "
            f"recall@k={question.recall_at_k:.2f} mrr={question.reciprocal_rank:.2f} "
            f"{question.text}"
        )

    print()
    print(f"definition accuracy:        {report.definition_accuracy:.2f}")
    print(f"relationship accuracy:      {report.relationship_accuracy:.2f}")
    print(f"import resolution accuracy: {report.import_resolution_accuracy:.2f}")
    print(f"mean recall@k:              {report.mean_recall_at_k:.2f}")
    print(f"mean reciprocal rank:       {report.mean_reciprocal_rank:.2f}")
    print(
        f"context tokens:             {report.context_tokens} "
        f"(baseline {report.baseline_tokens}, "
        f"{report.token_reduction * 100:.1f}% reduction)"
    )
    print(
        f"initial indexing:           {report.initial_indexing_seconds * 1000:.1f} ms"
    )
    print(
        f"incremental indexing:       {report.incremental_indexing_seconds * 1000:.1f} ms"
    )
    print(f"embedding cache hit rate:   {report.embedding_cache_hit_rate:.2f}")


# ---- argument parsing / dispatch ----


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ckg")
    parser.add_argument("--version", action="version", version=_get_version())
    parser.add_argument("--db", help="override the index database path")

    subparsers = parser.add_subparsers(dest="command", required=True)

    index_parser = subparsers.add_parser(
        "index", help="build or update the semantic index"
    )
    index_parser.add_argument("path")
    index_parser.add_argument(
        "--embed", action="store_true", help="also run the embedding worker"
    )
    index_parser.add_argument(
        "--no-background",
        action="store_true",
        help="disable background embedding drain",
    )

    status_parser = subparsers.add_parser(
        "status", help="show index generation and counts"
    )
    status_parser.add_argument("path", nargs="?", default=".")
    status_parser.add_argument(
        "--oneline", action="store_true", help="one-line summary for shell prompts"
    )

    search_parser = subparsers.add_parser("search", help="hybrid search over the index")
    search_parser.add_argument("query")
    search_parser.add_argument("path", nargs="?", default=".")
    search_parser.add_argument("--top-k", type=int, default=5)
    search_parser.add_argument("--no-vector", action="store_true")

    definition_parser = subparsers.add_parser(
        "definition", help="find where a symbol is defined"
    )
    definition_parser.add_argument("name")
    definition_parser.add_argument("path", nargs="?", default=".")

    callers_parser = subparsers.add_parser("callers", help="find callers of a symbol")
    callers_parser.add_argument("name")
    callers_parser.add_argument("path", nargs="?", default=".")

    callees_parser = subparsers.add_parser("callees", help="find callees of a symbol")
    callees_parser.add_argument("name")
    callees_parser.add_argument("path", nargs="?", default=".")

    imports_parser = subparsers.add_parser("imports", help="list a file's imports")
    imports_parser.add_argument("file")
    imports_parser.add_argument("path", nargs="?", default=".")

    context_parser = subparsers.add_parser(
        "context", help="build a token-budgeted context pack"
    )
    context_parser.add_argument("query")
    context_parser.add_argument("path", nargs="?", default=".")
    context_parser.add_argument("--budget", type=int, default=2000)
    context_parser.add_argument("--top-k", type=int, default=5)
    context_parser.add_argument("--no-vector", action="store_true")

    eval_parser = subparsers.add_parser(
        "eval", help="run the fixed benchmark and report retrieval/indexing metrics"
    )
    eval_parser.add_argument(
        "--embed", action="store_true", help="also exercise vector search"
    )
    eval_parser.add_argument("--top-k", type=int, default=5)

    watch_parser = subparsers.add_parser(
        "watch", help="keep the index fresh by watching for file changes"
    )
    watch_parser.add_argument("path")
    watch_parser.add_argument(
        "--no-embed",
        action="store_true",
        help="disable embedding worker after each reindex",
    )
    watch_parser.add_argument(
        "--debounce",
        type=float,
        default=0.5,
        help="seconds of edit quiet before reindexing (default 0.5)",
    )

    init_parser = subparsers.add_parser(
        "init", help="configure MCP for this project"
    )
    init_parser.add_argument("path", nargs="?", default=".")

    embed_parser = subparsers.add_parser(
        "embed", help="drain the embedding queue"
    )
    embed_parser.add_argument("path", nargs="?", default=".")
    embed_parser.add_argument("--limit", type=int, default=None)

    return parser


def _require_dir(path: str) -> None:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"path '{path}' does not exist")
    if not p.is_dir():
        raise NotADirectoryError(f"path '{path}' is not a directory")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        # validate target paths before dispatch
        if args.command in ("index", "watch"):
            _require_dir(args.path)
        elif args.command not in ("eval",) and hasattr(args, "path"):
            _require_dir(args.path)

        if args.command == "index":
            db_path = args.db or default_db_path(args.path)
            provider = None

            if args.embed:
                from embeddings.local_provider import LocalEmbeddingProvider

                provider = LocalEmbeddingProvider()

            report = cmd_index(args.path, db_path, provider=provider)
            _print_index_report(report, db_path)
            if not args.no_background and not args.embed:
                _maybe_spawn_background_embed(db_path)
            return 0

        if args.command == "eval":
            provider = None

            if args.embed:
                from embeddings.local_provider import LocalEmbeddingProvider

                provider = LocalEmbeddingProvider()

            _print_eval_report(cmd_eval(provider=provider, top_k=args.top_k))
            return 0

        if args.command == "init":
            try:
                results = cmd_init(args.path)
            except (ValueError, OSError) as error:
                print(f"Could not configure MCP: {error}", file=sys.stderr)
                return 1

            for file_path, status in results.items():
                if status == "already configured":
                    print(f"already configured: {file_path}")
                else:
                    print(f"Wrote {file_path}")
            return 0

        db_path = args.db or default_db_path(args.path)

        if args.command == "watch":
            if args.no_embed:
                provider = None
            else:
                from embeddings.local_provider import LocalEmbeddingProvider

                provider = LocalEmbeddingProvider()

            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            print(f"Watching {args.path} (index: {db_path})")
            cmd_watch(
                args.path,
                db_path,
                provider=provider,
                debounce_seconds=args.debounce,
                embed_limit=200,
            )
            return 0

        if not Path(db_path).exists():
            print(f"No index found at {db_path}. Run `ckg index {args.path}` first.")
            return 1

        if args.command == "embed":
            report = cmd_embed(db_path, limit=args.limit)
            _print_embed_report(report)
        elif args.command == "status":
            _print_status(cmd_status(db_path), oneline=getattr(args, "oneline", False))
        elif args.command == "search":
            provider = resolve_provider(db_path, use_vector=not args.no_vector)
            if provider is None:
                try:
                    qs = queue_status(db_path)
                    pending = qs.get("PENDING", 0) + qs.get("FAILED", 0) - qs.get("exhausted", 0)
                    if pending > 0:
                        print(f"vector search inactive: {pending} chunks pending embedding — run `ckg embed`")
                except Exception:  # noqa: BLE001, S110
                    pass
            _print_candidates(
                cmd_search(db_path, args.query, provider=provider, top_k=args.top_k)
            )
        elif args.command == "definition":
            _print_candidates(cmd_definition(db_path, args.name))
        elif args.command == "callers":
            _print_candidates(cmd_callers(db_path, args.name))
        elif args.command == "callees":
            _print_candidates(cmd_callees(db_path, args.name))
        elif args.command == "imports":
            _print_imports(cmd_imports(db_path, args.file))
        elif args.command == "context":
            provider = resolve_provider(db_path, use_vector=not args.no_vector)
            if provider is None:
                try:
                    qs = queue_status(db_path)
                    pending = qs.get("PENDING", 0) + qs.get("FAILED", 0) - qs.get("exhausted", 0)
                    if pending > 0:
                        print(f"vector search inactive: {pending} chunks pending embedding — run `ckg embed`")
                except Exception:  # noqa: BLE001, S110
                    pass
            _print_context_pack(
                cmd_context(
                    db_path,
                    args.query,
                    token_budget=args.budget,
                    provider=provider,
                    top_k=args.top_k,
                )
            )

        return 0
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except NotADirectoryError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except sqlite3.Error as exc:
        db = locals().get("db_path", "index")
        print(f"Database error at {db}: {exc} — try removing the database and re-running `ckg index`.", file=sys.stderr)
        return 1
    except ImportError as exc:
        print(f"Embeddings unavailable: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        if getattr(args, "embed", False) or args.command in ("embed", "eval"):
            print(f"Embeddings unavailable: {exc}", file=sys.stderr)
        else:
            print(f"Error: {exc}", file=sys.stderr)
        return 1
    except (ValueError, RuntimeError) as exc:
        if getattr(args, "embed", False) or args.command in ("embed", "eval"):
            print(f"Embeddings unavailable: {exc}", file=sys.stderr)
            return 1
        raise


if __name__ == "__main__":
    sys.exit(main())
