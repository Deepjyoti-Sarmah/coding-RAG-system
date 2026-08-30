import shutil
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

from embeddings.provider import EmbeddingProvider
from evaluation.benchmark import (
    BENCHMARK_QUESTIONS,
    BENCHMARK_REPO,
    CALLEES,
    CALLERS,
    DEFINITION,
    IMPORTERS,
    Question,
)
from evaluation.metrics import (
    accuracy,
    mean,
    recall_at_k,
    reciprocal_rank,
    token_reduction,
)
from indexing.diff import importers_of
from indexing.embedding_queue import run_embedding_worker
from indexing.indexer import reindex_index
from retrieval.context_builder import build_context_pack, estimate_tokens
from retrieval.index_queries import build_hybrid_retriever
from storage.index_store import load_index

RECALL_K = 5


@dataclass(slots=True)
class QuestionResult:
    question_id: str
    text: str
    category: str
    kind: str
    correct: bool | None  # None when there is no deterministic ground-truth check
    recall_at_k: float
    reciprocal_rank: float
    latency_seconds: float


@dataclass(slots=True)
class EvaluationReport:
    questions: list[QuestionResult] = field(default_factory=list)

    definition_accuracy: float = 1.0
    relationship_accuracy: float = 1.0
    import_resolution_accuracy: float = 1.0

    mean_recall_at_k: float = 0.0
    mean_reciprocal_rank: float = 0.0

    context_tokens: int = 0
    baseline_tokens: int = 0
    token_reduction: float = 0.0

    initial_indexing_seconds: float = 0.0
    incremental_indexing_seconds: float = 0.0

    embedding_cache_hit_rate: float = 0.0


def run_evaluation_on_repo(
    repo_dir: str | Path,
    questions: tuple[Question, ...] | list[Question],
    *,
    provider: EmbeddingProvider | None = None,
    top_k: int = RECALL_K,
    token_budget: int = 800,
    db_path: str | None = None,
) -> EvaluationReport:
    """Core evaluation over an already-materialized repo directory.

    Used by `run_evaluation` (which copies the fixture) and by the
    external harness (`evaluation.external`) which clones real repos.
    """
    repo_path = Path(repo_dir)
    # When db_path is None, caller manages its own temp dir; otherwise
    # we create a temporary DB alongside. For external harness the caller
    # provides db_path inside its own temp dir.
    tmp_obj = None
    if db_path is None:
        tmp_obj = tempfile.TemporaryDirectory()
        db_path = str(Path(tmp_obj.name) / "index.sqlite")

    try:
        start = time.perf_counter()
        reindex_index(db_path, str(repo_path))
        initial_indexing_seconds = time.perf_counter() - start

        # A no-op reindex over an unchanged repo is the cheapest possible
        # incremental run and is what "steady state" looks like in practice.
        start = time.perf_counter()
        reindex_index(db_path, str(repo_path))
        incremental_indexing_seconds = time.perf_counter() - start

        embedding_cache_hit_rate = 0.0
        if provider is not None:
            # Only the fixture has token.ts for the cache-hit micro-benchmark.
            # For external repos we skip this and report 0.0.
            token_file = repo_path / "token.ts"
            if token_file.exists():
                embedding_cache_hit_rate = _measure_embedding_cache_hit_rate(
                    repo_dir=repo_path,
                    db_path=db_path,
                    provider=provider,
                )
            else:
                # Still need to embed everything once for retrieval.
                run_embedding_worker(db_path, provider)

        result = load_index(db_path)
        retriever = build_hybrid_retriever(db_path, provider=provider)

        documents_by_id = {d.document_id: d for d in result.documents}
        importers = importers_of(
            import_references=result.import_references,
            documents_by_id=documents_by_id,
        )
        importer_paths_by_module = {
            module_path: {documents_by_id[doc_id].relative_path for doc_id in doc_ids}
            for module_path, doc_ids in importers.items()
        }

        question_results: list[QuestionResult] = []
        definition_checks: list[bool] = []
        relationship_checks: list[bool] = []
        import_checks: list[bool] = []
        context_token_counts: list[int] = []

        for question in questions:
            start = time.perf_counter()
            retrieval = retriever.retrieve(question.text, top_k=top_k)
            latency = time.perf_counter() - start

            # "importers" ground truth is expressed in file-path space, not
            # symbol-name space, so rank candidates by relative_path there.
            ranked = [
                candidate.relative_path
                if question.kind == IMPORTERS
                else candidate.symbol_name
                for candidate in retrieval.candidates
            ]

            correct = _check_ground_truth(
                question,
                result=result,
                importer_paths_by_module=importer_paths_by_module,
            )

            if question.kind == DEFINITION:
                definition_checks.append(bool(correct))
            elif question.kind in (CALLERS, CALLEES):
                relationship_checks.append(bool(correct))
            elif question.kind == IMPORTERS:
                import_checks.append(bool(correct))

            pack = build_context_pack(
                retrieval.candidates,
                query=question.text,
                graph=result.graph,
                symbols_by_key={s.stable_key: s for s in result.symbols},
                token_budget=token_budget,
            )
            context_token_counts.append(pack.total_tokens)

            question_results.append(
                QuestionResult(
                    question_id=question.id,
                    text=question.text,
                    category=question.category,
                    kind=question.kind,
                    correct=correct,
                    recall_at_k=recall_at_k(question.relevant, ranked, top_k),
                    reciprocal_rank=reciprocal_rank(question.relevant, ranked),
                    latency_seconds=latency,
                )
            )

        # Whole-repo baseline — not a savings denominator. Reporting
        # 1 - context/whole_repo would be ~99% and is indefensible; the
        # honest baseline is ground-truth files, which the fixture doesn't
        # have per query (unlike external.py where expected_files provides it).
        # Keep raw counts but do not claim savings.
        baseline_tokens = estimate_tokens(
            "\n".join(document.content for document in result.documents)
        )
        context_tokens = round(mean(context_token_counts))

        return EvaluationReport(
            questions=question_results,
            definition_accuracy=accuracy(definition_checks),
            relationship_accuracy=accuracy(relationship_checks),
            import_resolution_accuracy=accuracy(import_checks),
            mean_recall_at_k=mean(r.recall_at_k for r in question_results),
            mean_reciprocal_rank=mean(r.reciprocal_rank for r in question_results),
            context_tokens=context_tokens,
            baseline_tokens=baseline_tokens,
            token_reduction=0.0,
            initial_indexing_seconds=initial_indexing_seconds,
            incremental_indexing_seconds=incremental_indexing_seconds,
            embedding_cache_hit_rate=embedding_cache_hit_rate,
        )
    finally:
        if tmp_obj is not None:
            tmp_obj.cleanup()


