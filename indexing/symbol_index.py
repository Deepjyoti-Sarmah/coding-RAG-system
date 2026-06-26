from collections import defaultdict

from models.symbol import Symbol


class SymbolIndex:
    def __init__(self):
        self.by_name: dict[str, list[Symbol]] = defaultdict(list)

    def add(self, symbol: Symbol):
        self.by_name[symbol.name].append(symbol)

    def add_many(self, symbols: list[Symbol]):
        for symbol in symbols:
            self.add(symbol)

    def lookup(self, name: str) -> list[Symbol]:
        return self.by_name.get(name, [])
