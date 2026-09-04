# pyright: reportImportCycles=false
import argparse
import json
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, cast

from embeddings.provider import EmbeddingProvider
from evaluation.runner import EvaluationReport, run_evaluation
from indexing.embedding_queue import queue_status, run_embedding_worker
from indexing.indexer import IndexRunReport, reindex_index
from models.entities.import_references import ImportReference
from models.entities.resolved_import_reference import ResolvedImportReference
from retrieval.context_builder import ContextPack
from retrieval.hybrid_retriever import HybridRetrieval
from retrieval.index_queries import (
    build_context_pack_from_index,
    build_hybrid_retriever,
)
from session_memory import SessionService
from storage.index_store import count_rows, current_generation

DEFAULT_DB_DIRNAME = ".ckg"
DEFAULT_DB_FILENAME = "index.sqlite"


def _get_version() -> str:
    try:
        from importlib.metadata import version as _pkg_version

        return _pkg_version("code-knowledge-graph")
    except (ImportError, AttributeError, OSError, ValueError, KeyError):
        pass
    # fallback for source checkouts without installed metadata
    try:
        import tomllib  # Python 3.11+

        pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
        if pyproject.exists():
            with pyproject.open("rb") as fh:
                data = tomllib.load(fh)
                return data.get("project", {}).get("version", "0.0.0+source")
    except (ImportError, OSError, KeyError, ValueError):
        pass
    return "0.0.0+source"


def _is_tty() -> bool:
    try:
        return sys.stderr.isatty()
    except (OSError, ValueError, AttributeError):
        return False


def _emit_progress(message: str) -> None:
    if _is_tty():
        print(message, file=sys.stderr)


def default_db_path(root: str) -> str:
    return str(Path(root) / DEFAULT_DB_DIRNAME / DEFAULT_DB_FILENAME)


def has_embeddings(db_path: str) -> bool:
    return count_rows(db_path)["embeddings"] > 0


# ---- commands (pure, testable independently of argument parsing) ----


def cmd_index(
    root: str,
    db_path: str,
    *,
    provider: EmbeddingProvider | None = None,
) -> IndexRunReport:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    if _is_tty():
        print(f"Indexing {root}...", file=sys.stderr)

    report = reindex_index(
        db_path, root, on_progress=_emit_progress if _is_tty() else None
    )

    if _is_tty():
        print(f"Parsed {report.parsed_files} files...", file=sys.stderr)

    if provider is not None:
        # drain embeddings in batches so large repos emit periodic progress
        # instead of appearing hung; suppress when stderr is not a TTY
        total = 0
        batch_size = 50
        while True:
            batch_report = run_embedding_worker(
                db_path,
                provider,
                limit=batch_size,
                on_progress=_emit_progress if _is_tty() else None,
            )
            if batch_report.claimed == 0:
                break
            total += batch_report.done
            if _is_tty():
                print(f"Embedded {total} chunks...", file=sys.stderr)
            if batch_report.claimed < batch_size:
                # check if any pending remain; if not, break, else continue
                try:
                    pending = queue_status(db_path)  # pyright: ignore[reportAttributeAccessIssue,reportOperatorIssue,reportIndexIssue]
                    runnable = pending.get("PENDING", 0) + max(
                        0, pending.get("FAILED", 0) - pending.get("exhausted", 0)
                    )
                    if runnable == 0:
                        break
                except Exception:
                    break

    return report


def cmd_status(db_path: str) -> dict[str, object]:
    from storage.index_store import count_rows

    counts = count_rows(db_path)

    return {
        "generation": current_generation(db_path),
        "documents": counts["documents"],  # pyright: ignore[reportAttributeAccessIssue,reportOperatorIssue,reportIndexIssue]
        "symbols": counts["symbols"],  # pyright: ignore[reportAttributeAccessIssue,reportOperatorIssue,reportIndexIssue]
        "chunks": counts["chunks"],  # pyright: ignore[reportAttributeAccessIssue,reportOperatorIssue,reportIndexIssue]
        "embeddings": counts["embeddings"],  # pyright: ignore[reportAttributeAccessIssue,reportOperatorIssue,reportIndexIssue]
        "embedding_jobs": queue_status(db_path),
    }


def cmd_search(
    db_path: str,
    query: str,
    *,
    provider: EmbeddingProvider | None = None,
    top_k: int = 5,
) -> HybridRetrieval:
    retriever = build_hybrid_retriever(db_path, provider=provider)
    return retriever.retrieve(query, top_k=top_k)


def cmd_definition(db_path: str, name: str) -> HybridRetrieval:
    retriever = build_hybrid_retriever(db_path)
    return retriever.retrieve(f"where is {name} defined")


def cmd_callers(db_path: str, name: str) -> HybridRetrieval:
    retriever = build_hybrid_retriever(db_path)
    return retriever.retrieve(f"who calls {name}")


def cmd_callees(db_path: str, name: str) -> HybridRetrieval:
    retriever = build_hybrid_retriever(db_path)
    return retriever.retrieve(f"what does {name} call")


