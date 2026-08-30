import re
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from graph.code_graph import CodeGraph
from indexing.symbol_index import SymbolIndex
from models.entities.fts_hit import FtsHit
from models.entities.symbols import Symbol
from retrieval.candidate import HybridCandidate
from retrieval.neighborhood import expand_neighborhood
from retrieval.ranking import reciprocal_rank_fusion
from retrieval.reranker import detect_preference, rerank_candidates
from retrieval.vector_store import VectorStore

WHO_CALLS_PATTERN = re.compile(
    r"(?:who\s+(?:calls|invokes)|callers?\s+of|find\s+callers?\s+of)"
    r"\s+([A-Za-z_]\w*)",
    re.IGNORECASE,
)
WHAT_CALLS_PATTERN = re.compile(
    r"(?:what\s+does\s+([A-Za-z_]\w*)\s+call(?:s|\s+into)?|callees?\s+of\s+([A-Za-z_]\w*))",
    re.IGNORECASE,
)
WHERE_IS_PATTERN = re.compile(
    r"(?:where\s+is\s+([A-Za-z_]\w*)\s+(?:defined|implemented|declared)"
    r"|definition\s+of\s+([A-Za-z_]\w*))",
    re.IGNORECASE,
)
WHAT_IMPORTS_PATTERN = re.compile(
    r"(?:(?:what|who|which)\s+(?:files?|modules?)?\s*(?:imports?|uses?)\s+"
    r"([A-Za-z_][\w.]*)|importers?\s+of\s+([A-Za-z_][\w.]*))",
    re.IGNORECASE,
)

# Ordered: first match wins. Callers/callees/definitions are unambiguous
# structural intents; importer phrasings overlap with plain English ("what
# uses X"), so they run last.
_INTENT_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("callers", WHO_CALLS_PATTERN),
    ("callees", WHAT_CALLS_PATTERN),
    ("definition", WHERE_IS_PATTERN),
    ("importers", WHAT_IMPORTS_PATTERN),
]

Intent = tuple[str, str]

TOKEN_PATTERN = re.compile(r"[A-Za-z_]\w*")

FtsSearch = Callable[[str, int], list[FtsHit]]
Embed = Callable[[str], np.ndarray]

# Per-file cap to diversify retrieval: at most this many chunks per file in first pass.
DEFAULT_PER_FILE_CAP = 3


def _select_with_per_file_cap(
    candidates: list["HybridCandidate"],
    top_k: int,
    per_file_cap: int,
) -> list["HybridCandidate"]:
    """Diversity-aware truncation: first pass caps per file, second pass fills remainder."""
    if per_file_cap <= 0 or top_k <= 0:
        return candidates[:top_k]

    selected: list["HybridCandidate"] = []
    counts: dict[str, int] = {}
    skipped: list["HybridCandidate"] = []

    for cand in candidates:
        cnt = counts.get(cand.relative_path, 0)
        if cnt < per_file_cap:
            selected.append(cand)
            counts[cand.relative_path] = cnt + 1
            if len(selected) >= top_k:
                return selected
        else:
            skipped.append(cand)

    # Second pass: admit remainder in rank order if top_k not yet filled
    for cand in skipped:
        if len(selected) >= top_k:
            break
        selected.append(cand)

    return selected[:top_k]


def detect_intent(query: str) -> Intent | None:
    """Extract a structural question from natural language, if present."""
    for name, pattern in _INTENT_PATTERNS:
        match = pattern.search(query)

        if match is None:
            continue

        target = next((group for group in match.groups() if group), None)

        if target is not None:
            return name, target

    return None


@dataclass(slots=True)
class HybridRetrieval:
    strategy: str
    query: str
    candidates: list[HybridCandidate]


