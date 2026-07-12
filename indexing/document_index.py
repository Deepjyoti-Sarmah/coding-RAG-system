from models.entities.documents import Document


class DocumentIndex:
    def __init__(self) -> None:
        self._by_id: dict[str, Document] = {}

    def add(self, document: Document):
        self._by_id[document.document_id] = document

    def add_many(self, documents: list[Document]):
        for document in documents:
            self.add(document)

    def loookup_by_id(self, document_id: str) -> Document | None:
        return self._by_id.get(document_id)

    def documents(self) -> list[Document]:
        return list(self._by_id.values())
