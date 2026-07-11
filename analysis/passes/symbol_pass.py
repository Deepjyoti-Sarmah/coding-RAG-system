from tree_sitter import Tree

from analysis.symbol_extractor import extract_symbols
from models.build_result import BuildResult
from models.entities.document import Document
from models.indexing_context import IndexingContext


def run_symbol_pass(
    *,
    document: Document,
    tree: Tree,
    context: IndexingContext,
    result: BuildResult,
):
    new_symbols = extract_symbols(
        tree=tree,
        document=document,
    )

    context.extracted_symbols.extend(new_symbols)

    symbols = [extracted.symbol for extracted in new_symbols]

    result.symbols.extend(symbols)

    context.symbol_index.add_many(symbols)
