from collections import defaultdict

from models.entities.symbol import Symbol


class SymbolIndex:
    def __init__(self):
        self.by_id: dict[str, Symbol] = {}
        self.by_name: dict[str, list[Symbol]] = defaultdict(list)
        self.children_by_parent: dict[str | None, list[Symbol]] = defaultdict(list)

    def symbols(self) -> list[Symbol]:
        return list(self.by_id.values())

    def add(self, symbol: Symbol):
        self.by_id[symbol.symbol_id] = symbol
        self.by_name[symbol.name].append(symbol)
        self.children_by_parent[symbol.parent_symbol_id].append(symbol)

    def add_many(self, symbols: list[Symbol]):
        for symbol in symbols:
            self.add(symbol)

    def lookup_by_name(self, name: str) -> list[Symbol]:
        return self.by_name.get(name, [])

    def lookup_by_id(self, symbol_id: str) -> Symbol | None:
        return self.by_id.get(symbol_id)

    def lookup_children(self, parent_symbol_id: str | None) -> list[Symbol]:
        return self.children_by_parent.get(parent_symbol_id, [])
