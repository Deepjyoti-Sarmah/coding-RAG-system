# Security Policy

symbolgraph indexes source trees — including, potentially, files containing
secrets or personal data — onto the local disk. Its threat model and
what it deliberately does and doesn't do are below.

## Supported versions

| Version | Supported |
|---|---|
| 0.1.x | :white_check_mark: |

Pre-1.0: only the latest `0.1.x` release gets security fixes.

## Reporting a vulnerability

**Do not open a public GitHub issue for a security vulnerability.**

Use GitHub's private vulnerability reporting instead:
`https://github.com/Deepjyoti-Sarmah/coding-RAG-system/security/advisories/new`

Include what you'd include in any report: affected version, a
reproduction, and the impact as you see it. Expect an initial response
within a few days; there is no funded security team behind this project,
so treat that as a target, not an SLA.

## What symbolgraph deliberately does

- **No network egress by default.** Indexing, retrieval, and the MCP
  server run entirely against the local `.sg/index.sqlite`. The only
  opt-in network calls are to a locally-configured Ollama endpoint
  (`sg embed`, auto-detected at `http://localhost:11434`) — nothing
  reaches the public internet unless you point it there yourself.
- **Secrets and PII are redacted before they're stored.** `indexing/secrets.py`
  runs 15+ regexes (incl. Luhn-validated card numbers) plus a
  `GENERIC_CREDENTIAL` heuristic over file contents before indexing;
  `.env`-shaped and known-secret filenames are skipped outright.
  Session-memory recall (`session_memory/service.py`) redacts the same
  way. This is regex-based pattern matching, not a guarantee — it
  catches common shapes, not every secret format.
- **The dashboard requires auth.** `sg dashboard` checks an HMAC bearer
  token (`SG_DASHBOARD_TOKEN`) and a `Sec-Fetch-Site` CSRF check on
  every request; it binds to `127.0.0.1` only.
- **The index stays in `.sg/`.** Nothing is written outside the target
  repository's own directory tree (plus editor config files `sg init`
  is explicitly asked to write, e.g. `.mcp.json`).

## What symbolgraph does not do

- It does not phone home, collect telemetry, or report usage anywhere.
- It does not execute code from the repository it indexes — parsing is
  tree-sitter (a parser, not an interpreter) end to end.
- It does not guarantee secret redaction is complete. Don't index a
  repository you wouldn't otherwise let a local tool read.
