#!/usr/bin/env python3
"""AGENT_CMD wrapper for evaluation/ab_runner.py's file-based real-agent
protocol.

ab_runner.py invokes this via `--agent-command` (shell=True) with the
protocol's env vars set: SG_AB_TASK_ID, SG_AB_CONDITION, SG_AB_WORKTREE,
SG_AB_PROMPT_FILE, SG_AB_RESULT_FILE, SG_AB_PROJECT, and — only when
condition == with_sg — SG_AB_MCP_CONFIG / SG_AB_INDEX.

It runs a real, non-interactive `claude -p` session in the task worktree,
with symbolgraph's MCP server wired in only for the with_sg condition, and
translates Claude Code's own `--output-format json` result into the
result.json shape ab_runner.py's parse_result() requires
(status/changed_files/files_found/symbols_found + token/tool metrics).
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path


def main() -> int:
    worktree = Path(os.environ["SG_AB_WORKTREE"])
    prompt_file = Path(os.environ["SG_AB_PROMPT_FILE"])
    result_file = Path(os.environ["SG_AB_RESULT_FILE"])
    condition = os.environ["SG_AB_CONDITION"]
    task_prompt = prompt_file.read_text(encoding="utf-8")

    instructions = (
        f"{task_prompt}\n\n"
        "You are in a read-only investigation task. Do not modify any files. "
        "Answer by stating: which file(s) contain the relevant code "
        "(as repo-relative paths), and which named function/method/class "
        "symbol(s) implement it. Be concise."
    )

    # stream-json (not the single-result "json" format) is needed to see
    # individual tool_use blocks — that's the only reliable way to count
    # real symbolgraph MCP tool invocations rather than guessing from the
    # final answer text.
    allowed_tools = ["Read", "Grep", "Glob"]
    cmd = [
        "claude", "-p", instructions,
        "--output-format", "stream-json", "--verbose",
        "--permission-mode", "acceptEdits",
    ]
    if condition == "with_sg":
        mcp_config = os.environ.get("SG_AB_MCP_CONFIG")
        if mcp_config:
            allowed_tools.append("mcp__symbolgraph")
            cmd += ["--mcp-config", mcp_config, "--strict-mcp-config"]
    cmd += ["--allowedTools", *allowed_tools]

    result: dict = {
        "status": "failure",
        "changed_files": [],
        "files_found": [],
        "symbols_found": [],
        "input_tokens": None,
        "output_tokens": None,
        "total_tokens": None,
        "tool_calls": None,
        "sg_tools_used": None,
        "sg_queries": None,
        "notes": "",
    }

    try:
        proc = subprocess.run(
            cmd, cwd=worktree, capture_output=True, text=True, timeout=170,
            check=False,
        )
    except subprocess.TimeoutExpired:
        result["notes"] = "claude -p timed out"
        result_file.write_text(json.dumps(result), encoding="utf-8")
        return 1

    # stream-json emits one JSON object per line: message events (with
    # tool_use content blocks) followed by a final result event carrying
    # usage totals and num_turns.
    final_payload = None
    tool_calls = 0
    sg_tools_used = 0
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "result":
            final_payload = event
        elif event.get("type") == "assistant":
            for block in (event.get("message", {}).get("content") or []):
                if block.get("type") == "tool_use":
                    tool_calls += 1
                    if str(block.get("name", "")).startswith("mcp__symbolgraph"):
                        sg_tools_used += 1

    if final_payload is None:
        result["notes"] = f"no result event: stdout={proc.stdout[-500:]!r} stderr={proc.stderr[:500]!r}"
        result_file.write_text(json.dumps(result), encoding="utf-8")
        return 1

    answer = final_payload.get("result", "") or ""
    usage = final_payload.get("usage", {}) or {}
    input_tokens = usage.get("input_tokens")
    output_tokens = usage.get("output_tokens")
    cache_read = usage.get("cache_read_input_tokens") or 0
    cache_creation = usage.get("cache_creation_input_tokens") or 0

    # Extract candidate repo-relative file paths and symbol-looking tokens
    # from the free-text answer. Heuristic, not exact — scoring in
    # ab_metrics.score() only requires the expected file/symbol to appear
    # somewhere in these lists.
    file_candidates = sorted(set(re.findall(r"[\w./-]+\.\w+", answer)))
    symbol_candidates = sorted(
        set(re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*(?:\(\))?\b", answer))
    )
    payload = final_payload

    result.update(
        status="success" if not payload.get("is_error") else "failure",
        files_found=file_candidates,
        symbols_found=symbol_candidates,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=(
            (input_tokens or 0) + (output_tokens or 0)
            + cache_read + cache_creation
        ) if input_tokens is not None or output_tokens is not None else None,
        tool_calls=tool_calls,
        sg_tools_used=sg_tools_used,
        notes=answer[:2000],
    )
    result_file.write_text(json.dumps(result), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
