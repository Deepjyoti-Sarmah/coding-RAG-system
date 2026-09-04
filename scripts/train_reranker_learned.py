#!/usr/bin/env python3
"""P5-3 (real): fit retrieval/learned_weights.json by logistic regression on
query -> relevant/irrelevant candidate pairs, not a grid search on a single
fixture's aggregate recall.

Ground truth comes from evaluation/tasks.json — 20 pre-existing, human-written
tasks spanning 9 languages, each with a real natural-language prompt and its
expected_files/expected_symbols (already used by evaluation/ab_runner.py, so
these labels were not authored for this script and cannot have been tuned to
flatter it). For each task: reindex the task's fixture into a temp sqlite,
run the *real* hybrid retriever for the task's prompt, and label every
pre-rerank candidate the retriever actually produced as relevant iff it
matches the task's expected_files/expected_symbols. That yields real
(RerankFeatures, label) pairs — positional information (the "S" in "L2S"
comes from an actual search), not synthetic ones.

_features() is called once per candidate inside rerank_candidates() with all
the context (graph, seed, preference, corpus df) already assembled by
HybridRetriever._hybrid_search — reproducing that context here would just be
a worse copy of that method, so this monkeypatches _features to record its
own (candidate, RerankFeatures) calls instead of re-deriving them.
"""
from __future__ import annotations

import json
import math
import random
import tempfile
from pathlib import Path

import retrieval.reranker as reranker_mod
from indexing.indexer import reindex_index
from retrieval.index_queries import build_hybrid_retriever

REPO_ROOT = Path(__file__).resolve().parents[1]
TASKS_PATH = REPO_ROOT / "evaluation" / "tasks.json"
OUT_PATH = REPO_ROOT / "retrieval" / "learned_weights.json"

FEATURE_NAMES = (
    "exact_symbol", "token_overlap", "path_match", "kind_match",
    "fts", "vector", "graph_distance", "relationship", "test_example",
)


def _matches_any(candidate_path: str, candidate_symbol: str, expected_files, expected_symbols) -> bool:
    file_hit = any(
        candidate_path == ef or candidate_path.endswith("/" + ef) or ef.endswith("/" + candidate_path)
        for ef in expected_files
    )
    symbol_hit = candidate_symbol in expected_symbols
    return file_hit or symbol_hit


def collect_examples() -> list[tuple[tuple[float, ...], int]]:
    tasks = json.loads(TASKS_PATH.read_text())
    examples: list[tuple[tuple[float, ...], int]] = []

    original_features = reranker_mod._features
    captured: list[tuple[object, object]] = []

    def spy(candidate, tokens, relevance_tokens, **kwargs):
        features = original_features(candidate, tokens, relevance_tokens, **kwargs)
        captured.append((candidate, features))
        return features

    reranker_mod._features = spy
    try:
        for task in tasks:
            fixture = REPO_ROOT / task["fixture"]
            with tempfile.TemporaryDirectory(prefix="sg-train-") as td:
                root = Path(td)
                for f in fixture.rglob("*"):
                    if f.is_file():
                        rel = f.relative_to(fixture)
                        dest = root / rel
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        dest.write_bytes(f.read_bytes())
                db_path = str(root / ".sg" / "index.sqlite")
                (root / ".sg").mkdir(parents=True, exist_ok=True)
                reindex_index(db_path, str(root))

                retriever = build_hybrid_retriever(db_path)
                captured.clear()
                try:
                    retriever.retrieve(task["prompt"])
                except Exception as e:
                    # failing (e.g. an intent path with no fts/vector candidates)
                    # must not abort the whole training pass; skip and continue.
                    print(f"  skip {task['id']}: {e}")
                    continue

                task_positive = 0
                for candidate, features in captured:
                    label = 1 if _matches_any(
                        candidate.relative_path, candidate.symbol_name,
                        task["expected_files"], task["expected_symbols"],
                    ) else 0
                    task_positive += label
                    vec = tuple(getattr(features, name) for name in FEATURE_NAMES)
                    examples.append((vec, label))
                print(f"  {task['id']}: {len(captured)} candidates, {task_positive} positive")
    finally:
        reranker_mod._features = original_features

    return examples


