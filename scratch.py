from tree_sitter import Language, Parser
from tree_sitter_typescript import language_typescript

parser = Parser(Language(language_typescript()))

source = b"""
export function createUser() {}

export const Route = createFileRoute("/login")({})
"""

tree = parser.parse(source)

print(tree.root_node)
