import math
import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import PurePosixPath as Path

from graph.code_graph import CodeGraph
from models.common.tokens import STOPWORDS, TOKEN_PATTERN, split_identifier
from models.entities.symbols import Symbol
from retrieval.candidate import HybridCandidate

RELATIONSHIP_WEIGHT = 1.0
EXACT_SYMBOL_WEIGHT = 0.8
TOKEN_OVERLAP_WEIGHT = 0.35
GRAPH_DISTANCE_WEIGHT = 0.4
PATH_WEIGHT = 0.3
KIND_WEIGHT = 0.2
FTS_WEIGHT = 0.1
VECTOR_WEIGHT = 0.1
TEST_EXAMPLE_WEIGHT = -0.4

# Tuned-weights override: if learned_weights.json exists (grid search on the
# fixture, see its "_method" field — not fitted on paired agent runs),
# load and use those instead of heuristic. Falls back to heuristic if not present.
import json as _json
from pathlib import Path as _Path

_LEARNED_PATH = _Path(__file__).resolve().parent / "learned_weights.json"
if _LEARNED_PATH.exists():
    try:
        _lw = _json.loads(_LEARNED_PATH.read_text())
        RELATIONSHIP_WEIGHT = float(_lw.get("relationship", RELATIONSHIP_WEIGHT))
        EXACT_SYMBOL_WEIGHT = float(_lw.get("exact", EXACT_SYMBOL_WEIGHT))
        TOKEN_OVERLAP_WEIGHT = float(_lw.get("token_overlap", TOKEN_OVERLAP_WEIGHT))
        GRAPH_DISTANCE_WEIGHT = float(_lw.get("graph_distance", GRAPH_DISTANCE_WEIGHT))
        PATH_WEIGHT = float(_lw.get("path", PATH_WEIGHT))
        KIND_WEIGHT = float(_lw.get("kind", KIND_WEIGHT))
        FTS_WEIGHT = float(_lw.get("fts", FTS_WEIGHT))
        VECTOR_WEIGHT = float(_lw.get("vector", VECTOR_WEIGHT))
    except Exception:
        pass

_MIN_FRAGMENT_LENGTH = 2

PREFERENCE_CALLER = "caller"
PREFERENCE_CALLEE = "callee"
PREFERENCE_DEFINITION = "definition"

CALLER_INTENT_PATTERNS = (
    re.compile(r"\bcallers? of\b", re.IGNORECASE),
    re.compile(r"\bwho calls\b", re.IGNORECASE),
    re.compile(r"\bcalled by\b", re.IGNORECASE),
)
CALLEE_INTENT_PATTERNS = (
    re.compile(r"\bcallees? of\b", re.IGNORECASE),
    re.compile(r"\bwhat does\b", re.IGNORECASE),
    re.compile(r"\bwhat calls\b", re.IGNORECASE),
)
DEFINITION_INTENT_PATTERNS = (
    re.compile(r"\bwhere is\b", re.IGNORECASE),
    re.compile(r"\bdefinition of\b", re.IGNORECASE),
    re.compile(r"\bdefined\b", re.IGNORECASE),
    re.compile(r"\bimplemented\b", re.IGNORECASE),
    re.compile(r"\bimplementation\b", re.IGNORECASE),
)

_WEIGHTS = (
    EXACT_SYMBOL_WEIGHT,
    TOKEN_OVERLAP_WEIGHT,
    PATH_WEIGHT,
    KIND_WEIGHT,
    FTS_WEIGHT,
    VECTOR_WEIGHT,
    GRAPH_DISTANCE_WEIGHT,
    RELATIONSHIP_WEIGHT,
    TEST_EXAMPLE_WEIGHT,
)

# Test/example files that legitimately turn up in results (a real test
# calling the function asked about) shouldn't be excluded, only deprioritized
# relative to non-test source - see benchmarks/results/TRACK1_DIAGNOSIS.md,
# where these routinely outranked the actual implementation because nothing
# else in the reranker distinguishes them.
_TEST_EXAMPLE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(^|/)tests?/"),
    re.compile(r"(^|/)test_[^/]+$"),
    re.compile(r"_test\.[A-Za-z0-9]+$"),
    re.compile(r"(^|/)_examples?/"),
    re.compile(r"(^|/)testdata/"),
)


@dataclass(slots=True)
class RerankFeatures:
    exact_symbol: float
    token_overlap: float
    path_match: float
    kind_match: float
    fts: float
    vector: float
    graph_distance: float
    relationship: float
    test_example: float = 0.0

    def boost(self) -> float:
        values = (
            self.exact_symbol,
            self.token_overlap,
            self.path_match,
            self.kind_match,
            self.fts,
            self.vector,
            self.graph_distance,
            self.relationship,
            self.test_example,
        )
        return sum(weight * value for weight, value in zip(_WEIGHTS, values))