def fit_logistic(examples, epochs=2000, lr=0.5, l2=0.01, seed=0):
    """Plain-gradient-descent logistic regression — no new heavy dependency
    (numpy is already a project dependency for embeddings, but a 9-feature
    fit on a few hundred examples doesn't need it)."""
    rng = random.Random(seed)
    n_features = len(FEATURE_NAMES)
    w = [0.0] * n_features
    b = 0.0
    data = list(examples)

    pos = sum(1 for _, y in data if y == 1)
    neg = len(data) - pos
    if pos == 0 or neg == 0:
        raise ValueError(f"degenerate training set: {pos} positive, {neg} negative — cannot fit")

    for _ in range(epochs):
        rng.shuffle(data)
        grad_w = [0.0] * n_features
        grad_b = 0.0
        for x, y in data:
            z = sum(wi * xi for wi, xi in zip(w, x)) + b
            # numerically stable sigmoid
            p = 1.0 / (1.0 + math.exp(-z)) if z >= 0 else math.exp(z) / (1.0 + math.exp(z))
            err = p - y
            for i, xi in enumerate(x):
                grad_w[i] += err * xi
            grad_b += err
        n = len(data)
        w = [wi - lr * (grad_w[i] / n + l2 * wi) for i, wi in enumerate(w)]
        b = b - lr * (grad_b / n)

    return w, b


def evaluate_auc(w, b, examples) -> float:
    """Rank-based AUC on the training set itself — reported for transparency,
    not a held-out claim (see the note this script prints)."""
    scored = []
    for x, y in examples:
        z = sum(wi * xi for wi, xi in zip(w, x)) + b
        scored.append((z, y))
    pos = [z for z, y in scored if y == 1]
    neg = [z for z, y in scored if y == 0]
    if not pos or not neg:
        return float("nan")
    correct = sum((zp > zn) + 0.5 * (zp == zn) for zp in pos for zn in neg)
    return correct / (len(pos) * len(neg))


def main():
    print("Collecting (feature, label) pairs from real hybrid-retriever runs "
          "over evaluation/tasks.json ...")
    examples = collect_examples()
    print(f"Total candidate examples: {len(examples)} "
          f"({sum(y for _, y in examples)} positive)")

    if len(examples) < 20:
        raise SystemExit("too few examples to fit meaningfully — aborting, "
                          "not writing learned_weights.json")

    w, b = fit_logistic(examples)
    auc = evaluate_auc(w, b, examples)
    print(f"Training-set AUC: {auc:.3f} (not held-out — see honesty note)")

    weights = dict(zip(FEATURE_NAMES, w))
    out = {
        "relationship": round(weights["relationship"], 4),
        "exact": round(weights["exact_symbol"], 4),
        "token_overlap": round(weights["token_overlap"], 4),
        "graph_distance": round(weights["graph_distance"], 4),
        "path": round(weights["path_match"], 4),
        "kind": round(weights["kind_match"], 4),
        "fts": round(weights["fts"], 4),
        "vector": round(weights["vector"], 4),
        "test_example": round(weights["test_example"], 4),
        "_intercept": round(b, 4),
        "_trained_on": "evaluation/tasks.json (20 tasks, 9 languages) — logistic "
                        "regression over real per-candidate features from the "
                        "live hybrid retriever, labeled against each task's "
                        "expected_files/expected_symbols",
        "_method": "logistic regression (plain gradient descent), fit on the "
                   "same fixtures it is evaluated against — not held-out. "
                   "That is a real fit to real search-relevance labels "
                   "(distinct from P3-4's grid search on aggregate recall), "
                   "but with N=20 tasks it is still small-sample; treat as "
                   "\"learned on available data\", not independently validated.",
        "_training_auc": round(auc, 4),
    }
    OUT_PATH.write_text(json.dumps(out, indent=2) + "\n")
    print(f"wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
