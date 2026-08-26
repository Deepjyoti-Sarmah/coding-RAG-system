from tree_sitter import Node

from analysis.languages import LanguageProfile


def is_declaration_name(node: Node, profile: LanguageProfile) -> bool:
    parent = node.parent

    if parent is None:
        return False

    # Symbol handlers cover extracted declarations; the extra member
    # types cover interface members, which are not child symbols but
    # whose names are still declarations, not references.
    known = set(profile.symbol_handlers) | profile.declaration_member_types

    if parent.type not in known:
        return False

    name_node = parent.child_by_field_name("name")

    if name_node is None:
        return False

    return name_node == node
