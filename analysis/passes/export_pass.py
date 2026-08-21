from analysis.build_result import BuildResult
from analysis.export_extractor import extract_exports
from analysis.indexing_context import IndexingContext


def run_export_pass(
    *,
    context: IndexingContext,
    result: BuildResult,
):
    for parsed in context.parsed_documents:
        exports = extract_exports(
            tree=parsed.tree,
            document=parsed.document,
        )

        result.exports.extend(exports)

        context.export_index.add_many(exports)
