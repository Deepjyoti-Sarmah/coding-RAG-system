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


def _variable_signature(node: Node) -> str:
    type_annotation = node.child_by_field_name("type")

    if type_annotation is not None:
        return f"variable:{_annotation_text(type_annotation)}"

    value = node.child_by_field_name("value")

    if value is not None:
        return f"variable:<{value.type}>"

    return "variable"