def run_evaluation(
    *,
    provider: EmbeddingProvider | None = None,
    top_k: int = RECALL_K,
    token_budget: int = 800,
) -> EvaluationReport:
    with tempfile.TemporaryDirectory() as tmp:
        repo_dir = Path(tmp) / "repo"
        shutil.copytree(BENCHMARK_REPO, repo_dir)
        db_path = str(Path(tmp) / "index.sqlite")
        return run_evaluation_on_repo(
            repo_dir,
            BENCHMARK_QUESTIONS,
            provider=provider,
            top_k=top_k,
            token_budget=token_budget,
            db_path=db_path,
        )


def _measure_embedding_cache_hit_rate(
    *,
    repo_dir: Path,
    db_path: str,
    provider: EmbeddingProvider,
) -> float:
    """Fraction of chunks that avoid re-embedding after a single-symbol edit.

    Embeds every chunk once, edits exactly one symbol's body, then
    re-indexes and re-embeds. Only the edited symbol's chunk should need a
    fresh embedding; every other chunk should sit at DONE without ever being
    claimed by the worker - that's the queue-level equivalent of a cache hit
    (Phase 18 never re-enqueues a chunk whose content hash hasn't changed).
    """
    token_file = repo_dir / "token.ts"
    original_content = token_file.read_text(encoding="utf-8")
    # Editing inside a function body (not just appending to the file) is
    # required: chunk identity is keyed off each *symbol's* content hash,
    # so a change outside every symbol span wouldn't touch any chunk.
    edited_content = original_content.replace("token.length > 0", "token.length > 1")
    assert edited_content != original_content

    total_chunks = len(load_index(db_path).chunks)
    run_embedding_worker(db_path, provider)

    token_file.write_text(edited_content, encoding="utf-8")
    reindex_index(db_path, str(repo_dir))
    edit_report = run_embedding_worker(db_path, provider)

    token_file.write_text(original_content, encoding="utf-8")
    reindex_index(db_path, str(repo_dir))

    if total_chunks == 0:
        return 1.0

    return 1.0 - (edit_report.claimed / total_chunks)


def _check_ground_truth(
    question: Question,
    *,
    result,
    importer_paths_by_module: dict[str, set[str]],
) -> bool | None:
    if question.kind == DEFINITION:
        matches = [s for s in result.symbols if s.name == question.target]
        return (
            len(matches) == 1 and matches[0].relative_path == question.expected_location
        )

    if question.kind == CALLERS:
        matches = [s for s in result.symbols if s.name == question.target]
        if len(matches) != 1:
            return False
        callers = {s.name for s in result.graph.callers_of(matches[0].symbol_id)}
        return callers == set(question.relevant)

    if question.kind == CALLEES:
        matches = [s for s in result.symbols if s.name == question.target]
        if len(matches) != 1:
            return False
        callees = {s.name for s in result.graph.callees_of(matches[0].symbol_id)}
        return callees == set(question.relevant)

    if question.kind == IMPORTERS:
        actual = importer_paths_by_module.get(question.target, set())
        return actual == set(question.relevant)

    return None
