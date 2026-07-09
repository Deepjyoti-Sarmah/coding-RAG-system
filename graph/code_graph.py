from collections import defaultdict

from models.relationship import Relationship
from models.symbol import Symbol


class CodeGraph:
    def __init__(self) -> None:
        self._symbols_by_id: dict[str, Symbol] = {}
        self._relationships: list[Relationship] = []
        self._outgoing: dict[str, list[Relationship]] = defaultdict(list)
        self._incoming: dict[str, list[Relationship]] = defaultdict(list)

    # TODO: refactor may call .clear() and delete all off it
    def relationships(self) -> list[Relationship]:
        return self._relationships

    def add_symbols(self, symbols: list[Symbol]):
        for symbol in symbols:
            self._symbols_by_id[symbol.symbol_id] = symbol

    def add_relationships(self, relationships: list[Relationship]):
        for relationship in relationships:
            self._relationships.append(relationship)
            self._outgoing[relationship.source_symbol_id].append(relationship)
            self._incoming[relationship.target_symbol_id].append(relationship)

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
