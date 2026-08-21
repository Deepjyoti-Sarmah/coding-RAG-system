from analysis.build_result import BuildResult
from analysis.indexing_context import IndexingContext
from analysis.reference_extractor import extract_references


def run_reference_pass(
    *,
    context: IndexingContext,
    result: BuildResult,
):
    for extracted in context.extracted_symbols:
        references = extract_references(
            owner_symbol=extracted.symbol, owner_node=extracted.node
        )

        result.references.extend(references)
