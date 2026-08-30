from tree_sitter import Node

from models.entities.symbol_kind import SymbolKind
from parsing.node_text import node_text

_CALLABLE_KINDS = {
    SymbolKind.FUNCTION,
    SymbolKind.METHOD,
}


def extract_signature(
    *,
    node: Node,
    kind: SymbolKind,
) -> str:
    if kind in _CALLABLE_KINDS:
        return _callable_signature(node=node, kind=kind)

    if kind == SymbolKind.CLASS:
        return _class_signature(node=node)

    if kind == SymbolKind.VARIABLE:
        return _variable_signature(node=node)

    if kind == SymbolKind.INTERFACE:
        return _interface_signature(node=node)

    if kind == SymbolKind.TYPE_ALIAS:
        return _type_alias_signature(node=node)

    return kind.value


def _callable_signature(
    *,
    node: Node,
    kind: SymbolKind,
) -> str:
    parameters = node.child_by_field_name("parameters")

    parameter_types: list[str] = []

    if parameters is not None:
        for child in parameters.children:
            if child.type not in (
                "required_parameter",
                "optional_parameter",
                "formal_parameter",
            ):
                continue

            parameter_types.append(_parameter_type(child))

    parts = [f"{kind.value}({','.join(parameter_types)})"]

    # TypeScript/JS use a `return_type` field; Java's method return type
    # lives on the `type` field instead (there is no `return_type`).
    return_type = node.child_by_field_name(
        "return_type"
    ) or node.child_by_field_name("type")

    if return_type is not None:
        parts.append(_annotation_text(return_type))

    return "".join(parts)


def _parameter_type(parameter: Node) -> str:
    type_annotation = parameter.child_by_field_name("type")

    if type_annotation is None:
        return ""

    return _annotation_text(type_annotation)


def _annotation_text(type_annotation: Node) -> str:
    return node_text(type_annotation).lstrip(":").strip()


def _class_signature(node: Node) -> str:
    # Java expresses extends/implements as direct children (`superclass`,
    # `super_interfaces`); TS nests them under a `class_heritage` node.
    heritage = next(
        (
            child
            for child in node.children
            if child.type == "class_heritage"
        ),
        None,
    )

    # Java has no `class_heritage` wrapper: `extends`/`implements` are
    # direct `superclass`/`super_interfaces` children of the class node.
    if heritage is None and any(
        child.type in ("superclass", "super_interfaces")
        for child in node.children
    ):
        return _java_class_signature(node)

    if heritage is None:
        return "class"

    extends_clause = next(
        (
            child
            for child in heritage.children
            if child.type == "extends_clause"
        ),
        None,
    )

    if extends_clause is None:
        return "class"

    extends_text = node_text(extends_clause).replace(
        "extends", ""
    ).strip()

    return f"class:{extends_text}"


def _java_class_signature(node: Node) -> str:
    superclass = next(
        (child for child in node.children if child.type == "superclass"),
        None,
    )
    super_interfaces = next(
        (child for child in node.children if child.type == "super_interfaces"),
        None,
    )

    parts: list[str] = []

    if superclass is not None:
        parts.append(node_text(superclass).replace("extends", "").strip())

    if super_interfaces is not None:
        parts.append(node_text(super_interfaces).replace("implements", "").strip())

    if not parts:
        return "class"

    return f"class:{','.join(parts)}"


def _interface_signature(node: Node) -> str:
    # Java's `interface_declaration` uses `extends_interfaces` +
    # `method_declaration` members; TS's uses `extends_type_clause` +
    # `property_signature`/`method_signature`. Field/child-type presence
    # disambiguates without depending on the (shared) node type name.
    body = node.child_by_field_name("body")
    is_java = any(child.type == "extends_interfaces" for child in node.children) or (
        body is not None
        and any(child.type == "method_declaration" for child in body.children)
    )

    if is_java:
        return _java_interface_signature(node)

    parts = ["interface"]

    extends_text = _interface_extends_text(node)

    if extends_text:
        parts.append(f":{extends_text}")

    # Member names are part of an interface's public surface (unlike
    # parameter names), so renaming one must move the signature hash.
    parts.append(f"{{{','.join(_interface_members(node))}}}")

    return "".join(parts)


def _java_interface_signature(node: Node) -> str:
    parts = ["interface"]

    extends = next(
        (child for child in node.children if child.type == "extends_interfaces"),
        None,
    )

    if extends is not None:
        extends_text = node_text(extends).replace("extends", "").strip()
        parts.append(f":{extends_text}")

    body = node.child_by_field_name("body")
    members: list[str] = []

    if body is not None:
        for child in body.children:
            if child.type != "method_declaration":
                continue

            name = child.child_by_field_name("name")

            if name is None:
                continue

            members.append(f"{node_text(name)}:{_callable_signature(node=child, kind=SymbolKind.METHOD)}")

    parts.append(f"{{{','.join(sorted(members))}}}")

    return "".join(parts)


def _interface_extends_text(node: Node) -> str:
    heritage = next(
        (
            child
            for child in node.children
            if child.type == "extends_type_clause"
        ),
        None,
    )

    if heritage is None:
        return ""

    return ",".join(
        node_text(child)
        for child in heritage.children
        if child.type == "type_identifier"
    )


def _interface_members(node: Node) -> list[str]:
    body = node.child_by_field_name("body")

    if body is None:
        return []

    members: list[str] = []

    for child in body.children:
        if child.type not in ("property_signature", "method_signature"):
            continue

        name = child.child_by_field_name("name")

        if name is None:
            continue

        members.append(
            f"{node_text(name)}:{_member_shape(child)}"
        )

    return sorted(members)


def _member_shape(member: Node) -> str:
    if member.type == "method_signature":
        return _callable_signature(node=member, kind=SymbolKind.METHOD)

    type_annotation = member.child_by_field_name("type")

    if type_annotation is None:
        return ""

    return _annotation_text(type_annotation)


def _type_alias_signature(node: Node) -> str:
    value = node.child_by_field_name("value")

    if value is None:
        return "type"

    return f"type:{node_text(value)}"


def _variable_signature(node: Node) -> str:
    type_annotation = node.child_by_field_name("type")

    if type_annotation is not None:
        return f"variable:{_annotation_text(type_annotation)}"

    value = node.child_by_field_name("value")

    if value is not None:
        return f"variable:<{value.type}>"

    return "variable"
