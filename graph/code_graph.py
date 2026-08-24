from collections import defaultdict
from typing import Iterable

from models.entities.symbols import Symbol
from models.relationships.relationship_kind import RelationshipKind
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
        return self._sources_of(symbol_id, RelationshipKind.CALLS)

    def callees_of(self, symbol_id: str) -> list[Symbol]:
        return self._targets_of(symbol_id, RelationshipKind.CALLS)

    def base_types_of(self, symbol_id: str) -> list[Symbol]:
        return self._targets_of(symbol_id, RelationshipKind.EXTENDS)

    def subtypes_of(self, symbol_id: str) -> list[Symbol]:
        return self._sources_of(symbol_id, RelationshipKind.EXTENDS)

    def _sources_of(
        self,
        symbol_id: str,
        kind: RelationshipKind,
    ) -> list[Symbol]:
        return self._resolve(
            (
                relationship.source_symbol_id
                for relationship in self._incoming.get(symbol_id, [])
                if relationship.kind == kind
            )
        )

    def _targets_of(
        self,
        symbol_id: str,
        kind: RelationshipKind,
    ) -> list[Symbol]:
        return self._resolve(
            (
                relationship.target_symbol_id
                for relationship in self._outgoing.get(symbol_id, [])
                if relationship.kind == kind
            )
        )

    def _resolve(self, symbol_ids: Iterable[str]) -> list[Symbol]:
        symbols: list[Symbol] = []

        for symbol_id in symbol_ids:
            symbol = self._symbols_by_id.get(symbol_id)

            if symbol is None:
                continue

            symbols.append(symbol)

        return symbols
