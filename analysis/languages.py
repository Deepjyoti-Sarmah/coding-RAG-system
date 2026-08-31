"""Per-language extraction profiles.

Everything downstream of extraction (models, chunking, incremental
diffing, storage, retrieval) is language-neutral. Only the tree-sitter
node types used during extraction differ per grammar, so they are
collected here instead of being hardcoded at call sites.
"""

from dataclasses import dataclass, field
from typing import Any

from analysis.export_registry import export_handlers_for
from analysis.import_registry import import_handlers_for
from analysis.registry import TYPESCRIPT_FAMILY, symbol_handlers_for


@dataclass(frozen=True, slots=True)
class LanguageProfile:
    """Node-type vocabulary of one language's tree-sitter grammar."""

    language: str

    # Extraction handler tables, keyed by node type.
    symbol_handlers: dict[str, Any] = field(default_factory=dict)
    import_handlers: dict[str, Any] = field(default_factory=dict)
    export_handlers: dict[str, Any] = field(default_factory=dict)

    # Reference extraction.
    member_node: str = "member_expression"
    member_object_field: str = "object"
    member_property_field: str = "property"
    identifier_nodes: frozenset[str] = frozenset({"identifier", "property_identifier"})
    # Extracted only inside heritage clauses; type positions elsewhere
    # would flood the resolver with unresolvable references.
    heritage_only_nodes: frozenset[str] = frozenset({"type_identifier"})
    extends_parents: frozenset[str] = frozenset(
        {"extends_clause", "extends_type_clause"}
    )
    implements_parents: frozenset[str] = frozenset({"implements_clause"})
    call_parent: str = "call_expression"
    call_function_field: str = "function"

    # Names whose parent declares them (interface members etc.) are
    # declarations, not references.
    declaration_member_types: frozenset[str] = frozenset(
        {"property_signature", "method_signature"}
    )

    # Python expresses base classes via a named field on the class node
    # (`class Service(Base)` -> superclasses argument list) instead of an
    # extends-clause parent. When set, identifiers reached through this
    # field chain count as EXTENDS references.
    superclass_field: str | None = None

    # Rust's `impl Trait for Type` is a standalone top-level node, not
    # nested inside either symbol's own node, so the generic reference
    # walker (which only visits inside an already-extracted symbol's
    # node) never sees it. When set, a dedicated pass walks the raw tree
    # for this node type and emits an IMPLEMENTS reference from the
    # `impl_type_field` symbol to the `impl_trait_field` name.
    impl_node: str | None = None
    impl_trait_field: str | None = None
    impl_type_field: str | None = None

    # C#'s `using Ns;` names a namespace, not a file: any number of
    # files may declare types in it, so import resolution for these
    # languages consults `NamespaceIndex` instead of guessing paths
    # (see `analysis.semantic.import_resolver`). Non-empty only for
    # namespace-indexed languages.
    namespace_nodes: frozenset[str] = frozenset()
    namespace_name_field: str = "name"


_PROFILES: dict[str, LanguageProfile] = {
    language: LanguageProfile(
        language=language,
        symbol_handlers=symbol_handlers_for(language),
        import_handlers=import_handlers_for(language),
        export_handlers=export_handlers_for(language),
    )
    for language in TYPESCRIPT_FAMILY
}

_PROFILES["python"] = LanguageProfile(
    language="python",
    symbol_handlers=symbol_handlers_for("python"),
    import_handlers=import_handlers_for("python"),
    export_handlers=export_handlers_for("python"),
    member_node="attribute",
    member_object_field="object",
    member_property_field="attribute",
    identifier_nodes=frozenset({"identifier"}),
    heritage_only_nodes=frozenset(),
    extends_parents=frozenset(),
    implements_parents=frozenset(),
    call_parent="call",
    call_function_field="function",
    declaration_member_types=frozenset(),
    superclass_field="superclasses",
)

_PROFILES["go"] = LanguageProfile(
    language="go",
    symbol_handlers=symbol_handlers_for("go"),
    import_handlers=import_handlers_for("go"),
    export_handlers=export_handlers_for("go"),
    member_node="selector_expression",
    member_object_field="operand",
    member_property_field="field",
    identifier_nodes=frozenset({"identifier", "field_identifier"}),
    # Go has no heritage clauses; type names appear in declarations,
    # parameters, and composite literals where they are not resolvable
    # references in v1.
    heritage_only_nodes=frozenset({"type_identifier"}),
    # Struct fields and interface method names are declarations.
    declaration_member_types=frozenset({"field_declaration", "method_elem"}),
    extends_parents=frozenset(),
    implements_parents=frozenset(),
    call_parent="call_expression",
    call_function_field="function",
)

