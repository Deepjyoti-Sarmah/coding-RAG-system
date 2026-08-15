from dataclasses import dataclass

from models.entities.documents import Document
from models.entities.import_references import ImportReference
from models.entities.symbols import Symbol


@dataclass(slots=True)
class ResolvedImportReference:
    import_reference: ImportReference

    target_document: Document

    target_symbol: Symbol | None = None
