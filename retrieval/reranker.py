import re
from dataclasses import dataclass

from graph.code_graph import CodeGraph
from models.entities.symbols import Symbol
from retrieval.candidate import HybridCandidate

RELATIONSHIP_WEIGHT = 1.0
EXACT_SYMBOL_WEIGHT = 0.8
GRAPH_DISTANCE_WEIGHT = 0.4
PATH_WEIGHT = 0.3
KIND_WEIGHT = 0.2
FTS_WEIGHT = 0.1
VECTOR_WEIGHT = 0.1

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

TOKEN_PATTERN = re.compile(r"[A-Za-z_]\w*")

_WEIGHTS = (
    EXACT_SYMBOL_WEIGHT,
    PATH_WEIGHT,
    KIND_WEIGHT,
    FTS_WEIGHT,
    VECTOR_WEIGHT,
    GRAPH_DISTANCE_WEIGHT,
    RELATIONSHIP_WEIGHT,
)


@dataclass(slots=True)
class RerankFeatures:
    exact_symbol: float
    path_match: float
    kind_match: float
    fts: float
    vector: float
    graph_distance: float
    relationship: float

    def boost(self) -> float:
        values = (
            self.exact_symbol,
            self.path_match,
            self.kind_match,
            self.fts,
            self.vector,
            self.graph_distance,
            self.relationship,
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


def rerank_candidates(
    candidates: list[HybridCandidate],
    query: str,
    *,
    graph: CodeGraph,
    symbols_by_key: dict[str, Symbol],
    seed: Symbol | None = None,
    preference: str | None = None,
) -> list[HybridCandidate]:
    tokens = set(_tokens(query))

    for candidate in candidates:
        features = _features(
            candidate,
            tokens,
            graph=graph,
            symbols_by_key=symbols_by_key,
            seed=seed,
            preference=preference,
        )
        candidate.score += features.boost()

    return sorted(candidates, key=lambda candidate: candidate.score, reverse=True)


def _features(
    candidate: HybridCandidate,
    tokens: set[str],
    *,
    graph: CodeGraph,
    symbols_by_key: dict[str, Symbol],
    seed: Symbol | None,
    preference: str | None,
) -> RerankFeatures:
    symbol = symbols_by_key.get(candidate.chunk_key)

    return RerankFeatures(
        exact_symbol=1.0 if candidate.symbol_name.lower() in tokens else 0.0,
        path_match=_path_match(candidate, tokens),
        kind_match=1.0 if candidate.symbol_kind in tokens else 0.0,
        fts=1.0 if "fts" in candidate.sources else 0.0,
        vector=1.0 if "vector" in candidate.sources else 0.0,
        graph_distance=_graph_distance(symbol, seed, graph),
        relationship=_relationship(symbol, seed, graph, preference),
    )


def _path_match(candidate: HybridCandidate, tokens: set[str]) -> float:
    path_tokens = set(_tokens(candidate.relative_path)) | set(
        _tokens(candidate.qualified_name)
    )
    hits = len(path_tokens & tokens)
    return min(hits / 2.0, 1.0)


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
        return 1.0 if symbol.symbol_id in {c.symbol_id for c in graph.callers_of(seed.symbol_id)} else 0.0

    if preference == PREFERENCE_CALLEE:
        return 1.0 if symbol.symbol_id in {c.symbol_id for c in graph.callees_of(seed.symbol_id)} else 0.0

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


def _matches(query: str, patterns: tuple[re.Pattern, ...]) -> bool:
    return any(pattern.search(query) for pattern in patterns)


def _tokens(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_PATTERN.findall(text)]