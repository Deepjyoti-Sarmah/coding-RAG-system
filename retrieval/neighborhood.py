from dataclasses import dataclass

from graph.code_graph import CodeGraph
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
    one_hop_budget: int = DEFAULT_ONE_HOP_BUDGET,
    two_hop_budget: int = DEFAULT_TWO_HOP_BUDGET,
) -> list[NeighborhoodHit]:
    hits: list[tuple[str, int, Symbol]] = []
    seen: set[str] = {seed.symbol_id}

    for relation, symbol in _one_hop_relations(seed, graph=graph):
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
) -> list[tuple[str, Symbol]]:
    relations: list[tuple[str, Symbol]] = []

    for caller in graph.callers_of(seed.symbol_id):
        relations.append(("caller", caller))

    for callee in graph.callees_of(seed.symbol_id):
        relations.append(("callee", callee))

    for parent in graph.parents_of(seed.symbol_id):
        relations.append(("parent", parent))

    for target in graph.imports_of_document(seed.document_id):
        relations.append(("import", target))

    for symbol in graph.exports_of_document(seed.document_id):
        relations.append(("export", symbol))

    return relations


def _relation_rank(relation: str) -> int:
    return _RELATION_ORDER.index(relation)
