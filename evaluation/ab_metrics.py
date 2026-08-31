from __future__ import annotations

import json
import statistics


def _file_matches(expected: str, found_list: list[str]) -> bool:
    # Normalize: strip any "fastapi/" prefix that the agent might prepend
    def norm(p: str) -> str:
        return p.removeprefix("fastapi/")

    expected_n = norm(expected)
    for f in found_list:
        f_n = norm(f)
        if f_n == expected_n:
            return True
        if "/" not in expected_n:
            # expected is a basename — match only against basenames
            if "/" not in f_n and f_n == expected_n:
                return True
        else:
            # expected is a repo-relative path — match exact or trailing segment
            if f_n == expected_n or f_n.endswith("/" + expected_n):
                return True
    return False

def score(task, result):
    files_found = result.get("files_found") or []
    symbols_found = result.get("symbols_found") or []
    files_changed = result.get("files_changed") or []
    file_ok=all(_file_matches(x, files_found) for x in task["expected_files"])
    expected_changed=task.get("expected_changed_files", [])
    changed_ok=all(_file_matches(x, files_changed) for x in expected_changed)
    symbol_ok=all(x in symbols_found for x in task["expected_symbols"])
    result["success"]=bool(result.get("exit_code")==0 and file_ok and symbol_ok and changed_ok and not result.get("timed_out"))
    result["success_reason"]="; ".join(x for x,ok in (("process",result.get("exit_code")==0),("files_found",file_ok),("symbols",symbol_ok),("files_changed",changed_ok)) if not ok) or "criteria met"
    return result

def _stats(rows, key):
    vals=[r[key] for r in rows if isinstance(r.get(key),(int,float))]
    return {"mean":statistics.mean(vals) if vals else None,"median":statistics.median(vals) if vals else None}

def summarize(results):
    groups={"all":results}
    for r in results: groups.setdefault(r["language"],[]).append(r)
    out={}
    for name,rows in groups.items():
        out[name]={"runs":len(rows),"success_rate":sum(bool(r.get("success")) for r in rows)/len(rows) if rows else 0,"latency":_stats(rows,"elapsed_seconds"),"tokens":_stats(rows,"total_tokens"),"tool_calls":_stats(rows,"tool_calls"),"ckg_tools_used":_stats(rows,"ckg_tools_used")}
    pairs={}
    for r in results: pairs.setdefault(r["task_id"],{})[r["condition"]]=r
    diffs=[p["with_ckg"]["total_tokens"]-p["without_ckg"]["total_tokens"] for p in pairs.values() if "with_ckg" in p and "without_ckg" in p and all(isinstance(p[x].get("total_tokens"),(int,float)) for x in ("with_ckg","without_ckg"))]
    out["paired"]={"token_difference_mean":statistics.mean(diffs) if diffs else None,"pairs_with_tokens":len(diffs)}
    return out

def write_report(results, summary, path):
    lines=["# CKG task-level A/B evaluation","","Results are an instrumentation benchmark, not a productivity claim.","", "## Aggregate", "", "```json",json.dumps(summary,indent=2),"```", "", "## Tasks", "", "| Task | Condition | Success | Files found | Files changed | Symbols | CKG provisioned | CKG tools | Tokens | Tool calls | Latency |", "|---|---|---:|---|---|---|---:|---:|---:|---:|---:|"]
    lines += [f"| {r['task_id']} | {r['condition']} | {r.get('success')} | {r.get('files_found',[])} | {r.get('files_changed',[])} | {r.get('symbols_found',[])} | {bool((r.get('ckg_retrieval') or {}).get('enabled'))} | {r.get('ckg_tools_used')} | {r.get('total_tokens')} | {r.get('tool_calls')} | {r.get('elapsed_seconds')} |" for r in results]
    path.write_text("\n".join(lines)+"\n",encoding="utf-8")
