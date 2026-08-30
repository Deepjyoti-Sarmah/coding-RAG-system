from tree_sitter import Language
from tree_sitter_c_sharp import language as language_csharp
from tree_sitter_go import language as language_go
from tree_sitter_java import language as language_java
from tree_sitter_python import language as language_python
from tree_sitter_rust import language as language_rust
from tree_sitter_typescript import (
    language_tsx,
    language_typescript,
)

from parsing.base_parser import BaseParser
from parsing.tree_sitter_parser import TreeSitterParser

PARSER: dict[str, BaseParser] = {
    "typescript": TreeSitterParser(
        Language(language_typescript()),
    ),
    "tsx": TreeSitterParser(
        Language(language_tsx()),
    ),
    "javascript": TreeSitterParser(
        Language(language_typescript()),
    ),
    "jsx": TreeSitterParser(
        Language(language_tsx()),
    ),
    "python": TreeSitterParser(
        Language(language_python()),
    ),
    "go": TreeSitterParser(
        Language(language_go()),
    ),
    "java": TreeSitterParser(
        Language(language_java()),
    ),
    "rust": TreeSitterParser(
        Language(language_rust()),
    ),
    "csharp": TreeSitterParser(
        Language(language_csharp()),
    ),
}