def cmd_imports(
    db_path: str,
    relative_path: str,
) -> list[tuple[ImportReference, ResolvedImportReference | None]]:
    from storage.index_store import load_imports_for_path

    return load_imports_for_path(db_path, relative_path)


def cmd_context(
    db_path: str,
    query: str,
    *,
    token_budget: int,
    provider: EmbeddingProvider | None = None,
    top_k: int = 5,
) -> ContextPack:
    return build_context_pack_from_index(
        db_path,
        query,
        token_budget=token_budget,
        provider=provider,
        top_k=top_k,
    )


def cmd_eval(
    *, provider: EmbeddingProvider | None = None, top_k: int = 5
) -> EvaluationReport:
    return run_evaluation(provider=provider, top_k=top_k)


def cmd_watch(
    root: str,
    db_path: str,
    *,
    provider: EmbeddingProvider | None = None,
    debounce_seconds: float = 0.5,
    embed_limit: int | None = 200,
) -> None:
    from indexing.watcher import watch_repository

    watch_repository(
        root,
        db_path,
        provider=provider,
        debounce_seconds=debounce_seconds,
        embed_limit=embed_limit,
        on_report=lambda report: _print_index_report(report, db_path),
    )


def cmd_doctor(root: str = ".", verbose: bool = False) -> int:
    """One-command ops check — like `cce services`."""
    from pathlib import Path

    p = Path(root)
    db_path = default_db_path(root)
    checks: list[tuple[str, bool, str]] = []
    # .ckg exists
    has_db = Path(db_path).exists()
    checks.append(("index present", has_db, db_path if has_db else "no index — run `ckg index .`"))
    # lock free
    try:
        from indexing.resource_governor import ProjectIndexLock

        lk = ProjectIndexLock(root)
        free = lk.acquire(blocking=False)
        if free:
            lk.release()
        checks.append(("lock free", free, "locked" if not free else "free"))
    except Exception as e:
        checks.append(("lock free", False, str(e)))
    # queue pending
    try:
        if has_db:
            qs = queue_status(db_path)  # type: ignore
            pending = qs.get("PENDING", 0) + qs.get("FAILED", 0) - qs.get("exhausted", 0)
            checks.append(("embedding queue", pending == 0, f"pending={pending}"))
        else:
            checks.append(("embedding queue", True, "no db"))
    except Exception as e:
        checks.append(("embedding queue", False, str(e)))
    # git hook
    try:
        from indexing.git_hooks import _git_hooks_dir

        hd = _git_hooks_dir(p)
        hook = (hd / "hooks" / "post-commit") if hd else None
        has_hook = hook is not None and hook.exists() and "CKG keep-fresh" in hook.read_text(errors="ignore")
        checks.append(("git hook", has_hook, str(hook) if has_hook else "no hook — run `ckg init`"))
    except Exception:
        checks.append(("git hook", False, "unknown"))
    # embedding backend
    try:
        prov = _detect_provider()
        checks.append(("embedding backend", prov is not None, prov.model_id if prov else "none - FTS+graph only (ok)"))  # type: ignore[operator]
    except Exception as e:
        checks.append(("embedding backend", False, str(e)))

    ok = all(v for _, v, _ in checks)
    for name, passed, detail in checks:
        mark = "✓" if passed else "✗"
        print(f"{mark} {name}: {detail}")
        if verbose:
            pass
    return 0 if ok else 1


def _detect_provider(*, forced_model: str | None = None) -> EmbeddingProvider | None:
    """Auto-detect: Ollama if reachable, then local sentence-transformers if importable, else None.

    Respects CKG_EMBED_BACKEND (ollama/local) and CKG_OLLAMA_URL/MODEL env vars.
    Local import is lazy so core install never touches torch.
    """
    import os

    forced = os.environ.get("CKG_EMBED_BACKEND", "").strip().lower()
    if forced and forced not in ("ollama", "local", "", "auto"):
        raise RuntimeError(
            f"Unknown embedding backend '{forced}'. Expected 'ollama' or 'local'. "
            "Unset CKG_EMBED_BACKEND or set to 'ollama'/'local'."
        )

    # Ollama first (unless forced to local)
    if forced != "local":
        try:
            from embeddings.ollama_provider import (
                OllamaEmbeddingProvider,
                ollama_available,
            )

            # ollama_available uses env-var resolved URL internally
            if ollama_available():
                try:
                    return (
                        OllamaEmbeddingProvider(model_name=forced_model)
                        if forced_model
                        else OllamaEmbeddingProvider()
                    )
                except Exception:
                    # -- Ollama init may raise broad errors; fallback to local unless forced
                    if forced == "ollama":
                        raise
                    # fall through to local
            elif forced == "ollama":
                raise RuntimeError(
                    "Ollama backend forced via CKG_EMBED_BACKEND=ollama but no Ollama server reachable at "
                    f"{os.environ.get('CKG_OLLAMA_URL', os.environ.get('OLLAMA_HOST', 'http://localhost:11434'))}. "
                    "Start Ollama or unset CKG_EMBED_BACKEND."
                )
        except ImportError:
            pass

    if forced != "ollama":
        try:
            import importlib.util

            if importlib.util.find_spec("sentence_transformers") is not None:
                from embeddings.local_provider import LocalEmbeddingProvider

                return (
                    LocalEmbeddingProvider(model_name=forced_model)
                    if forced_model
                    else LocalEmbeddingProvider()
                )
            elif forced == "local":
                raise RuntimeError(
                    "Local embeddings forced via CKG_EMBED_BACKEND=local but 'sentence-transformers' not installed. "
                    "Install with: pip install code-knowledge-graph[local]"
                )
        except RuntimeError:
            raise
        except (
            ImportError,
            OSError,
            ValueError,
        ) as e:  # -- provider detection fallback must not crash CLI
            if forced == "local":
                raise RuntimeError(
                    "Local embeddings require 'sentence-transformers'. "
                    "Install with: pip install code-knowledge-graph[local]"
                ) from e
    return None


