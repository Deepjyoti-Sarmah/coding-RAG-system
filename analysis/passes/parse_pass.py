import hashlib

from analysis.build_result import BuildResult
from analysis.indexing_context import IndexingContext
from models.entities.documents import Document
from models.parsed_document import ParsedDocument
from parsing.registry import PARSER


def compute_file_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def run_parse_pass(
    *,
    context: IndexingContext,
    result: BuildResult,
    documents: list[Document] | None = None,
):
    to_parse = (
        documents
        if documents is not None
        else context.document_index.documents()
    )

    for document in to_parse:
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
