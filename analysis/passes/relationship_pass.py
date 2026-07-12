from analysis.relationship_builder import build_relationships
from models.build_result import BuildResult
from models.indexing_context import IndexingContext


def run_relationship_pass(
    *,
    context: IndexingContext,
    result: BuildResult,
):

    # unused for now
    _ = context

    result.relationships = build_relationships(
        resolved_references=result.resolved_references,
    )