def resolve_provider(db_path: str, *, use_vector: bool) -> EmbeddingProvider | None:
    if not use_vector:
        return None
    # Default to no embeddings if none available — FTS+graph is out-of-box (0.83/0.78 fixture)
    # Caller decides legibility when vector was explicitly requested.
    try:
        return _detect_provider()
    except RuntimeError:
        raise
    except Exception:
        return None


def _require_provider_or_explain() -> EmbeddingProvider:
    provider = _detect_provider()
    if provider is None:
        raise RuntimeError(
            "No embedding backend available. Either:\n"
            "  1. Install local embeddings: pip install code-knowledge-graph[local]\n"
            "  2. Start an Ollama server at http://localhost:11434 and pull nomic-embed-text (ollama pull nomic-embed-text)"
        )
    return provider


def _ensure_mcp_entry(path: Path, container_key: str | None) -> str:
    if container_key is None:
        return "written"
    entry: dict[str, object] = {"command": "ckg-mcp"}
    if path.exists():
        # An unreadable or non-object config is the user's file, not ours to
        # replace: rewriting it would silently discard whatever they had.
        text = path.read_text(encoding="utf-8")

        try:
            data: dict[str, object] = json.loads(text) if text.strip() else {}
        except json.JSONDecodeError as error:
            raise ValueError(f"{path} is not valid JSON: {error}") from error

        if not isinstance(data, dict):
            raise ValueError(f"{path} must contain a JSON object")

        # check if already configured under any common container
        for key in (container_key, "mcpServers", "servers", "mcp"):
            container = data.get(key)
            if isinstance(container, dict) and "ckg" in container:  # type: ignore[operator]
                return "already configured"
        container = data.get(container_key)  # type: ignore[assignment]
        if not isinstance(container, dict):
            data[container_key] = {}
            container = data[container_key]
        if "ckg" in container:  # type: ignore[operator]  # pyright: ignore[reportOperatorIssue]
            return "already configured"
        container["ckg"] = entry  # type: ignore[index]  # pyright: ignore[reportIndexIssue,reportOperatorIssue]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        return "written"
    else:
        data = {container_key: {"ckg": entry}}
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        return "written"


def cmd_init(root: str = ".", *, agents: list[str] | None = None) -> dict[str, str]:
    from ckg.editors import (
        EDITORS,
        atomic_write_text,
        detect_editors,
        project_storage_slug,
    )

    root_path = Path(root)
    if agents is None or agents == ["auto"]:
        agents = detect_editors(root_path)
        if agents == ["claude"]:
            agents = ["claude"]
        # auto: claude always + detected
        if "claude" not in agents:
            agents = ["claude"] + agents
    elif "all" in agents:
        agents = list(EDITORS.keys())
    # map agent -> target path/container
    editor_targets: dict[str, tuple[Path, str | None]] = {}
    for ag in agents:
        info = EDITORS.get(ag)
        if not info:
            continue
        cfg = info["config_path"]
        # handle ~/ expansion for codex
        if cfg.startswith("~"):
            cfg_path = Path(cfg).expanduser()
        else:
            cfg_path = root_path / cfg
        editor_targets[ag] = (cfg_path, info["container_key"])
    results: dict[str, str] = {}
    for ag, (path, container_key) in editor_targets.items():
        if container_key is None:
            # copilot/pi instruction files — versioned block with upgrade
            from ckg.editors import CKG_BLOCK_START, ensure_block_content

            existing = path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""
            if CKG_BLOCK_START in existing:
                results[str(path)] = "already configured"
            else:
                new_content, already = ensure_block_content(existing)
                if already:
                    results[str(path)] = "already configured"
                else:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    atomic_write_text(path, new_content)
                    results[str(path)] = "written"
            continue
        if path.suffix == ".toml":
            # codex TOML — append section, not JSON, sanitize
            from ckg.editors import toml_escape

            marker = 'ckg-mcp'
            if path.exists() and marker in path.read_text(encoding="utf-8", errors="ignore"):
                results[str(path)] = "already configured"
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                slug = project_storage_slug(str(root_path.resolve()))
                # sanitize slug for TOML
                slug_esc = toml_escape(slug)
                toml_snippet = f'\n[mcp_servers.ckg-{slug_esc}]\ncommand = "ckg-mcp"\n'
                # atomic append
                existing = path.read_text(encoding="utf-8") if path.exists() else ""
                atomic_write_text(path, existing + toml_snippet)
                results[str(path)] = "written"
            continue
        status = _ensure_mcp_entry(path, container_key)
        results[str(path)] = status
    # git hooks
    try:
        from indexing.git_hooks import install_hooks

        install_hooks(root_path)
    except Exception:
        pass
    return results


