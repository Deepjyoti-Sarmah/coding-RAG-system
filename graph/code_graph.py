from collections import defaultdict

from models.entities.symbols import Symbol
from models.relationships.relationships import Relationship


class CodeGraph:
    def __init__(self) -> None:
        self._symbols_by_id: dict[str, Symbol] = {}
        self._children_by_parent: dict[str | None, list[Symbol]] = defaultdict(list)
        self._relationships: list[Relationship] = []
        self._relationship_keys: set[tuple[str, str, object]] = set()
        self._outgoing: dict[str, list[Relationship]] = defaultdict(list)
        self._incoming: dict[str, list[Relationship]] = defaultdict(list)

    def symbols(self) -> tuple[Symbol, ...]:
        return tuple(self._symbols_by_id.values())

    def relationships(self) -> tuple[Relationship, ...]:
        return tuple(self._relationships)

    def add_symbols(self, symbols: list[Symbol]):
        for symbol in symbols:
            self._symbols_by_id[symbol.symbol_id] = symbol
            self._children_by_parent[symbol.parent_symbol_id].append(symbol)

    def add_relationships(self, relationships: list[Relationship]):
        for relationship in relationships:
            if relationship.key in self._relationship_keys:
                continue

            self._relationship_keys.add(relationship.key)
            self._relationships.append(relationship)
            self._outgoing[relationship.source_symbol_id].append(relationship)
            self._incoming[relationship.target_symbol_id].append(relationship)

    def children_of(self, symbol_id: str) -> list[Symbol]:
        return list(self._children_by_parent.get(symbol_id, []))

    def parents_of(self, symbol_id: str) -> list[Symbol]:
        symbol = self._symbols_by_id.get(symbol_id)

        if symbol is None or symbol.parent_symbol_id is None:
            return []

        parent = self._symbols_by_id.get(symbol.parent_symbol_id)

        return [parent] if parent is not None else []

    def callers_of(self, symbol_id: str) -> list[Symbol]:
        incoming_relationships = self._incoming.get(symbol_id, [])

        callers: list[Symbol] = []

        for relationship in incoming_relationships:
            caller_id = relationship.source_symbol_id

            caller_symbol = self._symbols_by_id.get(caller_id)

            if caller_symbol is None:
                continue

            callers.append(caller_symbol)

        return callers

    def callees_of(self, symbol_id: str) -> list[Symbol]:
        outgoing_relationships = self._outgoing.get(symbol_id, [])

        callees: list[Symbol] = []

        for relationship in outgoing_relationships:
            callees_id = relationship.target_symbol_id
            callees_symbol = self._symbols_by_id.get(callees_id)

            if callees_symbol is None:
                continue

            callees.append(callees_symbol)

        return callees
