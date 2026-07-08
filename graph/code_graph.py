from collections import defaultdict

from models.relationship import Relationship
from models.symbol import Symbol


class CodeGraph:
    def __init__(self) -> None:
        self.symbols_by_id: dict[str, Symbol] = {}
        self.outgoing: dict[str, list[Relationship]] = defaultdict(list)
        self.incoming: dict[str, list[Relationship]] = defaultdict(list)

    def add_symbols(self, symbols: list[Symbol]):
        for symbol in symbols:
            self.symbols_by_id[symbol.symbol_id] = symbol

    def add_relationships(self, relationships: list[Relationship]):
        for relationship in relationships:
            self.outgoing[relationship.source_symbol_id].append(relationship)
            self.incoming[relationship.target_symbol_id].append(relationship)

    def callers_of(self, symbol_id: str) -> list[Symbol]:
        incomming_relationships = self.incoming.get(symbol_id, [])

        callers: list[Symbol] = []

        for relationship in incomming_relationships:
            caller_id = relationship.source_symbol_id

            caller_symbol = self.symbols_by_id.get(caller_id)

            if caller_symbol is None:
                continue

            callers.append(caller_symbol)

        return callers

    def callees_of(self, symbol_id: str) -> list[Symbol]:
        outgoing_relationships = self.outgoing.get(symbol_id, [])

        callees: list[Symbol] = []

        for relationship in outgoing_relationships:
            callees_id = relationship.target_symbol_id
            callees_symbol = self.symbols_by_id[callees_id]
            callees.append(callees_symbol)

        return callees
