from dataclasses import dataclass

from graph.code_graph import CodeGraph
from indexing.symbol_index import SymbolIndex
from models.entities.exports import Export
from models.entities.resolved_import_reference import ResolvedImportReference
from models.entities.symbols import Symbol

DEFAULT_ONE_HOP_BUDGET = 6
DEFAULT_TWO_HOP_BUDGET = 2

_RELATION_ORDER = ("caller", "callee", "parent", "import", "export")


@dataclass(slots=True)
class NeighborhoodHit:
    symbol: Symbol
    relation: str
    hop: int


def expand_neighborhood(
    seed: Symbol,
    *,
    graph: CodeGraph,
    symbol_index: SymbolIndex,
    resolved_imports: list[ResolvedImportReference] | None = None,
    exports: list[Export] | None = None,
    one_hop_budget: int = DEFAULT_ONE_HOP_BUDGET,
    two_hop_budget: int = DEFAULT_TWO_HOP_BUDGET,
) -> list[NeighborhoodHit]:
    hits: list[tuple[str, int, Symbol]] = []
    seen: set[str] = {seed.symbol_id}

    for relation, symbol in _one_hop_relations(
        seed,
        graph=graph,
        symbol_index=symbol_index,
        resolved_imports=resolved_imports,
        exports=exports,
    ):
        if symbol.symbol_id in seen:
            continue

        seen.add(symbol.symbol_id)
        hits.append((relation, 1, symbol))

    hits.sort(key=lambda item: _relation_rank(item[0]))
    hits = hits[:one_hop_budget]

    two_hop: list[tuple[str, int, Symbol]] = []

    if not graph.callers_of(seed.symbol_id) and not graph.callees_of(seed.symbol_id):
        for child in graph.children_of(seed.symbol_id):
            for callee in graph.callees_of(child.symbol_id):
                if callee.symbol_id in seen:
                    continue

                seen.add(callee.symbol_id)
                two_hop.append(("callee", 2, callee))

                if len(two_hop) >= two_hop_budget:
                    break

            if len(two_hop) >= two_hop_budget:
                break

    return [
        NeighborhoodHit(symbol=s, relation=r, hop=h) for r, h, s in [*hits, *two_hop]
    ]


def _one_hop_relations(
    seed: Symbol,
    *,
    graph: CodeGraph,
    symbol_index: SymbolIndex,
    resolved_imports: list[ResolvedImportReference] | None,
    exports: list[Export] | None,
) -> list[tuple[str, Symbol]]:
    relations: list[tuple[str, Symbol]] = []

    for caller in graph.callers_of(seed.symbol_id):
        relations.append(("caller", caller))

    for callee in graph.callees_of(seed.symbol_id):
        relations.append(("callee", callee))

    for parent in graph.parents_of(seed.symbol_id):
        relations.append(("parent", parent))

    if resolved_imports is not None:
        relations.extend(
            ("import", target)
            for resolved in resolved_imports
            if resolved.import_reference.document_id == seed.document_id
            for target in [resolved.target_symbol]
            if target is not None
        )

    if exports is not None:
        relations.extend(
            ("export", symbol)
            for export in exports
            if export.document_id == seed.document_id and export.symbol_name is not None
            for symbol in _module_symbols(
                symbol_index, seed.document_id, export.symbol_name
            )
        )

    return relations


def _module_symbols(
    symbol_index: SymbolIndex,
    document_id: str,
    name: str,
) -> list[Symbol]:
    return [
        symbol
        for symbol in symbol_index.lookup_by_name(name)
        if symbol.document_id == document_id and symbol.parent_symbol_id is None
    ]


def _relation_rank(relation: str) -> int:
    return _RELATION_ORDER.index(relation)
