import argparse
import sys
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

    report = reindex_index(db_path, root)

    if provider is not None:
        run_embedding_worker(db_path, provider)

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
) -> None:
    from indexing.watcher import watch_repository

    watch_repository(
        root,
        db_path,
        provider=provider,
        debounce_seconds=debounce_seconds,
        on_report=lambda report: _print_index_report(report, db_path),
    )


def resolve_provider(db_path: str, *, use_vector: bool) -> EmbeddingProvider | None:
    if not use_vector or not has_embeddings(db_path):
        return None

    from embeddings.local_provider import LocalEmbeddingProvider

    return LocalEmbeddingProvider()


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


def _print_status(status: dict) -> None:
    print(f"generation: {status['generation']}")
    print(f"documents:  {status['documents']}")
    print(f"symbols:    {status['symbols']}")
    print(f"chunks:     {status['chunks']}")
    print(f"embeddings: {status['embeddings']}")

    jobs = status["embedding_jobs"]
    if jobs:
        job_summary = ", ".join(f"{k}={v}" for k, v in sorted(jobs.items()))
        print(f"embedding queue: {job_summary}")


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
    parser.add_argument("--db", help="override the index database path")

    subparsers = parser.add_subparsers(dest="command", required=True)

    index_parser = subparsers.add_parser(
        "index", help="build or update the semantic index"
    )
    index_parser.add_argument("path")
    index_parser.add_argument(
        "--embed", action="store_true", help="also run the embedding worker"
    )

    status_parser = subparsers.add_parser(
        "status", help="show index generation and counts"
    )
    status_parser.add_argument("path", nargs="?", default=".")

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
        "--embed",
        action="store_true",
        help="also run the embedding worker after each reindex",
    )
    watch_parser.add_argument(
        "--debounce",
        type=float,
        default=0.5,
        help="seconds of edit quiet before reindexing (default 0.5)",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "index":
        db_path = args.db or default_db_path(args.path)
        provider = None

        if args.embed:
            from embeddings.local_provider import LocalEmbeddingProvider

            provider = LocalEmbeddingProvider()

        report = cmd_index(args.path, db_path, provider=provider)
        _print_index_report(report, db_path)
        return 0

    if args.command == "eval":
        provider = None

        if args.embed:
            from embeddings.local_provider import LocalEmbeddingProvider

            provider = LocalEmbeddingProvider()

        _print_eval_report(cmd_eval(provider=provider, top_k=args.top_k))
        return 0

    db_path = args.db or default_db_path(args.path)

    if args.command == "watch":
        provider = None

        if args.embed:
            from embeddings.local_provider import LocalEmbeddingProvider

            provider = LocalEmbeddingProvider()

        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        print(f"Watching {args.path} (index: {db_path})")
        cmd_watch(
            args.path,
            db_path,
            provider=provider,
            debounce_seconds=args.debounce,
        )
        return 0

    if not Path(db_path).exists():
        print(f"No index found at {db_path}. Run `ckg index {args.path}` first.")
        return 1

    if args.command == "status":
        _print_status(cmd_status(db_path))
    elif args.command == "search":
        provider = resolve_provider(db_path, use_vector=not args.no_vector)
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


if __name__ == "__main__":
    sys.exit(main())
