from analysis.import_extractor import extract_imports
from models.build_result import BuildResult
from models.indexing_context import IndexingContext


def run_import_pass(
    *,
    context: IndexingContext,
    result: BuildResult,
):
    for parsed in context.parsed_documents:
        imports = extract_imports(
            tree=parsed.tree,
            document=parsed.document,
        )

        result.import_references.extend(imports)