_PROFILES["java"] = LanguageProfile(
    language="java",
    symbol_handlers=symbol_handlers_for("java"),
    import_handlers=import_handlers_for("java"),
    export_handlers=export_handlers_for("java"),
    member_node="member_expression",
    member_object_field="object",
    member_property_field="field",
    identifier_nodes=frozenset({"identifier", "type_identifier"}),
    heritage_only_nodes=frozenset({"type_identifier"}),
    extends_parents=frozenset({"superclass", "extends_interfaces"}),
    implements_parents=frozenset({"super_interfaces"}),
    call_parent="method_invocation",
    call_function_field="name",
    declaration_member_types=frozenset({"method_declaration", "field_declaration", "constructor_declaration", "enum_constant"}),
)


_PROFILES["rust"] = LanguageProfile(
    language="rust",
    symbol_handlers=symbol_handlers_for("rust"),
    import_handlers=import_handlers_for("rust"),
    export_handlers=export_handlers_for("rust"),
    member_node="field_expression",
    member_object_field="value",
    member_property_field="field",
    identifier_nodes=frozenset({"identifier", "type_identifier", "field_identifier"}),
    # `impl Trait for Type` and struct/enum field types are the only
    # heritage-adjacent positions; ordinary type annotations elsewhere
    # are not extracted (same rationale as TS/Go/Java).
    heritage_only_nodes=frozenset({"type_identifier"}),
    extends_parents=frozenset(),
    implements_parents=frozenset(),
    call_parent="call_expression",
    call_function_field="function",
    declaration_member_types=frozenset({"field_declaration", "function_signature_item"}),
    impl_node="impl_item",
    impl_trait_field="trait",
    impl_type_field="type",
)


_PROFILES["csharp"] = LanguageProfile(
    language="csharp",
    symbol_handlers=symbol_handlers_for("csharp"),
    import_handlers=import_handlers_for("csharp"),
    export_handlers=export_handlers_for("csharp"),
    member_node="member_access_expression",
    member_object_field="expression",
    member_property_field="name",
    identifier_nodes=frozenset({"identifier"}),
    # C# has no separate `type_identifier` node -- class/interface names
    # are plain `identifier`, same as every other position. Gating
    # extraction on heritage_only_nodes would suppress ordinary
    # identifier references everywhere, not just type positions (see
    # `analysis.semantic.reference_kind`), so it is left empty here,
    # same as Python's `identifier`-everywhere grammar.
    heritage_only_nodes=frozenset(),
    extends_parents=frozenset(),
    # `class X : Base, IStore` puts base class and interfaces in one
    # untyped list; there's no syntactic way to tell which is which
    # without resolving each name's kind first, which reference
    # extraction can't do. All `base_list` entries are recorded as
    # IMPLEMENTS -- inheritance-vs-implementation is not distinguished.
    implements_parents=frozenset({"base_list"}),
    call_parent="invocation_expression",
    call_function_field="function",
    declaration_member_types=frozenset(),
    namespace_nodes=frozenset(
        {"namespace_declaration", "file_scoped_namespace_declaration"}
    ),
)

_C_PROFILE: dict[str, str | frozenset[str]] = {
    "member_node": "field_expression",
    "member_object_field": "argument",
    "member_property_field": "field",
    "identifier_nodes": frozenset({"identifier", "field_identifier", "type_identifier"}),
    "heritage_only_nodes": frozenset(),
    "extends_parents": frozenset(),
    "implements_parents": frozenset(),
    "call_parent": "call_expression",
    "call_function_field": "function",
    "declaration_member_types": frozenset({"field_declaration"}),
}

_PROFILES["c"] = LanguageProfile(
    language="c", symbol_handlers=symbol_handlers_for("c"),
    import_handlers=import_handlers_for("c"), export_handlers=export_handlers_for("c"),
    **_C_PROFILE,  # type: ignore[arg-type,unused-ignore]  # pyright: ignore[reportArgumentType,reportCallIssue]
)

_PROFILES["cpp"] = LanguageProfile(
    language="cpp", symbol_handlers=symbol_handlers_for("cpp"),
    import_handlers=import_handlers_for("cpp"), export_handlers=export_handlers_for("cpp"),
    member_node="field_expression", member_object_field="argument", member_property_field="field",
    identifier_nodes=frozenset({"identifier", "field_identifier", "type_identifier", "namespace_identifier"}),
    heritage_only_nodes=frozenset({"type_identifier"}),
    extends_parents=frozenset({"base_class_clause"}),
    implements_parents=frozenset(), call_parent="call_expression", call_function_field="function",
    declaration_member_types=frozenset({"field_declaration", "declaration"}),
)


def profile_for(language: str) -> LanguageProfile | None:
    return _PROFILES.get(language)
