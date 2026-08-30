import posixpath

from analysis.languages import profile_for
from analysis.semantic.namespace_index import NamespaceIndex
from analysis.semantic.normalize_path import resolve_module_path
from indexing.document_index import DocumentIndex
from models.entities.documents import Document
from models.entities.import_references import ImportReference


def resolve_import(
    *,
    import_reference: ImportReference,
    importing_document: Document,
    document_index: DocumentIndex,
    namespace_index: NamespaceIndex | None = None,
) -> Document | list[Document] | None:
    """Resolve path imports singly and namespace imports as document lists.

    Most languages import a single file, guessable from the module
    path (`resolve_module_path`), so the legacy path strategy returns one
    document (or ``None``).
    Namespace-indexed languages (C#) are different: an import names a
    namespace that any number of files may declare types in, so every
    document known to declare it is a legitimate candidate -- there is
    no "best" one to pick over the others, only the full set.
    """
    profile = profile_for(importing_document.language)

    if profile is not None and profile.namespace_nodes:
        if namespace_index is None:
            return []

        documents = (
            document_index.lookup_by_id(document_id)
            for document_id in namespace_index.document_ids_for(
                import_reference.module_path
            )
        )

        return [document for document in documents if document is not None]

    importing_directory = posixpath.dirname(importing_document.relative_path)

    for candidate in resolve_module_path(
        module_path=import_reference.module_path,
        importing_directory=importing_directory,
        language=importing_document.language,
    ):
        document = document_index.lookup_by_relative_path(candidate)

        if document is not None:
            return document

    return None
