# C and C++ support design

## Declaration and definition identity

C and C++ declarations and definitions are separate symbol records. A
prototype in a header is not silently merged with a function body in a
translation unit because the current `Symbol` model has one source location
and a merge would lose the declaration location. A model-level
`DEFINITION_OF` relationship links a definition to its matching declaration
when both are indexed. Matching uses language, owning qualified name, name,
and the normalized function identity (parameter types/arity where available).

Callers resolve normally to the declaration when only a header is indexed. If
the implementation is indexed, callers/callees retain the declaration edge
and the definition link makes the implementation discoverable. An unresolved
or declaration-only function remains a valid symbol with no definition edge.

## C++ overload identity

Stable identity gains an optional deterministic discriminator. C++ function
and method handlers use an ownership-qualified signature containing normalized
parameter types and arity. Thus overloads with the same name and qualified
name cannot collide. When a type is incomplete, the handler falls back to
arity plus normalized parameter text; if even that is unavailable, the AST
parameter count and source-order-independent normalized declaration text are
used. Existing languages leave the discriminator empty, preserving their
identity behavior.

## Includes

`#include "local.h"` is recorded as an import and resolves against repository
relative candidates (including the importing directory and repository root).
Angle-bracket/system includes are recorded for observability but deliberately
remain unresolved; the index does not claim knowledge of external headers.
Missing quoted includes are also unresolved and do not create guessed files.
The existing `IMPORTS` relationship represents a resolved local include; no
new relationship kind is needed for include edges.

## C++ language boundaries

Namespaces and class ownership contribute to qualified names. Constructors,
destructors, methods, inheritance, qualified calls, and basic templates are
indexed. Template declarations use their concrete declared name/signature and
are not instantiated into synthetic duplicate symbols.

