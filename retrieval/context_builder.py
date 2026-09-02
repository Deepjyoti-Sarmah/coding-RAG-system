from dataclasses import dataclass

from graph.code_graph import CodeGraph
from models.entities.symbols import Symbol
from retrieval.candidate import HybridCandidate
from retrieval.tokenizer import count_tokens

ROLE_PRIMARY = "primary"
ROLE_SUPPORTING = "supporting"


def estimate_tokens(text: str) -> int:
    return count_tokens(text)


@dataclass(slots=True)
class ContextEntry:
    chunk_key: str
    symbol_id: str
    qualified_name: str
    symbol_kind: str
    relative_path: str
    location: str
    role: str
    source: str


@dataclass(slots=True)
class ContextPack:
    query: str
    token_budget: int
    total_tokens: int
    primary_definitions: list[ContextEntry]
    supporting_definitions: list[ContextEntry]
    relationships: tuple[str, ...]
    file_paths: tuple[str, ...]
    baseline_tokens: int = 0


def build_context_pack(
    candidates: list[HybridCandidate],
    *,
    query: str,
    graph: CodeGraph,
    symbols_by_key: dict[str, Symbol],
    token_budget: int,
    baseline_tokens: int = 0,
) -> ContextPack:
    primaries: list[ContextEntry] = []
    supporting: list[ContextEntry] = []
    used = 0
    seen: set[str] = set()

    role_ordered = _role_ordered(candidates, symbols_by_key)

    for role, symbol in role_ordered:
        if symbol.stable_key in seen:
            continue

        seen.add(symbol.stable_key)

        entry, cost = _budget_entry(symbol, role, token_budget - used)

        if entry is None:
            continue

        primaries.append(entry) if role == ROLE_PRIMARY else supporting.append(entry)
        used += cost

    relationships = _selected_relationships(
        [*primaries, *supporting],
        symbols_by_key,
        graph,
    )

    relationship_tokens = sum(estimate_tokens(relationship) for relationship in relationships)

    file_paths = tuple(
        sorted({entry.relative_path for entry in [*primaries, *supporting]})
    )

    return ContextPack(
        query=query,
        token_budget=token_budget,
        total_tokens=used + relationship_tokens,
        primary_definitions=primaries,
        supporting_definitions=supporting,
        relationships=relationships,
        file_paths=file_paths,
        baseline_tokens=baseline_tokens,
    )


def _role_ordered(
    candidates: list[HybridCandidate],
    symbols_by_key: dict[str, Symbol],
) -> list[tuple[str, Symbol]]:
    primaries: list[tuple[str, Symbol]] = []
    supporting: list[tuple[str, Symbol]] = []
    seen: set[str] = set()

    for candidate in candidates:
        symbol = symbols_by_key.get(candidate.chunk_key)

        if symbol is None or symbol.stable_key in seen:
            continue

        seen.add(symbol.stable_key)

        role = (
            ROLE_SUPPORTING
            if candidate.sources == ("graph",)
            else ROLE_PRIMARY
        )

        (supporting if role == ROLE_SUPPORTING else primaries).append((role, symbol))

    return [*primaries, *supporting]


def _budget_entry(
    symbol: Symbol,
    role: str,
    remaining: int,
) -> tuple[ContextEntry | None, int]:
    header = _header(symbol)
    header_tokens = estimate_tokens(header)

    if header_tokens > remaining:
        return None, 0

    full_source = f"{header}\n{symbol.content}"
    full_tokens = estimate_tokens(full_source)

    if full_tokens <= remaining:
        return ContextEntry(
            chunk_key=symbol.stable_key,
            symbol_id=symbol.symbol_id,
            qualified_name=symbol.qualified_name,
            symbol_kind=symbol.kind.value,
            relative_path=symbol.relative_path,
            location=f"{symbol.relative_path}:{symbol.location.start_line}",
            role=role,
            source=symbol.content,
        ), full_tokens

    return ContextEntry(
        chunk_key=symbol.stable_key,
        symbol_id=symbol.symbol_id,
        qualified_name=symbol.qualified_name,
        symbol_kind=symbol.kind.value,
        relative_path=symbol.relative_path,
        location=f"{symbol.relative_path}:{symbol.location.start_line}",
        role=role,
        source="",
    ), header_tokens


def _header(symbol: Symbol) -> str:
    return (
        f"{symbol.kind.value} {symbol.qualified_name} "
        f"— {symbol.relative_path}:{symbol.location.start_line}"
    )


def _selected_relationships(
    entries: list[ContextEntry],
    symbols_by_key: dict[str, Symbol],
    graph: CodeGraph,
) -> tuple[str, ...]:
    selected = {entry.symbol_id for entry in entries}
    names_by_id = {
        entry.symbol_id: entry.qualified_name for entry in entries
    }

    relationships: list[str] = []

    for entry in entries:
        source = symbols_by_key[entry.chunk_key]

        for edge in graph.outgoing(source.symbol_id):
            if edge.target_symbol_id not in selected:
                continue

            relationships.append(
                f"{source.qualified_name} -> "
                f"{names_by_id[edge.target_symbol_id]} ({edge.kind.value})"
            )

    return tuple(sorted(set(relationships)))