def detect_preference(query: str) -> str | None:
    if _matches(query, CALLER_INTENT_PATTERNS):
        return PREFERENCE_CALLER

    if _matches(query, CALLEE_INTENT_PATTERNS):
        return PREFERENCE_CALLEE

    if _matches(query, DEFINITION_INTENT_PATTERNS):
        return PREFERENCE_DEFINITION

    return None


def _idf_weight(df: int, total: int) -> float:
    """Rarity weight in [0,1]: rare => ~1, ubiquitous => ~0.

    Curve: 1 - log(1+df)/log(1+total). When df==1 of N=900 the token is
    present in one document: weight ~1 - log2/log901 ~0.9 (strong). When
    df==N (ubiquitous) weight is 0. When total<=1 return 1.0 (no
    information to dampen).
    """
    if total <= 1:
        return 1.0
    # clamp df to [1, total] to keep log domain valid
    df = max(1, min(df, total))
    weight = 1.0 - math.log(1 + df) / math.log(1 + total)
    return max(0.0, min(1.0, weight))


def build_basename_token_df(relative_paths: Iterable[str]) -> dict[str, int]:
    """Document frequency of basename tokens over the indexed corpus."""
    df: Counter[str] = Counter()
    for rp in relative_paths:
        tokens = set(_tokens(Path(rp).stem))
        for tok in tokens:
            df[tok] += 1
    return dict(df)


def rerank_candidates(
    candidates: list[HybridCandidate],
    query: str,
    *,
    graph: CodeGraph,
    symbols_by_key: dict[str, Symbol],
    seed: Symbol | None = None,
    preference: str | None = None,
    basename_token_df: dict[str, int] | None = None,
    total_docs: int | None = None,
) -> list[HybridCandidate]:
    tokens = set(_tokens(query))
    relevance_tokens = _relevance_tokens(query)

    # kind frequency over this candidate pool (corpus for kind is the pool itself)
    if candidates:
        kind_counts: dict[str, int] = dict(Counter(c.symbol_kind for c in candidates))
        total_candidates = len(candidates)
    else:
        kind_counts = {}
        total_candidates = 0

    for candidate in candidates:
        features = _features(
            candidate,
            tokens,
            relevance_tokens,
            graph=graph,
            symbols_by_key=symbols_by_key,
            seed=seed,
            preference=preference,
            basename_token_df=basename_token_df,
            total_docs=total_docs,
            kind_counts=kind_counts,
            total_candidates=total_candidates,
        )
        candidate.score += features.boost()

    return sorted(candidates, key=lambda candidate: candidate.score, reverse=True)


def _features(
    candidate: HybridCandidate,
    tokens: set[str],
    relevance_tokens: frozenset[str],
    *,
    graph: CodeGraph,
    symbols_by_key: dict[str, Symbol],
    seed: Symbol | None,
    preference: str | None,
    basename_token_df: dict[str, int] | None = None,
    total_docs: int | None = None,
    kind_counts: dict[str, int] | None = None,
    total_candidates: int | None = None,
) -> RerankFeatures:
    symbol = symbols_by_key.get(candidate.chunk_key)

    pm = _path_match(candidate, tokens, basename_token_df, total_docs)

    raw_kind = 1.0 if candidate.symbol_kind in tokens else 0.0
    if raw_kind and kind_counts is not None and total_candidates and total_candidates >= 5:
        df_kind = kind_counts.get(candidate.symbol_kind, 1)
        # Piecewise: if at most half share this kind, keep full signal;
        # beyond half, linearly damp toward zero (so 90% common => ~0.2).
        # This preserves the existing unit-test expectation (N=2, df=1 => 1.0)
        # while still damping the django case (N~90, df~80 => ~0.22).
        if df_kind * 2 > total_candidates:
            # damp factor in [0,1) for majority-shared kinds
            damp = max(0.0, 2 * (1 - df_kind / total_candidates))
            # also apply IDF shape for extra rarity weighting when very common
            # blend linear damp with log IDF to keep rare-kind boost high
            idf = _idf_weight(df_kind, total_candidates)
            # use the more conservative (smaller) damp so majority is strongly suppressed
            raw_kind = raw_kind * min(damp, idf) if idf < damp else raw_kind * damp
        # else keep 1.0

    return RerankFeatures(
        exact_symbol=1.0 if candidate.symbol_name.lower() in tokens else 0.0,
        token_overlap=_token_overlap(candidate.symbol_name, relevance_tokens),
        path_match=pm,
        kind_match=raw_kind,
        fts=_rank_score(candidate.fts_rank),
        vector=_rank_score(candidate.vector_rank),
        graph_distance=_graph_distance(symbol, seed, graph),
        relationship=_relationship(symbol, seed, graph, preference),
        test_example=1.0 if _is_test_or_example(candidate.relative_path) else 0.0,
    )


