import posixpath

from analysis.semantic.normalize_path import resolve_module_path
from indexing.document_index import DocumentIndex
from models.entities.documents import Document
from models.entities.import_references import ImportReference


def resolve_import(
    *,
    import_reference: ImportReference,
    importing_document: Document,
    document_index: DocumentIndex,
) -> Document | None:
    importing_directory = posixpath.dirname(importing_document.relative_path)

    for candidate in resolve_module_path(
        module_path=import_reference.module_path,
        importing_directory=importing_directory,
    ):
        document = document_index.lookup_by_relative_path(candidate)

        if document is not None:
            return document

    return None
