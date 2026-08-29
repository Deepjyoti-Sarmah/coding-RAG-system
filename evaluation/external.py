"""External benchmark harness — file-level ground truth from CCE queries.

Ground truth is expected_files (paths relative to source_dir), not symbol
names.  Candidates are chunks; several can share a file, so dedupe to
file paths and retrieve wider (top_k=30) to yield min(10, distinct files
available) distinct files.
"""
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
import statistics

from embeddings.provider import EmbeddingProvider
from evaluation.metrics import mean, recall_at_k, reciprocal_rank
from indexing.embedding_queue import run_embedding_worker
from indexing.indexer import reindex_index
from retrieval.index_queries import build_hybrid_retriever
from storage.index_store import load_index


@dataclass(frozen=True, slots=True)
class ExternalQuestion:
    query: str
    expected_files: frozenset[str]
    category: str = ""


@dataclass(slots=True)
class ExternalQuestionResult:
    query: str
    expected_files: frozenset[str]
    category: str
    ranked_files: list[str]  # deduped distinct files in rank order
    precision_at_10: float
    recall_at_10: float
    reciprocal_rank: float
    latency_seconds: float
    precision_ceiling_at_10: float = 0.0
    precision_at_10_normalized: float = 0.0
    precision_over_returned: float = 0.0


@dataclass(slots=True)
class ExternalReport:
    repo: str
    source_dir: str
    commit: str | None
    questions: list[ExternalQuestionResult] = field(default_factory=list)
    mean_precision_at_10: float = 0.0
    mean_recall_at_10: float = 0.0
    mean_reciprocal_rank: float = 0.0
    mean_precision_ceiling_at_10: float = 0.0
    mean_precision_at_10_normalized: float = 0.0
    mean_precision_over_returned: float = 0.0
    p50_latency_seconds: float = 0.0
    p95_latency_seconds: float = 0.0
    index_seconds: float = 0.0
    total_questions: int = 0


def load_external_questions(path: str | Path) -> list[ExternalQuestion]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    questions: list[ExternalQuestion] = []
    for entry in data:
        query = entry.get("query", "")
        expected = entry.get("expected_files", [])
        category = entry.get("category", "")
        questions.append(
            ExternalQuestion(
                query=query,
                expected_files=frozenset(expected),
                category=category,
            )
        )
    return questions


def _dedupe_files(candidates, limit: int = 10) -> list[str]:
    """Deduplicate chunk candidates to distinct file paths in rank order."""
    seen: set[str] = set()
    files: list[str] = []
    for c in candidates:
        fp = c.relative_path
        if fp not in seen:
            seen.add(fp)
            files.append(fp)
            if len(files) >= limit:
                break
    return files


def _precision_at_k(expected: frozenset[str], ranked: list[str], k: int = 10) -> float:
    if not expected or k == 0:
        return 0.0
    top = ranked[:k]
    hits = sum(1 for f in top if f in expected)
    return hits / k


def _precision_ceiling_at_k(expected: frozenset[str], k: int = 10) -> float:
    if k == 0:
        return 0.0
    return min(len(expected), k) / k


def _precision_over_returned(expected: frozenset[str], ranked: list[str]) -> float:
    if not ranked:
        return 0.0
    hits = sum(1 for f in ranked if f in expected)
    return hits / len(ranked)


def run_external_evaluation(
    repo_dir: str | Path,
    questions: list[ExternalQuestion],
    *,
    provider: EmbeddingProvider | None = None,
    top_k: int = 30,
    file_k: int = 10,
    db_path: str | Path | None = None,
) -> ExternalReport:
    """Run file-level evaluation over a materialized repo directory.

    Indexes repo_dir (which should be the source_dir, so expected_files
    paths line up), optionally embeds, then retrieves with top_k=30 and
    dedupes to file_k distinct files for metrics.
    """
    repo_path = Path(repo_dir)
    if db_path is None:
        import tempfile

        tmp = tempfile.mkdtemp()
        db_path = str(Path(tmp) / "index.sqlite")
        # Caller is expected to manage temp dir for external harness; we
        # just use a temp file here if not provided.
    else:
        db_path = str(db_path)

    start = time.perf_counter()
    reindex_index(db_path, str(repo_path))
    index_seconds = time.perf_counter() - start

    if provider is not None:
        run_embedding_worker(db_path, provider)

    # Load index to verify but retriever handles its own DB connection
    # We don't need load_index for retrieval, but useful for sanity.
    _ = load_index(db_path)
    retriever = build_hybrid_retriever(db_path, provider=provider)

    results: list[ExternalQuestionResult] = []
    latencies: list[float] = []

    for q in questions:
        start = time.perf_counter()
        retrieval = retriever.retrieve(q.query, top_k=top_k)
        latency = time.perf_counter() - start
        latencies.append(latency)

        ranked_files = _dedupe_files(retrieval.candidates, limit=file_k)

        prec = _precision_at_k(q.expected_files, ranked_files, k=file_k)
        rec = recall_at_k(q.expected_files, ranked_files, k=file_k)
        rr = reciprocal_rank(q.expected_files, ranked_files)
        ceiling = _precision_ceiling_at_k(q.expected_files, k=file_k)
        normalized = (prec / ceiling) if ceiling > 0 else 0.0
        over_ret = _precision_over_returned(q.expected_files, ranked_files)

        results.append(
            ExternalQuestionResult(
                query=q.query,
                expected_files=q.expected_files,
                category=q.category,
                ranked_files=ranked_files,
                precision_at_10=prec,
                recall_at_10=rec,
                reciprocal_rank=rr,
                latency_seconds=latency,
                precision_ceiling_at_10=ceiling,
                precision_at_10_normalized=normalized,
                precision_over_returned=over_ret,
            )
        )

    mean_p = mean(r.precision_at_10 for r in results)
    mean_r = mean(r.recall_at_10 for r in results)
    mean_rr = mean(r.reciprocal_rank for r in results)
    mean_ceiling = mean(r.precision_ceiling_at_10 for r in results)
    mean_norm = mean(r.precision_at_10_normalized for r in results)
    mean_over = mean(r.precision_over_returned for r in results)
    p50 = statistics.median(latencies) if latencies else 0.0
    # p95 as 95th percentile
    p95 = 0.0
    if latencies:
        sorted_lat = sorted(latencies)
        idx = int(0.95 * len(sorted_lat))
        idx = min(idx, len(sorted_lat) - 1)
        p95 = sorted_lat[idx]

    return ExternalReport(
        questions=results,
        mean_precision_at_10=mean_p,
        mean_recall_at_10=mean_r,
        mean_reciprocal_rank=mean_rr,
        mean_precision_ceiling_at_10=mean_ceiling,
        mean_precision_at_10_normalized=mean_norm,
        mean_precision_over_returned=mean_over,
        p50_latency_seconds=p50,
        p95_latency_seconds=p95,
        index_seconds=index_seconds,
        total_questions=len(results),
        repo="",
        source_dir=str(repo_path),
        commit=None,
    )
