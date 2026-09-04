# P5-4a Pre-registration — External Token/$ Benchmark

Committed **before** the first run. Git history proves the queries were not
tuned to the outcome. Running before this commit exists forfeits credibility
(see `ROADMAP.md` P5-4 execute order).

## Repo selection criterion (recorded before measuring)

Already pinned on disk (no clone drift), spanning Python / Python-large / Go —
the same language spread as the deleted third-party-derived table, chosen for
coverage of the spread, not for expected savings:

| # | Repo | Upstream URL | Pinned SHA | `source_dir` | Queries file |
|---|---|---|---|---|---|
| 1 | FastAPI | `https://github.com/fastapi/fastapi` | `49033471594ea5d99a80abdf1043231b7791ee49` | `fastapi` | `benchmarks/fastapi_original.json` |
| 2 | Django | `https://github.com/django/django` | `3b767c5f6ab6a4421ea3892ac6afacd8aa1345d6` | `django` | `benchmarks/django_original.json` |
| 3 | Fiber | `https://github.com/gofiber/fiber` | `e7229b1b3ead150398ad7c100a128c6f276f4b43` | `.` | `benchmarks/fiber_original.json` |

Local checkouts: `local_fastapi/fastapi`, `local_django/django`, `local_fiber/fiber`.
Runs use `--repo <url> --commit <sha>` so the recorded commit is what gets
cloned; the local dirs above are the code that was read to author queries.

## Query authorship rule

20 original `{query, expected_files, category}` per repo, written by reading
the code. File **names** were listed to confirm paths exist; file **sizes**
were not consulted while writing, and no other project's query list was
consulted (`P6-6`). Query files are committed in this same commit, before any
`run_external.py` invocation on these repos.

## Pre-declared gates and buckets

* **Recall gate:** a repo may headline only if `mean_recall_at_10 >= 0.90`.
  A repo failing the gate still gets its full row published — it is dropped
  from headlines only, never from the table.
* **Size buckets** by per-question `baseline_tokens`: `<1k`, `1k-4k`, `>4k`.
  The bucket table is the headline unit, not the whole-run mean. A bucket
  with no questions reports null, not `0.0`.
* **Budgets:** `800, 1200, 2000`. Context tokens must be non-decreasing and
  aggregate savings non-increasing across budgets (pinned by test).
* **Metric:** `aggregate_savings_pct` only (`1 - mean_ctx/mean_baseline`).
  `mean_savings_pct` is printed struck-through for the same reason as the
  self row. Baseline is always `expected_files` content
  (`evaluation/external.py:196`); whole-repo stays refused
  (`evaluation/runner.py:202`). Tokenizer `tiktoken o200k_base`
  (`retrieval/tokenizer.py:14`), `len//4` fallback.
* **Dollars:** projection, not measurement. Input tokens only in v1:
  `dollars = (mean_baseline - mean_context) * price_in / 1e6`, default model
  `sonnet`, price date printed with every figure (see `retrieval/pricing.py`).
  Always rendered as formula with inputs visible, never a bare `$X`.

## Falsifiability

If the `>4k` bucket does not clear roughly `60%` aggregate at budget 800,
the "savings scale with file size" story is wrong and the honest output is
the negative result, published as-is. If any repo falls below the recall
gate, its savings are reported without a headline.

## Publication rule

Every repo run gets published whatever it returns, in
`benchmarks/results/<name>.json` + `benchmarks/results/SUMMARY.md`, with
commit SHA and queries-file link per row. Every claim string carries:
aggregate% + recall@10 + p50 + budget + bucket + baseline definition +
commit SHA. No dollar figure without model + price + price date.
