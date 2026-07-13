from analysis.import_resolution_builder import build_resolved_import
from analysis.semantic.import_resolver import resolve_import
from models.build_result import BuildResult
from models.indexing_context import IndexingContext


def run_import_resolver_pass(
    *,
    context: IndexingContext,
    result: BuildResult,
):

    for import_reference in result.import_references:
        document = resolve_import(
            import_reference=import_reference,
            document_index=context.document_index,
        )

        if document is None:
            continue

        result.resolved_import_references.append(
            build_resolved_import(
                import_reference=import_reference,
                target_document=document,
            )
        )
