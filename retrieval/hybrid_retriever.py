import re
from dataclasses import dataclass
from typing import Literal

from chunking.symbol_chunker import SemanticChunk
from graph.code_graph import CodeGraph
from indexing.symbol_index import SymbolIndex
from indexing.vector_index import VectorIndex
from models.entities.symbol import Symbol

WHO_CALLS_PATTERN = re.compile(r"who calls\s+(\w+)", re.IGNORECASE)
WHERE_IS_DEFINED_PATTERN = re.compile(
    r"where is\s+(\w+)\s+(?:implemented|defined)", re.IGNORECASE
)

RetrievalStrategy = Literal["graph_callers", "symbol_lookup", "vector_search"]


@dataclass(slots=True)
class RetrievalResult:
    strategy: RetrievalStrategy
    results: list[Symbol] | list[tuple[SemanticChunk, float]]


class HybridRetriever:
    def __init__(
        self,
        symbol_index: SymbolIndex,
        graph: CodeGraph,
        vector_index: VectorIndex,
    ):
        self.symbol_index = symbol_index
        self.graph = graph
        self.vector_index = vector_index

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
    ) -> RetrievalResult:
        who_calls_match = WHO_CALLS_PATTERN.search(query)
        if who_calls_match:
            target_name = who_calls_match.group(1)
            return self._find_callers_of(target_name)

        where_is_match = WHERE_IS_DEFINED_PATTERN.search(query)
        if where_is_match:
            symbol_name = where_is_match.group(1)
            return self._find_symbol_definition(symbol_name)

        return self._search_by_meaning(query, top_k)

    def _find_callers_of(self, target_name: str) -> RetrievalResult:
        matching_symbols = self.symbol_index.lookup_by_name(target_name)

        all_callers: list[Symbol] = []
        for symbol in matching_symbols:
            callers_of_this_symbol = self.graph.callers_of(symbol.symbol_id)
            all_callers.extend(callers_of_this_symbol)

        return RetrievalResult(
            strategy="graph_callers",
            results=all_callers,
        )

    def _find_symbol_definition(self, symbol_name: str) -> RetrievalResult:
        matching_symbols = self.symbol_index.lookup_by_name(symbol_name)

        return RetrievalResult(
            strategy="symbol_lookup",
            results=matching_symbols,
        )

    def _search_by_meaning(self, query: str, top_k: int) -> RetrievalResult:
        ranked_chunks = self.vector_index.search(query, top_k)

        return RetrievalResult(
            strategy="vector_search",
            results=ranked_chunks,
        )
