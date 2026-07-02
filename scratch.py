from tree_sitter import Language, Parser
from tree_sitter_typescript import language_typescript

parser = Parser(Language(language_typescript()))
source = b"""
export function createUser() {}

export const Route = createFileRoute("/login")({})

export class UserService {
    login() {
        return true;
    }

    logout() {
        return false;
    }
}

export interface User {}

export type UserId = string
"""

tree = parser.parse(source)


# def print_tree(node, indent=0):
#     print(" " * indent + node.type)
#
#     for child in node.children:
#         print_tree(child, indent + 2)
#
#
root = tree.root_node
#
print("Root children:")
for child in root.children:
    print(child.type)
#
# for node in tree.root_node.children:
#     declaration = node.child_by_field_name("declaration")
#
#     print("\nTYPE:", declaration.type)
#
#     name = declaration.child_by_field_name("name")
#
#     print("\nDeclaration:", declaration.type)
#     print("Name:", name)
#
#     if name:
#         print(name.text.decode())
#
# for node in tree.root_node.children:
#     declaration = node.child_by_field_name("declaration")
#
#     if declaration.type != "lexical_declaration":
#         continue
#
#     print(declaration)
#
#     for child in declaration.children:
#         print(
#             child.type,
#             child.text.decode(),
#         )
#
#     variable = declaration.children[1]
#
#     print("\nVariable Declarator")
#     print(variable)
#
#     print("\nChildren")
#
#     for child in variable.children:
#         print(
#             child.type,
#             child.text.decode(),
#         )
#
#     print("\nField name:")
#     print(variable.child_by_field_name("name"))
#

print("\n=== CLASSS ===")

for node in root.children:
    declaration = node.child_by_field_name("declaration")

    if declaration is None:
        continue

    if declaration.type != "class_declaration":
        continue

    print("\nCLASS:")
    print(declaration.type)

    name = declaration.child_by_field_name("name")

    print("NAME:")
    print(name)
    print(name.text.decode())

    body = declaration.child_by_field_name("body")

    print("\nBODY:")
    print(body)

    print("\nBODY CHILDREN:")

    for child in body.children:
        print(
            child.type,
            repr(child.text.decode()),
        )

        print("\nMETHODS:")

        for child in body.children:
            if child.type != "method_definition":
                continue

            print("\nMETHOD:")
            print(child)

            print("\nMETHOD CHILDREN:")

            for c in child.children:
                print(
                    c.type,
                    repr(c.text.decode()),
                )

            print("\nFIELD NAME:")
            print(child.child_by_field_name("name"))

    for child in body.children:
        print("\nNODE")
        print(child.type)

        for c in child.children:
            print(
                "   ",
                c.type,
                repr(c.text.decode()),
            )


# print("\nAST:")
# print_tree(root)
