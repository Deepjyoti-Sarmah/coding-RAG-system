from dataclasses import dataclass

from tree_sitter import Tree

from models.entities.documents import Document


@dataclass(slots=True)
class ParsedDocument:
    document: Document
    tree: Tree
    file_hash: str
    has_parse_errors: bool = False
