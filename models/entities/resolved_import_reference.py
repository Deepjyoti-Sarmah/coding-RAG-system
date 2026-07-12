from dataclasses import dataclass

from models.entities.documents import Document
from models.entities.import_references import ImportReference


@dataclass(slots=True)
class ResolvedImportReference:
    import_reference: ImportReference

    target_document: Document
