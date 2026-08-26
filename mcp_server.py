from pathlib import Path

from mcp.server.mcpserver import MCPServer

from cli import (
    cmd_callees,
    cmd_callers,
    cmd_context,
    cmd_definition,
    cmd_imports,
    cmd_index,
    cmd_search,
    cmd_status,
    default_db_path,
    resolve_provider,
)

mcp = MCPServer(
    name="ckg",
    instructions=(
        "Code Knowledge Graph: a local-first semantic index over a repository "
        "supporting TypeScript, JavaScript, TSX, JSX, Python, and Go. Call "
        "index_repository once before any other tool for a given path. Prefer "
        "definition/callers/callees for exact structural questions and "
        "search/context for open-ended ones."
    ),
)


def _not_indexed(path: str, db_path: str) -> dict:
    return {
        "error": f'No index found at {db_path}. Call index_repository(path="{path}") first.'
    }


def _candidate_dict(candidate) -> dict:
    return {
        "symbol_name": candidate.symbol_name,
        "qualified_name": candidate.qualified_name,
        "kind": candidate.symbol_kind,
        "relative_path": candidate.relative_path,
        "score": candidate.score,
        "sources": list(candidate.sources),
    }


def _import_dict(pair) -> dict:
    import_reference, resolved = pair
    entry: dict = {
        "module_path": import_reference.module_path,
        "imported_name": import_reference.imported_name,
        "local_name": import_reference.local_name,
        "resolved": resolved is not None,
    }

    if resolved is not None:
        entry["target_file"] = resolved.target_document.relative_path
        entry["target_symbol"] = (
            resolved.target_symbol.name if resolved.target_symbol is not None else None
        )

    return entry


def _context_entry_dict(entry) -> dict:
    return {
        "qualified_name": entry.qualified_name,
        "kind": entry.symbol_kind,
        "relative_path": entry.relative_path,
        "location": entry.location,
        "role": entry.role,
        "source": entry.source,
    }


@mcp.tool()
def index_repository(path: str, embed: bool = False) -> dict:
    """Build or update the semantic index for a repository at `path`.

    Must be called (once) before any other tool is used against that path.
    Cheap and safe to call again after edits - only changed files are
    reprocessed. `embed` also runs the embedding worker so search/context
    can use vector similarity, not just lexical/graph matching; it loads a
    local ML model and is slower, so it defaults to off.
    """
    db_path = default_db_path(path)
    provider = None

    if embed:
        from embeddings.local_provider import LocalEmbeddingProvider

        provider = LocalEmbeddingProvider()

    report = cmd_index(path, db_path, provider=provider)

    return {
        "db_path": db_path,
        "parsed_files": report.parsed_files,
        "resolved_references": report.resolved_references,
        "changes": {p: c.value for p, c in report.changes.items()},
    }


@mcp.tool()
def repository_status(path: str = ".") -> dict:
    """Report index generation and document/symbol/chunk/embedding counts for `path`."""
    db_path = default_db_path(path)

    if not Path(db_path).exists():
        return {"indexed": False}

    return {"indexed": True, **cmd_status(db_path)}


@mcp.tool()
def definition(name: str, path: str = ".") -> dict:
    """Find the exact definition site(s) of a symbol by name."""
    db_path = default_db_path(path)

    if not Path(db_path).exists():
        return _not_indexed(path, db_path)

    retrieval = cmd_definition(db_path, name)
    return {"results": [_candidate_dict(c) for c in retrieval.candidates]}


@mcp.tool()
def callers(name: str, path: str = ".") -> dict:
    """Find every symbol that calls `name` (1-hop incoming graph neighborhood)."""
    db_path = default_db_path(path)

    if not Path(db_path).exists():
        return _not_indexed(path, db_path)

    retrieval = cmd_callers(db_path, name)
    return {"results": [_candidate_dict(c) for c in retrieval.candidates]}


@mcp.tool()
def callees(name: str, path: str = ".") -> dict:
    """Find every symbol that `name` calls (1-hop outgoing graph neighborhood)."""
    db_path = default_db_path(path)

    if not Path(db_path).exists():
        return _not_indexed(path, db_path)

    retrieval = cmd_callees(db_path, name)
    return {"results": [_candidate_dict(c) for c in retrieval.candidates]}


@mcp.tool()
def search(query: str, path: str = ".", top_k: int = 5) -> dict:
    """Hybrid semantic search: lexical (FTS) + vector + exact-symbol + graph
    expansion + reranking over the indexed repository. Use for open-ended or
    natural-language questions; use definition/callers/callees for exact
    structural lookups instead.
    """
    db_path = default_db_path(path)

    if not Path(db_path).exists():
        return _not_indexed(path, db_path)

    provider = resolve_provider(db_path, use_vector=True)
    retrieval = cmd_search(db_path, query, provider=provider, top_k=top_k)

    return {
        "results": [_candidate_dict(c) for c in retrieval.candidates],
        "vector_search_used": provider is not None,
    }


@mcp.tool()
def imports(file: str, path: str = ".") -> dict:
    """List a file's own import statements and where each one resolves to."""
    db_path = default_db_path(path)

    if not Path(db_path).exists():
        return _not_indexed(path, db_path)

    return {"imports": [_import_dict(pair) for pair in cmd_imports(db_path, file)]}


@mcp.tool()
def context(query: str, path: str = ".", token_budget: int = 2000, top_k: int = 5) -> dict:
    """Build a token-budgeted context pack for a query: primary/supporting
    definitions with source excerpts, important relationships between them,
    and the file paths involved. This is the right tool for "give me enough
    context to answer X" rather than a raw candidate list.
    """
    db_path = default_db_path(path)

    if not Path(db_path).exists():
        return _not_indexed(path, db_path)

    provider = resolve_provider(db_path, use_vector=True)
    pack = cmd_context(db_path, query, token_budget=token_budget, provider=provider, top_k=top_k)

    return {
        "query": pack.query,
        "token_budget": pack.token_budget,
        "total_tokens": pack.total_tokens,
        "primary_definitions": [_context_entry_dict(e) for e in pack.primary_definitions],
        "supporting_definitions": [_context_entry_dict(e) for e in pack.supporting_definitions],
        "relationships": list(pack.relationships),
        "file_paths": list(pack.file_paths),
    }


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