def cmd_uninstall(root: str = ".") -> dict[str, str]:
    from indexing.git_hooks import uninstall_hooks

    root_path = Path(root)
    removed = {}
    for name in [".mcp.json", ".vscode/mcp.json", ".cursor/mcp.json", "opencode.json"]:
        p = root_path / name
        if p.exists():
            # remove ckg entry if present
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                for k in ("mcpServers", "mcp", "servers"):
                    if isinstance(data.get(k), dict) and "ckg" in data[k]:
                        del data[k]["ckg"]
                        p.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
                        removed[str(p)] = "removed"
            except Exception:
                pass
    for h in uninstall_hooks(root_path):
        removed[h] = "removed"
    return removed


def cmd_embed(
    db_path: str,
    *,
    provider: EmbeddingProvider | None = None,
    limit: int | None = None,
):
    if provider is None:
        provider = _require_provider_or_explain()
    if limit is None:
        # when no explicit limit, drain in batches with periodic progress
        total = 0
        batch_size = 50
        last_report = None
        while True:
            batch_report = run_embedding_worker(
                db_path,
                provider,
                limit=batch_size,
                on_progress=_emit_progress if _is_tty() else None,
            )
            if batch_report.claimed == 0:
                if last_report is None:
                    return batch_report
                break
            last_report = batch_report
            total += batch_report.done
            if _is_tty():
                print(f"Embedded {total} chunks...", file=sys.stderr)
            # peek queue to decide continuation
            try:
                pending = queue_status(db_path)  # pyright: ignore[reportAttributeAccessIssue,reportOperatorIssue,reportIndexIssue]
                runnable = pending.get("PENDING", 0) + max(
                    0, pending.get("FAILED", 0) - pending.get("exhausted", 0)
                )
                if runnable == 0:
                    break
            except Exception:
                break
        return last_report if last_report is not None else batch_report
    return run_embedding_worker(
        db_path,
        provider,
        limit=limit,
        on_progress=_emit_progress if _is_tty() else None,
    )


def _background_lock_path(db_path: str) -> Path:
    return Path(db_path).parent / f".{Path(db_path).name}.embed.lock"


def _try_acquire_embed_lock(db_path: str, lease: int = 300) -> bool:
    lock = _background_lock_path(db_path)
    now = time.time()
    if lock.exists():
        try:
            mtime = lock.stat().st_mtime
            if now - mtime < lease:
                return False
            lock.unlink()
        except OSError:
            return False
    try:
        lock.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        return True
    except FileExistsError:
        return False
    except OSError:
        return False


def _maybe_spawn_background_embed(db_path: str) -> None:
    # skip when queue empty (common after first run due to hash reuse)
    try:
        counts = queue_status(db_path)
        pending = counts.get("PENDING", 0)  # pyright: ignore[reportAttributeAccessIssue,reportOperatorIssue,reportIndexIssue]
        failed = counts.get("FAILED", 0)
        exhausted = counts.get("exhausted", 0)
        runnable = pending + max(0, failed - exhausted)
        if runnable == 0:
            return
    except Exception:
        return
    if not _try_acquire_embed_lock(db_path):
        return
    # Auto-detect backend for background drain; core install may have none
    code = (
        "import sys\n"
        "from pathlib import Path\n"
        "db_path=sys.argv[1]\n"
        "lock=Path(db_path).parent / f'.{Path(db_path).name}.embed.lock'\n"
        "try:\n"
        "    from ckg.cli import _detect_provider\n"
        "    from indexing.embedding_queue import run_embedding_worker\n"
        "    provider=_detect_provider()\n"
        "    if provider is not None:\n"
        "        run_embedding_worker(db_path, provider)\n"
        "except Exception:\n"
        "    pass\n"
        "finally:\n"
        "    try:\n"
        "        lock.unlink()\n"
        "    except Exception:\n"
        "        pass\n"
    )
    try:
        subprocess.Popen(
            [sys.executable, "-c", code, db_path],
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
        )
    except Exception:
        try:
            _background_lock_path(db_path).unlink()
        except Exception:
            pass


# ---- output formatting ----