class HybridRetriever:
    def __init__(
        self,
        *,
        symbol_index: SymbolIndex,
        graph: CodeGraph,
        fts_search: FtsSearch,
        vector_store: VectorStore | None = None,
        embed: Embed | None = None,
        basename_token_df: dict[str, int] | None = None,
        total_docs: int | None = None,
    ) -> None:
        self.symbol_index = symbol_index
        self.graph = graph
        self.fts_search = fts_search
        self.vector_store = vector_store
        self.embed = embed
        self.basename_token_df = basename_token_df
        self.total_docs = total_docs

    def retrieve(self, query: str, top_k: int = 5, per_file_cap: int = DEFAULT_PER_FILE_CAP) -> HybridRetrieval:
        intent = detect_intent(query)

        if intent is not None:
            result = self._run_intent(intent)

            # A structural lookup with no hits (unknown symbol, unresolved
            # imports) falls through - a hybrid search beats an empty answer.
            if result.candidates:
                return result

        return self._hybrid_search(query, top_k, per_file_cap=per_file_cap)

    def _run_intent(self, intent: Intent) -> HybridRetrieval:
        kind, target = intent

        if kind == "callers":
            return self._graph_callers(target)
        if kind == "callees":
            return self._graph_callees(target)
        if kind == "definition":
            return self._exact_definition(target)
        return self._graph_importers(target)

    def _graph_callers(self, target_name: str) -> HybridRetrieval:
        candidates: list[HybridCandidate] = []

        for symbol in self.symbol_index.lookup_by_name(target_name):
            for caller in self.graph.callers_of(symbol.symbol_id):
                candidates.append(self._from_symbol(caller, sources=("graph",)))

        return HybridRetrieval(
            strategy="graph_callers", query=target_name, candidates=candidates
        )

    def _graph_callees(self, target_name: str) -> HybridRetrieval:
        candidates: list[HybridCandidate] = []

        for symbol in self.symbol_index.lookup_by_name(target_name):
            for callee in self.graph.callees_of(symbol.symbol_id):
                candidates.append(self._from_symbol(callee, sources=("graph",)))

        return HybridRetrieval(
            strategy="graph_callees", query=target_name, candidates=candidates
        )

    def _exact_definition(self, symbol_name: str) -> HybridRetrieval:
        candidates = [
            self._from_symbol(symbol, sources=("exact",))
            for symbol in self.symbol_index.lookup_by_name(symbol_name)
        ]

        return HybridRetrieval(
            strategy="exact_symbol", query=symbol_name, candidates=candidates
        )

    def _graph_importers(self, target_text: str) -> HybridRetrieval:
        candidates: list[HybridCandidate] = []
        seen: set[str] = set()

        surfaces = [
            symbols
            for document_id in self._importer_document_ids(target_text)
            for symbols in [self._importer_surface_symbols(document_id)]
            if symbols
        ]

        for symbols in sorted(surfaces, key=lambda group: group[0].relative_path):
            for symbol in symbols:
                if symbol.stable_key in seen:
                    continue

                seen.add(symbol.stable_key)
                candidates.append(self._from_symbol(symbol, sources=("graph",)))

        return HybridRetrieval(
            strategy="graph_importers",
            query=target_text,
            candidates=candidates,
        )

    def _importer_document_ids(self, target_text: str) -> list[str]:
        """Files importing `target_text`, read as a path or as a symbol name.

        A dot means the caller named a file ("auth.ts", "pkg/auth.go"), so we
        match importers of that document. Otherwise it is a symbol name, and
        we match only importers that resolved to that exact symbol.
        """
        importer_ids: list[str] = []

        if "." in target_text:
            sources = [
                self.graph.importers_of_document(document_id)
                for document_id in self.graph.document_ids_for_path(target_text)
            ]
        else:
            sources = [
                self.graph.importers_of_symbol(symbol.symbol_id)
                for symbol in self.symbol_index.lookup_by_name(target_text)
            ]

        for document_ids in sources:
            for document_id in document_ids:
                if document_id not in importer_ids:
                    importer_ids.append(document_id)

        return importer_ids

    def _importer_surface_symbols(self, document_id: str) -> list[Symbol]:
        module_symbols = [
            symbol
            for symbol in self.symbol_index.lookup_children(None)
            if symbol.document_id == document_id
        ]

        exported_ids = {
            symbol.symbol_id
            for symbol in self.graph.exports_of_document(document_id)
        }

        primary = sorted(
            (s for s in module_symbols if s.symbol_id in exported_ids),
            key=lambda s: s.qualified_name,
        )
        secondary = sorted(
            (s for s in module_symbols if s.symbol_id not in exported_ids),
            key=lambda s: s.qualified_name,
        )

        return primary + secondary

    def _hybrid_search(self, query: str, top_k: int, per_file_cap: int = DEFAULT_PER_FILE_CAP) -> HybridRetrieval:
        ranked: list[list[str]] = []
        source_by_key: dict[str, set[str]] = {}

        fts_hits = self.fts_search(query, top_k * 3)
        fts_meta = {hit.chunk_key: hit for hit in fts_hits}
        fts_rank_by_key = {hit.chunk_key: rank for rank, hit in enumerate(fts_hits)}

        if fts_hits:
            ranked.append([hit.chunk_key for hit in fts_hits])

            for hit in fts_hits:
                source_by_key.setdefault(hit.chunk_key, set()).add("fts")

        vector_meta: dict[str, object] = {}
        vector_rank_by_key: dict[str, int] = {}

        if self.vector_store is not None and self.embed is not None:
            vector_hits = self.vector_store.search(self.embed(query), top_k=top_k * 3)
            vector_keys = [hit.chunk_key for hit in vector_hits]
            vector_meta.update({hit.chunk_key: hit for hit in vector_hits})
            vector_rank_by_key = {key: rank for rank, key in enumerate(vector_keys)}

            if vector_keys:
                ranked.append(vector_keys)

                for hit in vector_hits:
                    source_by_key.setdefault(hit.chunk_key, set()).add("vector")

        exact_keys = self._exact_keys(query)

        if exact_keys:
            ranked.append(exact_keys)

            for key in exact_keys:
                source_by_key.setdefault(key, set()).add("exact")

        symbols_by_key = {
            symbol.stable_key: symbol for symbol in self.symbol_index.symbols()
        }
        fused = reciprocal_rank_fusion(ranked)

        candidates: list[HybridCandidate] = []

        for key, score in sorted(fused.items(), key=lambda item: item[1], reverse=True):
            candidate = self._candidate_from_key(
                key,
                symbols_by_key,
                fts_meta,
                vector_meta,
                score,
                tuple(sorted(source_by_key.get(key, set()))),
                fts_rank_by_key,
                vector_rank_by_key,
            )

            if candidate is None:
                continue

            candidates.append(candidate)

        seed = self._detect_seed(query)
        preference = detect_preference(query)

        expanded = self._expand_graph(candidates, symbols_by_key, seed=seed)

        reranked = rerank_candidates(
            [*candidates, *expanded],
            query,
            graph=self.graph,
            symbols_by_key=symbols_by_key,
            seed=seed,
            preference=preference,
            basename_token_df=self.basename_token_df,
            total_docs=self.total_docs,
        )

        return HybridRetrieval(
            strategy="hybrid",
            query=query,
            candidates=_select_with_per_file_cap(reranked, top_k, per_file_cap),
        )

    def _detect_seed(self, query: str) -> Symbol | None:
        for token in TOKEN_PATTERN.findall(query):
            symbols = self.symbol_index.lookup_by_name(token)

            if len({symbol.symbol_id for symbol in symbols}) == 1:
                return symbols[0]

        return None

    def _exact_keys(self, query: str) -> list[str]:
        keys: list[str] = []
        seen: set[str] = set()

        for token in TOKEN_PATTERN.findall(query):
            for symbol in self.symbol_index.lookup_by_name(token):
                if symbol.stable_key not in seen:
                    seen.add(symbol.stable_key)
                    keys.append(symbol.stable_key)

        return keys

    def _candidate_from_key(
        self,
        key: str,
        symbols_by_key: dict[str, Symbol],
        fts_meta: dict[str, FtsHit],
        vector_meta: dict[str, object],
        score: float,
        sources: tuple[str, ...],
        fts_rank_by_key: dict[str, int],
        vector_rank_by_key: dict[str, int],
    ) -> HybridCandidate | None:
        symbol = symbols_by_key.get(key)
        fts_rank = fts_rank_by_key.get(key)
        vector_rank = vector_rank_by_key.get(key)

        if symbol is not None:
            return self._from_symbol(
                symbol,
                sources=sources,
                score=score,
                fts_rank=fts_rank,
                vector_rank=vector_rank,
            )

        hit = fts_meta.get(key) or vector_meta.get(key)

        if hit is not None:
            return HybridCandidate(
                chunk_key=key,
                symbol_id="",
                symbol_name=getattr(hit, "symbol_name", ""),
                qualified_name=getattr(hit, "qualified_name", ""),
                relative_path=getattr(hit, "relative_path", ""),
                symbol_kind="",
                score=score,
                sources=sources,
                fts_rank=fts_rank,
                vector_rank=vector_rank,
            )

        return None

    def _expand_graph(
        self,
        candidates: list[HybridCandidate],
        symbols_by_key: dict[str, Symbol],
        seed: Symbol | None = None,
    ) -> list[HybridCandidate]:
        if seed is None:
            if not candidates:
                return []

            seed = symbols_by_key.get(candidates[0].chunk_key)

            if seed is None:
                return []

        in_results = {candidate.chunk_key for candidate in candidates}
        expanded: list[HybridCandidate] = []

        hits = expand_neighborhood(seed, graph=self.graph)

        for hit in hits:
            if hit.symbol.stable_key in in_results:
                continue

            expanded.append(self._from_symbol(hit.symbol, sources=("graph",)))
            in_results.add(hit.symbol.stable_key)

        return expanded

    def _from_symbol(
        self,
        symbol: Symbol,
        *,
        sources: tuple[str, ...],
        score: float = 0.0,
        fts_rank: int | None = None,
        vector_rank: int | None = None,
    ) -> HybridCandidate:
        return HybridCandidate(
            chunk_key=symbol.stable_key,
            symbol_id=symbol.symbol_id,
            symbol_name=symbol.name,
            qualified_name=symbol.qualified_name,
            relative_path=symbol.relative_path,
            symbol_kind=symbol.kind.value,
            score=score,
            sources=sources,
            fts_rank=fts_rank,
            vector_rank=vector_rank,
        )
