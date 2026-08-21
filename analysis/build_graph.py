from analysis.pipeline import run_extraction_passes, run_resolution_passes
from chunking.symbol_chunker import build_semantic_chunks
from ingestion.loader import load_code_files
from models.build_result import BuildResult
from models.indexing_context import IndexingContext


def build_graph(root_dir: str) -> BuildResult:
    result = BuildResult()
    context = IndexingContext()

    result.documents = load_code_files(root_dir)
    context.document_index.add_many(result.documents)

    run_extraction_passes(context=context, result=result)

    result.symbol_index = context.symbol_index

    run_resolution_passes(context=context, result=result)

    result.chunks = build_semantic_chunks(result)

    return result
