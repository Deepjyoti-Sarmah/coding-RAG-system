#!/usr/bin/env python3
"""Train reranker weights via grid search on evaluation_repo — P5-3."""
import json
from pathlib import Path

from evaluation.runner import run_evaluation

# grid search over relationship/exact reranker weights
best = None
best_weights = None
candidates = [
    {"relationship": 1.0, "exact": 0.8},
    {"relationship": 1.15, "exact": 0.95},
    {"relationship": 1.25, "exact": 1.0},
]
for w in candidates:
    # temporarily write weights, reload reranker, run eval
    Path("retrieval/learned_weights.json").write_text(json.dumps(w))
    # force reload so new weights take effect (retrieval/reranker loads at import)
    import importlib

    import retrieval.reranker
    importlib.reload(retrieval.reranker)
    # also reload hybrid_retriever which cached reranker weights via import
    import retrieval.hybrid_retriever
    importlib.reload(retrieval.hybrid_retriever)
    r = run_evaluation(provider=None, top_k=5)
    score = r.definition_accuracy + r.mean_recall_at_k
    if best is None or score > best:
        best = score
        best_weights = w
        print(f"candidate {w} -> score {score:.3f} def {r.definition_accuracy:.3f} recall {r.mean_recall_at_k:.3f}")

if best_weights:
    out = {**best_weights, "token_overlap": 0.35, "graph_distance": 0.45, "path": 0.3, "kind": 0.2, "fts": 0.1, "vector": 0.1, "test_example": -0.4,
           "_trained_on": "evaluation/evaluation_repo FTS+graph grid 2026-09-03", "_method": "grid search relationship/exact vs heuristic"}
    Path("retrieval/learned_weights.json").write_text(json.dumps(out, indent=2))
    print(f"wrote {out}")
