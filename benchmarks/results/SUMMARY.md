# External Benchmark Summary — Token/$ Savings (P5-4)

Pre-registered in `benchmarks/PREREGISTRATION.md` (repos, SHAs, recall gate
`>= 0.90`, buckets `<1k / 1k-4k / >4k`, budgets `800 / 1200 / 2000`).
Queries committed before the first run; every repo published whatever it
returned. Regenerate with the pinned commands below; verify with `--recompute`
(strict equality on stored precision/recall/RR).

Baseline is always `expected_files` content only
(`evaluation/external.py:196`), never whole-repo (refused at
`evaluation/runner.py:202`). Tokenizer `tiktoken o200k_base`
(`retrieval/tokenizer.py:14`), `len//4` fallback. Dollars are a projection:
input tokens only, `sonnet $2.00/1M` as of `2026-06-24`
(`retrieval/pricing.py`), rendered as formula, never a bare `$X`.

## Pooled headline — the citable number

**87.2% fewer context tokens across 60 queries on Django, Fiber and FastAPI,
at recall@10 0.95, budget 800.**

| | |
|---|---|
| Questions | 60 (20 per repo) |
| Baseline tokens | 382,064 |
| Context tokens | 48,925 |
| **Pooled aggregate** | **87.2%** |
| Mean recall@10 | 0.95 |
| Tokens saved / query | 5,552 |
| $/query (sonnet, input only) | $0.0111 |

Pooled over **individual questions** — every query's own `baseline_tokens` and
`context_tokens` summed, then one ratio. It is deliberately *not* the mean of
the three repos' percentages (that would be 86.3%), because averaging
percentages weights a repo with small files the same as one with large files.

Reproduce: `sg savings` (the `(pooled)` row) or `sg savings --json`. Pinned by
`tests/test_pricing.py::TestPooledClaim` so the published claim cannot drift
from the data. The self-repo run is excluded from the pool on purpose — it is
a sanity anchor on this codebase's own `retrieval/` package, not an
independent repository.

## Per repo (budget 800, aggregate only, recall-gated)

| Repo | Lang | Files | Aggregate | Recall@10 | p50 | $/query (sonnet) |
|---|---|---|---|---|---|---|
| Django | Python (large) | 20 qs | **90.9%** (8909 → 811) | 1.00 | 18.2ms | $0.0162 |
| Fiber | Go | 20 qs | **84.7%** (5272 → 804) | 0.95 | 9.3ms | $0.0089 |
| FastAPI | Python | 20 qs | **83.1%** (4923 → 831) | 0.90 | 3.8ms | $0.0082 |
| self (`retrieval/`) | Python | 11 qs | **16.7%** (1007 → 839) | 1.00 | 1.6ms | $0.0003 |

## Buckets @ 800 — the actual finding: savings scale with file size

| Repo | `<1k` | `1k-4k` | `>4k` |
|---|---|---|---|
| Django | +11.3% (n=1, R 1.00) | +65.8% (n=7, R 1.00) | **+93.9%** (n=12, R 1.00) |
| Fiber | −21.1% (n=2, R 1.00) | +53.3% (n=7, R 1.00) | **+90.4%** (n=11, R 0.91) |
| FastAPI | −293.3% (n=10, R 0.80) | +60.3% (n=4, R 1.00) | **+94.4%** (n=6, R 1.00) |
| self | −135.1% (n=8, R 1.00) | +69.5% (n=3, R 1.00) | no data |

The `>4k` bucket clears the pre-declared `~60%` falsifiability bar on all
three repos (90–94%). The `<1k` rows are negative and printed anyway — the
context pack's fixed structure (~800 tokens) costs more than a tiny file.
That is why the claim is segmented, not a single percentage.

## Budgets — aggregate falls as budget rises (monotonic, test-pinned)

| Repo | 800 | 1200 | 2000 |
|---|---|---|---|
| Django | 90.9% | 86.3% | 77.3% |
| Fiber | 84.7% | 77.1% | 61.9% |
| FastAPI | 83.1% | 74.8% | 58.2% |

## Why not the mean: FastAPI's mean-of-ratios is −1268% at the same run

FastAPI budget 800: `mean_savings_pct −1268.6%`, `aggregate +83.1%`
(budget 2000: mean −3281.7%, aggregate +58.2%). Ten tiny files where the
pack costs more than the file each count once under the mean; the aggregate
weights by token volume. Cite the aggregate. The mean is kept visible in
each result file for the same reason.

## Misses (recall < 1.0, published as-is)

* FastAPI (R@10 0.90, exactly at gate): "WebSocket routing…" and
  "serving static files…" miss at all budgets. `<1k` bucket recall 0.80.
* Fiber (R@10 0.95): "Ctx Params Query BodyParser…" misses (`ctx.go`
  outside top-10 files); `>4k` bucket recall 0.91.
* Django: 20/20 at all budgets.

## Provenance (every number grep-able in a tracked file)

| Result file | Repo | Commit | Queries |
|---|---|---|---|
| `benchmarks/results/fastapi.json` | `https://github.com/fastapi/fastapi` | `49033471594ea5d99a80abdf1043231b7791ee49` | `benchmarks/fastapi_original.json` |
| `benchmarks/results/django.json` | `https://github.com/django/django` | `3b767c5f6ab6a4421ea3892ac6afacd8aa1345d6` | `benchmarks/django_original.json` |
| `benchmarks/results/fiber.json` | `https://github.com/gofiber/fiber` | `e7229b1b3ead150398ad7c100a128c6f276f4b43` | `benchmarks/fiber_original.json` |
| `benchmarks/results/self_retrieval.json` | self | n/a | `benchmarks/self_queries.json` |

```bash
python benchmarks/run_external.py --repo <url> --source-dir <dir> \
  --queries <queries-file> --commit <sha> --budgets 800,1200,2000 \
  --output benchmarks/results/<name>.json
python benchmarks/run_external.py --recompute "benchmarks/results/*.json"
sg savings --json  # token/$ rows with model + price date
```