def _print_index_report(report: IndexRunReport, db_path: str) -> None:
    counts: dict[str, int] = {}
    for change in report.changes.values():
        counts[change.value] = counts.get(change.value, 0) + 1  # pyright: ignore[reportAttributeAccessIssue,reportOperatorIssue,reportIndexIssue]

    print(f"Indexed into {db_path}")
    print(f"  parsed files:        {report.parsed_files}")
    print(f"  resolved references: {report.resolved_references}")
    for kind in ("new", "changed", "unchanged", "deleted"):
        if kind in counts:
            print(f"  {kind}: {counts[kind]}")  # pyright: ignore[reportAttributeAccessIssue,reportOperatorIssue,reportIndexIssue]


def _print_status(
    status: dict[str, Any],
    *,
    oneline: bool = False,
) -> None:
    if oneline:
        jobs = cast(dict[str, int], status["embedding_jobs"])
        pending = jobs.get("PENDING", 0) + jobs.get("FAILED", 0) - jobs.get("exhausted", 0)
        pending = max(0, pending)
        print(
            f"symbols {status['symbols']} chunks {status['chunks']} pending {pending} gen {status['generation']}"
        )
        return
    print(f"generation: {status['generation']}")
    print(f"documents:  {status['documents']}")
    print(f"symbols:    {status['symbols']}")
    print(f"chunks:     {status['chunks']}")
    chunks = status["chunks"]  # pyright: ignore[reportAttributeAccessIssue,reportOperatorIssue,reportIndexIssue]
    embeddings = status["embeddings"]  # pyright: ignore[reportAttributeAccessIssue,reportOperatorIssue,reportIndexIssue]
    if chunks:
        pct = (int(embeddings) / int(chunks) * 100) if chunks else 0  # type: ignore[arg-type]  # pyright: ignore[reportOperatorIssue,reportArgumentType]
        if int(embeddings) < int(chunks):  # type: ignore[arg-type]  # pyright: ignore[reportOperatorIssue,reportArgumentType]
            print(
                f"embeddings: {embeddings}/{chunks} ({pct:.0f}%) — run `ckg embed` to enable vector search"
            )
        else:
            print(f"embeddings: {embeddings}/{chunks} ({pct:.0f}%)")
    else:
        print(f"embeddings: {embeddings}")

    jobs = cast(dict[str, int], status["embedding_jobs"])
    if jobs:
        job_summary = ", ".join(f"{k}={v}" for k, v in sorted(jobs.items()))
        print(f"embedding queue: {job_summary}")
        pending = jobs.get("PENDING", 0) + jobs.get("FAILED", 0) - jobs.get("exhausted", 0)
        if pending > 0 and int(embeddings) < int(chunks):  # type: ignore[arg-type]  # pyright: ignore[reportOperatorIssue,reportArgumentType]
            print(
                f"vector search degraded: {pending} chunks pending embedding — run `ckg embed`"
            )


def _print_embed_report(report) -> None:
    print(
        f"embeddings: claimed={report.claimed} done={report.done} reused={report.reused} stale={report.stale} failed={report.failed}"
    )


def _print_candidates(retrieval: HybridRetrieval) -> None:
    if not retrieval.candidates:
        print("No results.")
        return

    for candidate in retrieval.candidates:
        sources = ",".join(candidate.sources)
        print(
            f"{candidate.qualified_name or candidate.symbol_name} "
            f"({candidate.symbol_kind}) — {candidate.relative_path} "
            f"[score={candidate.score:.3f} sources={sources}]"
        )


def _print_imports(
    imports: list[tuple[ImportReference, ResolvedImportReference | None]],
) -> None:
    if not imports:
        print("No imports found.")
        return

    for import_reference, resolved in imports:
        target = "unresolved"

        if resolved is not None:
            target = resolved.target_document.relative_path
            if resolved.target_symbol is not None:
                target += f"::{resolved.target_symbol.name}"

        print(
            f"{import_reference.local_name} <- {import_reference.imported_name} "
            f'from "{import_reference.module_path}" -> {target}'
        )


def _print_context_pack(pack: ContextPack) -> None:
    print(f"context for: {pack.query}")
    print(f"tokens: {pack.total_tokens}/{pack.token_budget}")

    for label, entries in (
        ("primary", pack.primary_definitions),
        ("supporting", pack.supporting_definitions),
    ):
        for entry in entries:
            print(
                f"\n[{label}] {entry.qualified_name} ({entry.symbol_kind}) — {entry.location}"
            )
            if entry.source:
                print(entry.source)

    if pack.relationships:
        print("\nrelationships:")
        for relationship in pack.relationships:
            print(f"  {relationship}")