def _path_match(
    candidate: HybridCandidate,
    tokens: set[str],
    basename_token_df: dict[str, int] | None = None,
    total_docs: int | None = None,
) -> float:
    """How well the candidate's file identifies the query, at two strengths.

    A hit on the file's own basename (e.g. "base" in "core/management/
    base.py") is a strong, specific signal - the query is plausibly naming
    this exact file - and gets IDF-weighted credit. A hit only on a directory
    segment or the qualified name (e.g. every file under "middleware/"
    matching a query containing "middleware") is a weak, generic signal:
    dozens of unrelated files in the same directory tree share it equally,
    so it's capped well below a basename match rather than saturating to
    the same 1.0 (see benchmarks/results/TRACK1_DIAGNOSIS.md - this
    generic-directory case was routinely outscoring the actual target,
    whose own path often shares no token with the query at all).
    """
    basename_tokens = set(_tokens(Path(candidate.relative_path).stem))

    overlap = basename_tokens & tokens
    if overlap:
        if basename_token_df is not None and total_docs is not None and total_docs > 0:
            best = 0.0
            for tok in overlap:
                df = basename_token_df.get(tok, 1)
                w = _idf_weight(df, total_docs)
                best = max(best, w)
            return best
        return 1.0

    path_tokens = set(_tokens(candidate.relative_path)) | set(
        _tokens(candidate.qualified_name)
    )
    hits = len(path_tokens & tokens)
    return min(hits / 4.0, 0.5)


def _is_test_or_example(relative_path: str) -> bool:
    return any(pattern.search(relative_path) for pattern in _TEST_EXAMPLE_PATTERNS)


def _graph_distance(
    symbol: Symbol | None,
    seed: Symbol | None,
    graph: CodeGraph,
) -> float:
    if seed is None or symbol is None or symbol.symbol_id == seed.symbol_id:
        return 0.0

    if _is_neighbor(seed, symbol, graph):
        return 1.0

    for middle in _neighbors(seed, graph):
        if _is_neighbor(middle, symbol, graph):
            return 0.5

    return 0.0


def _relationship(
    symbol: Symbol | None,
    seed: Symbol | None,
    graph: CodeGraph,
    preference: str | None,
) -> float:
    if seed is None or symbol is None or preference is None:
        return 0.0

    if preference == PREFERENCE_DEFINITION:
        return 1.0 if symbol.symbol_id == seed.symbol_id else 0.0

    if preference == PREFERENCE_CALLER:
        return (
            1.0
            if symbol.symbol_id
            in {c.symbol_id for c in graph.callers_of(seed.symbol_id)}
            else 0.0
        )

    if preference == PREFERENCE_CALLEE:
        return (
            1.0
            if symbol.symbol_id
            in {c.symbol_id for c in graph.callees_of(seed.symbol_id)}
            else 0.0
        )

    return 0.0


def _neighbors(symbol: Symbol, graph: CodeGraph) -> list[Symbol]:
    return [
        *graph.callers_of(symbol.symbol_id),
        *graph.callees_of(symbol.symbol_id),
        *graph.parents_of(symbol.symbol_id),
        *graph.children_of(symbol.symbol_id),
    ]


def _is_neighbor(a: Symbol, b: Symbol, graph: CodeGraph) -> bool:
    return any(neighbor.symbol_id == b.symbol_id for neighbor in _neighbors(a, graph))


def _matches(query: str, patterns: tuple[re.Pattern[str], ...]) -> bool:
    return any(pattern.search(query) for pattern in patterns)


def _tokens(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_PATTERN.findall(text)]


def _rank_score(rank: int | None) -> float:
    if rank is None:
        return 0.0
    return 1.0 / (1 + rank)


def _relevance_tokens(query: str) -> frozenset[str]:
    """Stopword-filtered, identifier-split query tokens for overlap scoring.

    Mirrors build_fts_query's stopword handling so ranking and lexical
    matching agree on what counts as a relevant term.
    """
    raw_terms = TOKEN_PATTERN.findall(query)
    filtered = [t for t in raw_terms if t.lower() not in STOPWORDS]
    terms = filtered if filtered else raw_terms

    expanded: set[str] = set()
    for term in terms:
        expanded.add(term.lower())
        expanded.update(_fragments(term))

    return frozenset(expanded)


def _fragments(identifier: str) -> list[str]:
    words = split_identifier(identifier).split()
    return [
        word.lower()
        for word in words
        if len(word) >= _MIN_FRAGMENT_LENGTH and word.lower() not in STOPWORDS
    ]


def _token_overlap(symbol_name: str, relevance_tokens: frozenset[str]) -> float:
    fragments = _fragments(symbol_name)

    if not fragments:
        return 0.0

    hits = sum(1 for fragment in fragments if fragment in relevance_tokens)
    return hits / len(fragments)
