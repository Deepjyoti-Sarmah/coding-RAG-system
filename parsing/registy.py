from tree_sitter import Language
from tree_sitter_typescript import (
    language_typescript,
    language_tsx,
)

from parsing.tree_sitter_parser import TreeSitterParser
from parsing.typescript_parser import TypescriptParser


PARSER = {
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
}
