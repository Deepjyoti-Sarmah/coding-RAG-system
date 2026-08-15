from analysis.semantic.member_resolver import resolve_member_reference
from analysis.semantic.name_resolver import resolve_symbol
from models.build_result import BuildResult
from models.indexing_context import IndexingContext


def run_reference_resolver_pass(
    *,
    context: IndexingContext,
    result: BuildResult,
):
    for reference in result.references:
        if len(reference.path) > 1:
            resolved = resolve_member_reference(
                reference=reference,
                symbol_index=context.symbol_index,
                export_index=context.export_index,
                resolved_import_references=result.resolved_import_references,
            )
        else:
            resolved = resolve_symbol(
                reference=reference,
                symbol_index=context.symbol_index,
                resolved_import_references=result.resolved_import_references,
            )

        result.resolved_references.append(resolved)