def _print_eval_report(report: EvaluationReport) -> None:
    print("Benchmark: fixed evaluation repo (tests/fixtures/evaluation_repo)\n")

    for question in report.questions:
        correct = (
            "-"
            if question.correct is None
            else ("PASS" if question.correct else "FAIL")
        )
        print(
            f"[{question.category:10}] {correct:4} "
            f"recall@k={question.recall_at_k:.2f} mrr={question.reciprocal_rank:.2f} "
            f"{question.text}"
        )

    print()
    print(f"definition accuracy:        {report.definition_accuracy:.2f}")
    print(f"relationship accuracy:      {report.relationship_accuracy:.2f}")
    print(f"import resolution accuracy: {report.import_resolution_accuracy:.2f}")
    print(f"mean recall@k:              {report.mean_recall_at_k:.2f}")
    print(f"mean reciprocal rank:       {report.mean_reciprocal_rank:.2f}")
    print(
        f"context tokens:             {report.context_tokens} (baseline {report.baseline_tokens})"
    )
    print(
        f"initial indexing:           {report.initial_indexing_seconds * 1000:.1f} ms"
    )
    print(
        f"incremental indexing:       {report.incremental_indexing_seconds * 1000:.1f} ms"
    )
    print(f"embedding cache hit rate:   {report.embedding_cache_hit_rate:.2f}")


# ---- argument parsing / dispatch ----


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ckg",
        description="Code Knowledge Graph — local-first semantic index",
        epilog="examples:\n  ckg init --agent all    # configure all editors\n  ckg index .             # index repo\n  ckg search \"login\"     # hybrid search\n  ckg doctor .            # ops check\n  ckg dashboard --no-browser",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=_get_version())
    parser.add_argument("--db", help="override the index database path")

    subparsers = parser.add_subparsers(dest="command", required=True)

    index_parser = subparsers.add_parser(
        "index", help="build or update the semantic index"
    )
    index_parser.add_argument("path")
    index_parser.add_argument(
        "--embed", action="store_true", help="also run the embedding worker"
    )
    index_parser.add_argument(
        "--no-background",
        action="store_true",
        help="disable background embedding drain",
    )

    status_parser = subparsers.add_parser(
        "status", help="show index generation and counts"
    )
    status_parser.add_argument("path", nargs="?", default=".")
    status_parser.add_argument(
        "--oneline", action="store_true", help="one-line summary for shell prompts"
    )

    search_parser = subparsers.add_parser("search", help="hybrid search over the index")
    search_parser.add_argument("query")
    search_parser.add_argument("path", nargs="?", default=".")
    search_parser.add_argument("--top-k", type=int, default=5)
    search_parser.add_argument("--no-vector", action="store_true")

    definition_parser = subparsers.add_parser(
        "definition", help="find where a symbol is defined"
    )
    definition_parser.add_argument("name")
    definition_parser.add_argument("path", nargs="?", default=".")

    callers_parser = subparsers.add_parser("callers", help="find callers of a symbol")
    callers_parser.add_argument("name")
    callers_parser.add_argument("path", nargs="?", default=".")

    callees_parser = subparsers.add_parser("callees", help="find callees of a symbol")
    callees_parser.add_argument("name")
    callees_parser.add_argument("path", nargs="?", default=".")

    imports_parser = subparsers.add_parser("imports", help="list a file's imports")
    imports_parser.add_argument("file")
    imports_parser.add_argument("path", nargs="?", default=".")

    context_parser = subparsers.add_parser(
        "context", help="build a token-budgeted context pack"
    )
    context_parser.add_argument("query")
    context_parser.add_argument("path", nargs="?", default=".")
    context_parser.add_argument("--budget", type=int, default=2000)
    context_parser.add_argument("--top-k", type=int, default=5)
    context_parser.add_argument("--no-vector", action="store_true")

    eval_parser = subparsers.add_parser(
        "eval", help="run the fixed benchmark and report retrieval/indexing metrics"
    )
    eval_parser.add_argument(
        "--embed", action="store_true", help="also exercise vector search"
    )
    eval_parser.add_argument("--top-k", type=int, default=5)

    watch_parser = subparsers.add_parser(
        "watch", help="keep the index fresh by watching for file changes"
    )
    watch_parser.add_argument("path")
    watch_parser.add_argument(
        "--no-embed",
        action="store_true",
        help="disable embedding worker after each reindex",
    )
    watch_parser.add_argument(
        "--debounce",
        type=float,
        default=0.5,
        help="seconds of edit quiet before reindexing (default 0.5)",
    )

    init_parser = subparsers.add_parser("init", help="configure MCP for this project")
    init_parser.add_argument("path", nargs="?", default=".")
    init_parser.add_argument("--agent", choices=["auto", "claude", "cursor", "vscode", "codex", "copilot", "pi", "opencode", "gemini", "all"], default="auto")
    init_parser.add_argument("--plugin", action="store_true", help="also generate plugin")
    uninstall_parser = subparsers.add_parser("uninstall", help="remove CKG MCP configs and hooks")
    uninstall_parser.add_argument("path", nargs="?", default=".")

    embed_parser = subparsers.add_parser("embed", help="drain the embedding queue")
    embed_parser.add_argument("path", nargs="?", default=".")
    embed_parser.add_argument("--limit", type=int, default=None)

    doctor_parser = subparsers.add_parser("doctor", help="check index health, locks, hooks, and embedding backend (like cce services)")
    doctor_parser.add_argument("path", nargs="?", default=".")
    doctor_parser.add_argument("--verbose", action="store_true", help="show detailed checks")

    sessions = subparsers.add_parser(
        "sessions", help="manage local project session memory"
    )
    session_sub = sessions.add_subparsers(dest="sessions_command", required=True)
    for name in ("start", "list"):
        p = session_sub.add_parser(name)
        p.add_argument("path", nargs="?", default=".")
    p = session_sub.add_parser("status")
    p.add_argument("path", nargs="?", default=".")
    p.add_argument("session_id", nargs="?")
    p = session_sub.add_parser("timeline")
    p.add_argument("path", nargs="?", default=".")
    p.add_argument("session_id", nargs="?")
    p.add_argument("--limit", type=int, default=50)
    p = session_sub.add_parser("recall")
    p.add_argument("query")
    p.add_argument("path", nargs="?", default=".")
    p.add_argument("--limit", type=int, default=10)
    p = session_sub.add_parser("export")
    p.add_argument("path", nargs="?", default=".")
    p.add_argument("session_id", nargs="?")
    p.add_argument("--format", choices=("json", "markdown"), default="json")
    p = session_sub.add_parser("prune")
    p.add_argument("path", nargs="?", default=".")
    p.add_argument("--days", type=int, required=True)

    dashboard = subparsers.add_parser(
        "dashboard", help="serve the local read-only dashboard"
    )
    dashboard.add_argument("path", nargs="?", default=".")
    dashboard.add_argument("--host", default="127.0.0.1")
    dashboard.add_argument("--port", type=int, default=8765)
    dashboard.add_argument("--no-browser", action="store_true")
    dashboard.add_argument(
        "--allow-remote", action="store_true", help="allow non-local binding (unsafe)"
    )

    ab = subparsers.add_parser("eval-ab", help="run the task-level CKG A/B harness")
    ab.add_argument("--manifest", default="evaluation/tasks.json")
    ab.add_argument(
        "--condition", choices=("with_ckg", "without_ckg", "both"), default="both"
    )
    ab.add_argument("--output", default="results/")
    ab.add_argument("--dry-run", action="store_true")
    ab.add_argument("--agent-command")
    ab.add_argument(
        "--pilot",
        action="store_true",
        help="run exactly one Python and one JavaScript task",
    )
    ab.add_argument(
        "--preflight",
        action="store_true",
        help="validate paired CKG provisioning without launching an agent",
    )
    ab.add_argument(
        "--timeout",
        type=int,
        help="per-run timeout in seconds, overriding each task's manifest value",
    )

    return parser


