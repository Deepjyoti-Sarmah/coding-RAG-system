from models.entities.documents import Document
from models.entities.import_references import ImportReference
from models.entities.resolved_import_reference import ResolvedImportReference


def build_resolved_import(
    *,
    import_reference: ImportReference,
    target_document: Document,
) -> ResolvedImportReference:

    return ResolvedImportReference(
        import_reference=import_reference,
        target_document=target_document,
    )
