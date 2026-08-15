from collections import defaultdict

from models.entities.exports import Export


class ExportIndex:
    def __init__(self):
        self._by_key: dict[tuple[str, str], list[Export]] = defaultdict(list)

    def add(self, export: Export):
        self._by_key[(export.document_id, export.exported_name)].append(export)

    def add_many(self, exports: list[Export]):
        for export in exports:
            self.add(export)

    def lookup(self, document_id: str, exported_name: str) -> list[Export]:
        return self._by_key.get((document_id, exported_name), [])
