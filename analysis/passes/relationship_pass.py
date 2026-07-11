from analysis.relationship_extractor import extract_relationship
from models.build_result import BuildResult
from models.indexing_context import IndexingContext


def run_relationship_pass(
    *,
    context: IndexingContext,
    result: BuildResult,
):
    for extracted in context.extracted_symbols:
        relationships = extract_relationship(
            symbol=extracted.symbol,
            symbol_node=extracted.node,
            symbol_index=context.symbol_index,
        )

        result.relationships.extend(relationships)
