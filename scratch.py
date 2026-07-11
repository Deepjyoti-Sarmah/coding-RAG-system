# from tree_sitter import Language, Parser
# from tree_sitter_typescript import language_typescript

# parser = Parser(Language(language_typescript()))
# source = b"""
# export function createUser() {}

# export const Route = createFileRoute("/login")({})

# export class UserService {
#     login() {
#         return true;
#     }

#     logout() {
#         return false;
#     }
# }

# export interface User {}

# export type UserId = string

# function login() {
#     createAuth();

#     auth.createAuth();

#     auth.client.createAuth();
# }
# """

# tree = parser.parse(source)


# # def print_tree(node, indent=0):
# #     print(" " * indent + node.type)
# #
# #     for child in node.children:
# #         print_tree(child, indent + 2)
# #
# #
# root = tree.root_node


# def print_tree(node, indent=0):
#     print(" " * indent + node.type)

#     for child in node.children:
#         print_tree(child, indent + 2)


# print("Root children:")
# for child in root.children:
#     print(child.type)

# #
# # for node in tree.root_node.children:
# #     declaration = node.child_by_field_name("declaration")
# #
# #     print("\nTYPE:", declaration.type)
# #
# #     name = declaration.child_by_field_name("name")
# #
# #     print("\nDeclaration:", declaration.type)
# #     print("Name:", name)
# #
# #     if name:
# #         print(name.text.decode())
# #
# # for node in tree.root_node.children:
# #     declaration = node.child_by_field_name("declaration")
# #
# #     if declaration.type != "lexical_declaration":
# #         continue
# #
# #     print(declaration)
# #
# #     for child in declaration.children:
# #         print(
# #             child.type,
# #             child.text.decode(),
# #         )
# #
# #     variable = declaration.children[1]
# #
# #     print("\nVariable Declarator")
# #     print(variable)
# #
# #     print("\nChildren")
# #
# #     for child in variable.children:
# #         print(
# #             child.type,
# #             child.text.decode(),
# #         )
# #
# #     print("\nField name:")
# #     print(variable.child_by_field_name("name"))
# #

# print("\n=== CLASSS ===")

# for node in root.children:
#     declaration = node.child_by_field_name("declaration")

#     if declaration is None:
#         continue

#     if declaration.type != "class_declaration":
#         continue

#     if declaration.type != "function_declaration":
#         continue

#     body = declaration.child_by_field_name("body")

#     for child in body.children:
#         print_tree(child)

#     print("\nCLASS:")
#     print(declaration.type)

#     name = declaration.child_by_field_name("name")

#     print("NAME:")
#     print(name)
#     print(name.text.decode())

#     body = declaration.child_by_field_name("body")

#     print("\nBODY:")
#     print(body)

#     print("\nBODY CHILDREN:")

#     for child in body.children:
#         print(
#             child.type,
#             repr(child.text.decode()),
#         )

#         print("\nMETHODS:")

#         for child in body.children:
#             if child.type != "method_definition":
#                 continue

#             print("\nMETHOD:")
#             print(child)

#             print("\nMETHOD CHILDREN:")

#             for c in child.children:
#                 print(
#                     c.type,
#                     repr(c.text.decode()),
#                 )

#             print("\nFIELD NAME:")
#             print(child.child_by_field_name("name"))

#     for child in body.children:
#         print("\nNODE")
#         print(child.type)

#         for c in child.children:
#             print(
#                 "   ",
#                 c.type,
#                 repr(c.text.decode()),
#             )


# print("\nAST:")
# print_tree(root)


# def print_symbol_tree(symbols: list[Symbol]):
#     by_id = {s.symbol_id: s for s in symbols}

#     for symbol in symbols:
#         parent = (
#             by_id[symbol.parent_symbol_id].name if symbol.parent_symbol_id else None
#         )

#         print(f"{symbol.kind.value:10} {symbol.name:20} parent={parent}")


# print("\n=== CALL EXPRESSIONS ===")


# def walk(node):
#     if node.type == "call_expression":
#         print("\nCALL:")
#         print(node.text.decode())

#         function_node = node.child_by_field_name("function")

#         print("FUNCTION NODE:")
#         print(function_node.type)

#         for i, child in enumerate(function_node.children):
#             print(
#                 i,
#                 child.type,
#                 function_node.field_name_for_child(i),
#             )

#     for child in node.children:
#         walk(child)

# walk(tree.root_node)

from analysis.build_graph import build_graph
from analysis.reference_extractor import extract_references
from analysis.symbol_extractor import extract_symbols
from ingestion.loader import load_code_files
from parsing.registry import PARSER

documents = load_code_files("test_repo")

document = documents[0]

parser = PARSER[document.language]

tree = parser.parse(document)

symbols = extract_symbols(
    tree=tree,
    document=document,
)

print("=== REFERENCES ===\n")

for extracted in symbols:
    print(f"\nOwner: {extracted.symbol.name}")

    references = extract_references(
        owner_symbol=extracted.symbol,
        owner_node=extracted.node,
    )

    for reference in references:
        print(
            f"  {reference.name:15}"
            f"{reference.location.start_line:5}"
            f"{reference.location.start_byte:8}"
        )

build_result = build_graph("test_repo")

print("=== RESOLVED REFERENCES ===\n")

for resolved in build_result.resolved_references:
    print(
        f"{resolved.reference.name:15}"
        f" -> "
        f"{resolved.target_symbol.name:15}"
        f" ({resolved.target_symbol.kind.value})"
    )
