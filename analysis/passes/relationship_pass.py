from analysis.relationship_builder import build_relationships
from models.build_result import BuildResult


def run_relationship_pass(
    *,
    result: BuildResult,
):
    result.relationships = build_relationships(
        resolved_references=result.resolved_references,
    )
