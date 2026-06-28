from dataclasses import dataclass

from graph.code_graph import CodeGraph
from models import symbol


@dataclass(slots=True)
class SemanticChunk:
    chunk_id: str
    symbol_id: str
    relative_path: str
    embedding_text: str
    display_text: str


def build_semantic_chunk(symbol: symbol.Symbol, graph: CodeGraph) -> SemanticChunk:
    callee_names = get_related_names(symbols=graph.callees_of(symbol.symbol_id))
    caller_names = get_related_names(symbols=graph.callers_of(symbol.symbol_id))

    embedding_text = build_embedding_text(
        symbol=symbol,
        callee_names=callee_names,
        caller_names=caller_names,
    )

    chunk_id = build_chunk_id(symbol)

    return SemanticChunk(
        chunk_id=chunk_id,
        symbol_id=symbol.symbol_id,
        relative_path=symbol.relative_path,
        embedding_text=embedding_text,
        display_text=symbol.content,
    )


def get_related_names(symbols: list[symbol.Symbol]) -> str:

    if not symbols:
        return "none"

    names = [s.name for s in symbols]
    return ", ".join(names)


def build_embedding_text(
    symbol: symbol.Symbol, callee_names: str, caller_names: str
) -> str:
    lines = [
        f"{symbol.kind.value} {symbol.name}",
        f"file: {symbol.relative_path}",
        f"calls: {callee_names}",
        f"called by: {caller_names}",
        f"source:\n{symbol.content}",
    ]

    return "\n".join(lines)


def build_chunk_id(symbol: symbol.Symbol) -> str:
    short_symbol_id = symbol.symbol_id[:8]
    return f"{symbol.relative_path}::{symbol.name}::{short_symbol_id}"
