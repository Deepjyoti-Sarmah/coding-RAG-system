from tree_sitter import Node

from models.entities.symbol_kind import SymbolKind

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
            ):
                continue

            parameter_types.append(_parameter_type(child))

    parts = [f"{kind.value}({','.join(parameter_types)})"]

    return_type = node.child_by_field_name("return_type")

    if return_type is not None:
        parts.append(_annotation_text(return_type))

    return "".join(parts)


def _parameter_type(parameter: Node) -> str:
    type_annotation = parameter.child_by_field_name("type")

    if type_annotation is None:
        return ""

    return _annotation_text(type_annotation)


def _annotation_text(type_annotation: Node) -> str:
    return type_annotation.text.decode("utf-8").lstrip(":").strip()


def _class_signature(node: Node) -> str:
    heritage = next(
        (
            child
            for child in node.children
            if child.type == "class_heritage"
        ),
        None,
    )

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

    extends_text = extends_clause.text.decode("utf-8").replace(
        "extends", ""
    ).strip()

    return f"class:{extends_text}"


def _interface_signature(node: Node) -> str:
    parts = ["interface"]

    extends_text = _interface_extends_text(node)

    if extends_text:
        parts.append(f":{extends_text}")

    # Member names are part of an interface's public surface (unlike
    # parameter names), so renaming one must move the signature hash.
    parts.append(f"{{{','.join(_interface_members(node))}}}")

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
        child.text.decode("utf-8")
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
            f"{name.text.decode('utf-8')}:{_member_shape(child)}"
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

    return f"type:{value.text.decode('utf-8')}"


def _variable_signature(node: Node) -> str:
    type_annotation = node.child_by_field_name("type")

    if type_annotation is not None:
        return f"variable:{_annotation_text(type_annotation)}"

    value = node.child_by_field_name("value")

    if value is not None:
        return f"variable:<{value.type}>"

    return "variable"
