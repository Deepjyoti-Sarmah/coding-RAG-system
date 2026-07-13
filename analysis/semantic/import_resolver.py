from analysis.semantic.normalize_path import normalize_path
from indexing.document_index import DocumentIndex
from models.entities.documents import Document
from models.entities.import_references import ImportReference


def resolve_import(
    *,
    import_reference: ImportReference,
    importing_document: Document,
    document_index: DocumentIndex,
) -> Document | None:
    path = normalize_path(import_reference.module_path)

    return document_index.lookup_by_relative_path(path)
