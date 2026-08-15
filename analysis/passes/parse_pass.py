import hashlib

from models.build_result import BuildResult
from models.indexing_context import IndexingContext
from models.parsed_document import ParsedDocument
from parsing.registry import PARSER


def compute_file_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def run_parse_pass(
    *,
    context: IndexingContext,
    result: BuildResult,
):
    for document in context.document_index.documents():
        parser = PARSER.get(document.language)

        if parser is None:
            continue

        tree = parser.parse(document)

        context.parsed_documents.append(
            ParsedDocument(
                document=document,
                tree=tree,
                file_hash=compute_file_hash(document.content),
                has_parse_errors=tree.root_node.has_error,
            )
        )
