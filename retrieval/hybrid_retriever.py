import re
from dataclasses import dataclass
from typing import Callable

import numpy as np

from graph.code_graph import CodeGraph
from indexing.symbol_index import SymbolIndex
from models.entities.exports import Export
from models.entities.fts_hit import FtsHit
from models.entities.resolved_import_reference import ResolvedImportReference
from models.entities.symbols import Symbol
from retrieval.candidate import HybridCandidate
from retrieval.neighborhood import expand_neighborhood
from retrieval.ranking import reciprocal_rank_fusion
from retrieval.reranker import detect_preference, rerank_candidates
from retrieval.vector_store import VectorStore

WHO_CALLS_PATTERN = re.compile(
    r"who calls\s+([A-Za-z_]\w*)", re.IGNORECASE
)
WHAT_CALLS_PATTERN = re.compile(
    r"what does\s+([A-Za-z_]\w*)\s+call", re.IGNORECASE
)
WHERE_IS_PATTERN = re.compile(
    r"where is\s+([A-Za-z_]\w*)\s+(?:defined|implemented)", re.IGNORECASE
)

TOKEN_PATTERN = re.compile(r"[A-Za-z_]\w*")

FtsSearch = Callable[[str, int], list[FtsHit]]
Embed = Callable[[str], np.ndarray]


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
        resolved_imports: list[ResolvedImportReference] | None = None,
        exports: list[Export] | None = None,
    ) -> None:
        self.symbol_index = symbol_index
        self.graph = graph
        self.fts_search = fts_search
        self.vector_store = vector_store
        self.embed = embed
        self.resolved_imports = resolved_imports
        self.exports = exports

    def retrieve(self, query: str, top_k: int = 5) -> HybridRetrieval:
        who_calls = WHO_CALLS_PATTERN.search(query)
        if who_calls:
            return self._graph_callers(who_calls.group(1))

        what_calls = WHAT_CALLS_PATTERN.search(query)
        if what_calls:
            return self._graph_callees(what_calls.group(1))

        where_is = WHERE_IS_PATTERN.search(query)
        if where_is:
            return self._exact_definition(where_is.group(1))

        return self._hybrid_search(query, top_k)

    def _graph_callers(self, target_name: str) -> HybridRetrieval:
        candidates: list[HybridCandidate] = []

        for symbol in self.symbol_index.lookup_by_name(target_name):
            for caller in self.graph.callers_of(symbol.symbol_id):
                candidates.append(self._from_symbol(caller, sources=("graph",)))

        return HybridRetrieval(strategy="graph_callers", query=target_name, candidates=candidates)

    def _graph_callees(self, target_name: str) -> HybridRetrieval:
        candidates: list[HybridCandidate] = []

        for symbol in self.symbol_index.lookup_by_name(target_name):
            for callee in self.graph.callees_of(symbol.symbol_id):
                candidates.append(self._from_symbol(callee, sources=("graph",)))

        return HybridRetrieval(strategy="graph_callees", query=target_name, candidates=candidates)

    def _exact_definition(self, symbol_name: str) -> HybridRetrieval:
        candidates = [
            self._from_symbol(symbol, sources=("exact",))
            for symbol in self.symbol_index.lookup_by_name(symbol_name)
        ]

        return HybridRetrieval(strategy="exact_symbol", query=symbol_name, candidates=candidates)

    def _hybrid_search(self, query: str, top_k: int) -> HybridRetrieval:
        ranked: list[list[str]] = []
        source_by_key: dict[str, set[str]] = {}

        fts_hits = self.fts_search(query, top_k * 3)
        fts_meta = {hit.chunk_key: hit for hit in fts_hits}

        if fts_hits:
            ranked.append([hit.chunk_key for hit in fts_hits])

            for hit in fts_hits:
                source_by_key.setdefault(hit.chunk_key, set()).add("fts")

        vector_meta: dict[str, object] = {}

        if self.vector_store is not None and self.embed is not None:
            vector_hits = self.vector_store.search(self.embed(query), top_k=top_k * 3)
            vector_keys = [hit.chunk_key for hit in vector_hits]
            vector_meta.update({hit.chunk_key: hit for hit in vector_hits})

            if vector_keys:
                ranked.append(vector_keys)

                for hit in vector_hits:
                    source_by_key.setdefault(hit.chunk_key, set()).add("vector")

        exact_keys = self._exact_keys(query)

        if exact_keys:
            ranked.append(exact_keys)

            for key in exact_keys:
                source_by_key.setdefault(key, set()).add("exact")

        symbols_by_key = {symbol.stable_key: symbol for symbol in self.symbol_index.symbols()}
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
            )

            if candidate is None:
                continue

            candidates.append(candidate)

        seed = self._detect_seed(query)
        preference = detect_preference(query)

        expanded = self._expand_graph(candidates, symbols_by_key, seed=seed)

        ranked = rerank_candidates(
            [*candidates, *expanded],
            query,
            graph=self.graph,
            symbols_by_key=symbols_by_key,
            seed=seed,
            preference=preference,
        )

        return HybridRetrieval(
            strategy="hybrid",
            query=query,
            candidates=ranked[:top_k],
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
    ) -> HybridCandidate | None:
        symbol = symbols_by_key.get(key)

        if symbol is not None:
            return self._from_symbol(symbol, sources=sources, score=score)

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

        hits = expand_neighborhood(
            seed,
            graph=self.graph,
            symbol_index=self.symbol_index,
            resolved_imports=self.resolved_imports,
            exports=self.exports,
        )

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
        )