from models.common.source_location import SourceLocation
from models.entities.documents import Document
from models.entities.import_references import ImportReference


def build_import_reference(
    *,
    document: Document,
    module_path: str,
    imported_name: str,
    local_name: str,
    location: SourceLocation,
) -> ImportReference:

    return ImportReference(
        document_id=document.document_id,
        module_path=module_path,
        imported_name=imported_name,
        local_name=local_name,
        location=location,
    )