def _require_dir(path: str) -> None:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"path '{path}' does not exist")
    if not p.is_dir():
        raise NotADirectoryError(f"path '{path}' is not a directory")


def main(argv: list[str] | None = None) -> int:  # pyright: ignore[reportGeneralTypeIssues]
    args = build_parser().parse_args(argv)

    try:
        # validate target paths before dispatch
        if (
            args.command in ("index", "watch")
            or args.command not in ("eval",)
            and hasattr(args, "path")
        ):
            _require_dir(args.path)

        if args.command == "eval-ab":
            from evaluation.ab_runner import main as ab_main

            return ab_main(
                [
                    "--manifest",
                    args.manifest,
                    "--condition",
                    args.condition,
                    "--output",
                    args.output,
                ]
                + (["--dry-run"] if args.dry_run else [])
                + (["--pilot"] if args.pilot else [])
                + (["--preflight"] if args.preflight else [])
                + (
                    ["--agent-command", args.agent_command]
                    if args.agent_command
                    else []
                )
                + (["--timeout", str(args.timeout)] if args.timeout else [])
            )

        if args.command == "doctor":
            return cmd_doctor(args.path, verbose=args.verbose)

        if args.command == "dashboard":
            if (
                args.host not in ("127.0.0.1", "localhost", "::1")
                and not args.allow_remote
            ):
                print(
                    "Refusing remote dashboard binding without --allow-remote",
                    file=sys.stderr,
                )
                return 1
            import webbrowser

            from ckg.dashboard.server import create_server

            server = create_server(args.path, args.host, args.port)
            print(
                f"CKG dashboard: http://{args.host}:{args.port}/ (local read-only; do not expose publicly)"
            )
            if not args.no_browser:
                webbrowser.open(f"http://{args.host}:{args.port}/")
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
            finally:
                server.server_close()
            return 0

        if args.command == "sessions":
            service = SessionService(args.path)
            command = args.sessions_command
            if command == "start":
                result = service.start()
            elif command == "list":
                result = service.list()
            elif command == "status":
                result = service.status(args.session_id)
            elif command == "timeline":
                result = service.timeline(args.session_id, args.limit)
            elif command == "recall":
                result = service.recall(args.query, args.limit)
            elif command == "export":
                output = service.export(args.session_id, args.format)
                print(output)
                return 0
            else:
                result = service.prune(args.days)
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "index":
            db_path = args.db or default_db_path(args.path)
            provider = None

            if args.embed:
                provider = _require_provider_or_explain()

            report = cmd_index(args.path, db_path, provider=provider)
            _print_index_report(report, db_path)
            if not args.no_background and not args.embed:
                _maybe_spawn_background_embed(db_path)
            return 0

        if args.command == "eval":
            provider = None

            if args.embed:
                provider = _require_provider_or_explain()

            _print_eval_report(cmd_eval(provider=provider, top_k=args.top_k))
            return 0

        if args.command == "init":
            try:
                results = cmd_init(args.path, agents=[args.agent])
            except (ValueError, OSError) as error:
                print(f"Could not configure MCP: {error}", file=sys.stderr)
                return 1

            for file_path, status in results.items():
                if status == "already configured":
                    print(f"already configured: {file_path}")
                else:
                    print(f"Wrote {file_path}")
            return 0

        if args.command == "uninstall":
            results = cmd_uninstall(args.path)
            for p, s in results.items():
                print(f"{s}: {p}")
            return 0

        db_path = args.db or default_db_path(args.path)

        if args.command == "watch":
            if args.no_embed:
                provider = None
            else:
                provider = _detect_provider()

            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            print(f"Watching {args.path} (index: {db_path})")
            cmd_watch(
                args.path,
                db_path,
                provider=provider,
                debounce_seconds=args.debounce,
                embed_limit=200,
            )
            return 0

        if not Path(db_path).exists():
            print(f"No index found at {db_path}. Run `ckg index {args.path}` first.")
            return 1

        if args.command == "embed":
            # cmd_embed will auto-detect; if no backend, it raises legible error
            report = cmd_embed(db_path, limit=args.limit)
            _print_embed_report(report)
        elif args.command == "status":
            _print_status(cmd_status(db_path), oneline=getattr(args, "oneline", False))
        elif args.command == "search":
            provider = resolve_provider(db_path, use_vector=not args.no_vector)
            if provider is None and not args.no_vector:
                # Legible failure when no backend at all
                try:
                    backend = _detect_provider()
                    if backend is None:
                        print(
                            "Vector search disabled: no embedding backend available. "
                            "Install with 'pip install code-knowledge-graph[local]' "
                            "or start Ollama at http://localhost:11434 (ollama pull nomic-embed-text).",
                            file=sys.stderr,
                        )
                    else:
                        qs = queue_status(db_path)
                        pending = (
                            qs.get("PENDING", 0)
                            + qs.get("FAILED", 0)
                            - qs.get("exhausted", 0)
                        )  # pyright: ignore[reportAttributeAccessIssue,reportOperatorIssue,reportIndexIssue]
                        if pending > 0:
                            print(
                                f"vector search inactive: {pending} chunks pending embedding — run `ckg embed`"
                            )
                except Exception:
                    pass
            _print_candidates(
                cmd_search(db_path, args.query, provider=provider, top_k=args.top_k)
            )
        elif args.command == "definition":
            _print_candidates(cmd_definition(db_path, args.name))
        elif args.command == "callers":
            _print_candidates(cmd_callers(db_path, args.name))
        elif args.command == "callees":
            _print_candidates(cmd_callees(db_path, args.name))
        elif args.command == "imports":
            _print_imports(cmd_imports(db_path, args.file))
        elif args.command == "context":
            provider = resolve_provider(db_path, use_vector=not args.no_vector)
            if provider is None and not args.no_vector:
                try:
                    backend = _detect_provider()
                    if backend is None:
                        print(
                            "Vector search disabled: no embedding backend available. "
                            "Install with 'pip install code-knowledge-graph[local]' "
                            "or start Ollama at http://localhost:11434 (ollama pull nomic-embed-text).",
                            file=sys.stderr,
                        )
                    else:
                        qs = queue_status(db_path)
                        pending = (
                            qs.get("PENDING", 0)
                            + qs.get("FAILED", 0)
                            - qs.get("exhausted", 0)
                        )  # pyright: ignore[reportAttributeAccessIssue,reportOperatorIssue,reportIndexIssue]
                        if pending > 0:
                            print(
                                f"vector search inactive: {pending} chunks pending embedding — run `ckg embed`"
                            )
                except Exception:
                    pass
            _print_context_pack(
                cmd_context(
                    db_path,
                    args.query,
                    token_budget=args.budget,
                    provider=provider,
                    top_k=args.top_k,
                )
            )

        return 0
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except NotADirectoryError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except sqlite3.Error as exc:
        db = locals().get("db_path", "index")
        print(
            f"Database error at {db}: {exc} — try removing the database and re-running `ckg index`.",
            file=sys.stderr,
        )
        return 1
    except ImportError as exc:
        print(f"Embeddings unavailable: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        if getattr(args, "embed", False) or args.command in ("embed", "eval"):
            print(f"Embeddings unavailable: {exc}", file=sys.stderr)
        else:
            print(f"Error: {exc}", file=sys.stderr)
        return 1
    except (ValueError, RuntimeError) as exc:
        if getattr(args, "embed", False) or args.command in ("embed", "eval"):
            print(f"Embeddings unavailable: {exc}", file=sys.stderr)
            return 1
        raise


if __name__ == "__main__":
    sys.exit(main())
