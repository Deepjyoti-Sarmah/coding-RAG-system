from __future__ import annotations
import json, statistics

def score(task, result):
    files=" ".join(result.get("files_changed") or [])
    symbols=" ".join(result.get("symbols_found") or [])
    file_ok=all(x in files for x in task["expected_files"])
    symbol_ok=all(x in symbols for x in task["expected_symbols"])
    result["success"]=bool(result.get("exit_code")==0 and file_ok and symbol_ok and not result.get("timed_out"))
    result["success_reason"]="; ".join(x for x,ok in (("process",result.get("exit_code")==0),("files",file_ok),("symbols",symbol_ok)) if not ok) or "criteria met"
    return result

def _stats(rows, key):
    vals=[r[key] for r in rows if isinstance(r.get(key),(int,float))]
    return {"mean":statistics.mean(vals) if vals else None,"median":statistics.median(vals) if vals else None}

def summarize(results):
    groups={"all":results}
    for r in results: groups.setdefault(r["language"],[]).append(r)
    out={}
    for name,rows in groups.items():
        out[name]={"runs":len(rows),"success_rate":sum(bool(r.get("success")) for r in rows)/len(rows) if rows else 0,"latency":_stats(rows,"elapsed_seconds"),"tokens":_stats(rows,"total_tokens"),"tool_calls":_stats(rows,"tool_calls")}
    pairs={}
    for r in results: pairs.setdefault(r["task_id"],{})[r["condition"]]=r
    diffs=[p["with_ckg"]["total_tokens"]-p["without_ckg"]["total_tokens"] for p in pairs.values() if "with_ckg" in p and "without_ckg" in p and all(isinstance(p[x].get("total_tokens"),(int,float)) for x in ("with_ckg","without_ckg"))]
    out["paired"]={"token_difference_mean":statistics.mean(diffs) if diffs else None,"pairs_with_tokens":len(diffs)}
    return out

def write_report(results, summary, path):
    lines=["# CKG task-level A/B evaluation","","Results are an instrumentation benchmark, not a productivity claim.","", "## Aggregate", "", "```json",json.dumps(summary,indent=2),"```", "", "## Tasks", "", "| Task | Condition | Success | Tokens | Latency |", "|---|---|---:|---:|---:|"]
    lines += [f"| {r['task_id']} | {r['condition']} | {r.get('success')} | {r.get('total_tokens')} | {r.get('elapsed_seconds')} |" for r in results]
    path.write_text("\n".join(lines)+"\n",encoding="utf-8")
