// Every number and command here is sourced from the symbolgraph repo itself —
// re-measured, not copied forward. Last verified 2026-09-05:
//   uv run pytest -q --cov          -> 677 passed, 80.68% branch coverage
//   grep -c "@mcp.tool()" symbolgraph/mcp_server.py -> 15
//   len(analysis.languages._PROFILES)               -> 11
//   len(symbolgraph.editors.EDITORS)                -> 8
// Nothing here is invented copy.

export const REPO_URL = "https://github.com/Deepjyoti-Sarmah/coding-RAG-system";

// v0.1.0 is tagged, but the package is not on PyPI yet — a `uv tool install
// symbolgraph` line here would be a lie today, so the install path stays a
// checkout until the release actually publishes.
export const INSTALL_TABS = [
  {
    key: "uv",
    label: "uv",
    lines: [
      "git clone https://github.com/Deepjyoti-Sarmah/coding-RAG-system",
      "cd coding-RAG-system && uv tool install .",
    ],
  },
  {
    key: "pipx",
    label: "pipx",
    lines: [
      "git clone https://github.com/Deepjyoti-Sarmah/coding-RAG-system",
      "cd coding-RAG-system && pipx install .",
    ],
  },
];

// The genuine 60-second path: install, point it at a repo, wire the agent.
export const QUICKSTART = [
  {
    n: "01",
    cmd: "sg index .",
    desc: "Parse the repo into .sg/index.sqlite — symbols, typed edges, FTS5 and vectors.",
  },
  {
    n: "02",
    cmd: "sg init --agent all",
    desc: "Detect every installed agent and write its MCP entry. Idempotent — safe to re-run.",
  },
  {
    n: "03",
    cmd: 'sg search "auth flow"',
    desc: "Confirm retrieval works from the CLI before an agent ever asks.",
  },
];

// symbolgraph is a CLI + MCP server, not a desktop app, so every platform
// installs the same way. Three cards mirror the reference layout without
// inventing per-OS binaries that do not exist.
export const PLATFORMS = [
  { name: "macOS", tag: "12+ · Apple silicon & Intel", detail: "uv or pipx · zero config" },
  { name: "Linux", tag: "any distro · glibc or musl", detail: "uv or pipx · zero config" },
  { name: "Windows", tag: "10 / 11 · native or WSL", detail: "pipx native · uv under WSL" },
];

// Real output from running these against this repository, not illustrative
// filler: 394 files parsed, 2,065 symbols, 36,504 resolved references
// (re-measured 2026-09-05).
export const TERMINAL_STEPS = [
  { cmd: "sg init --agent all", out: "Wrote .mcp.json · .cursor · .vscode · +5 more" },
  { cmd: "sg index .", out: "394 files parsed · 36,504 references resolved" },
  { cmd: "sg status --oneline", out: "symbols 2065 · chunks 2065 · pending 0 · gen 1" },
];

// The pipeline stages, in order — a genuine sequence, so the numbering here
// is earned rather than decorative.
export const PIPELINE = [
  {
    n: "01",
    stage: "Parse",
    headline: "Parsed once",
    detail:
      "tree-sitter builds one AST per file, once — reused by every extraction pass instead of re-parsed per feature.",
    ref: "analysis/pipeline.py",
  },
  {
    n: "02",
    stage: "Identify",
    headline: "Survives edits",
    detail:
      "Every function, class and interface member gets a stable_key that survives edits, moves and renames.",
    ref: "analysis/fingerprints.py",
  },
  {
    n: "03",
    stage: "Relate",
    headline: "Typed edges",
    detail:
      "CALLS, EXTENDS, IMPLEMENTS, HAS_TYPE, RETURNS — resolved across files, including re-exports.",
    ref: "analysis/relationship_builder.py",
  },
  {
    n: "04",
    stage: "Store",
    headline: "One local database",
    detail:
      "One SQLite file: symbols, relationships, chunks, an FTS5 index and a sqlite-vec vector index.",
    ref: "storage/schema.py",
  },
  {
    n: "05",
    stage: "Retrieve",
    headline: "Four signals, fused",
    detail:
      "Exact match, full-text, vector and graph expansion — fused by reciprocal rank, then reranked.",
    ref: "retrieval/hybrid_retriever.py",
  },
  {
    n: "06",
    stage: "Serve",
    headline: "Definitions, not files",
    detail:
      "Definitions and their relationships inside a token budget — over the CLI, or 15 tools over MCP.",
    ref: "symbolgraph/mcp_server.py",
  },
];

// The core thesis. This is the argument the whole project rests on, so it
// gets a section rather than a bullet.
export const THESIS = {
  tag: "The premise",
  headline: "Why a symbol, not a chunk",
  body: "Chunk-based retrieval splits code on token counts, so it hands an agent the middle of a function and calls it context. A symbol graph splits on what the language actually defines — so a result is a whole definition, and its callers and callees come with it.",
  columns: [
    {
      label: "Chunked retrieval",
      points: [
        "Splits on token windows, blind to syntax",
        "A match can be half a function body",
        "Callers and callees are a separate search",
        "Re-embeds the file on every edit",
      ],
    },
    {
      label: "symbolgraph",
      points: [
        "Splits on definitions tree-sitter proves exist",
        "A result is always a complete definition",
        "Typed edges arrive with the result",
        "Merkle root skips files that did not change",
      ],
    },
  ],
};

// The codebase's own canonical test fixture — real product data, not
// invented sample content.
export const EXAMPLE_GRAPH = {
  nodes: [
    { id: "login", x: 30, y: 24 },
    { id: "createAuth", x: 210, y: 24 },
    { id: "logout", x: 210, y: 104 },
    { id: "run", x: 30, y: 104 },
  ],
  edges: [
    { from: "login", to: "createAuth" },
    { from: "run", to: "login" },
  ],
};

// The 15 tools an agent actually sees over MCP, grouped by what they do.
// Sourced from the @mcp.tool() definitions in symbolgraph/mcp_server.py.
export const MCP_TOOLS = [
  {
    group: "Index",
    tools: [
      { name: "index_repository", args: "path, embed", desc: "Build or refresh the index" },
      { name: "repository_status", args: "path", desc: "Generation, counts, pending work" },
    ],
  },
  {
    group: "Navigate",
    tools: [
      { name: "definition", args: "name, path", desc: "Where a symbol is defined" },
      { name: "callers", args: "name, path", desc: "What calls it" },
      { name: "callees", args: "name, path", desc: "What it calls" },
      { name: "imports", args: "file, path", desc: "What a file imports" },
    ],
  },
  {
    group: "Retrieve",
    tools: [
      { name: "search", args: "query, path, top_k", desc: "Hybrid search, graph-expanded" },
      { name: "context", args: "query, path, token_budget", desc: "A context pack under budget" },
    ],
  },
  {
    group: "Session memory",
    tools: [
      { name: "session_start", args: "path", desc: "Open a working session" },
      { name: "session_end", args: "path, session_id", desc: "Close it" },
      { name: "session_status", args: "path, session_id", desc: "What is open now" },
      { name: "session_recall", args: "path, query, limit", desc: "Recall earlier context" },
      { name: "session_timeline", args: "path, session_id", desc: "What happened, in order" },
      { name: "record_decision", args: "path, decision, reason", desc: "Persist a decision" },
      { name: "record_code_area", args: "path, file_path", desc: "Mark an area as relevant" },
    ],
  },
];

// Feature rows — symbolgraph's own capabilities, in its own words.
export const FEATURE_ROWS = [
  {
    tag: "Retrieval",
    title: "Hybrid, not just similar",
    desc: "Exact symbol match, full-text search, vector search and graph expansion from the seed symbol — fused by reciprocal rank, reranked, capped per file.",
    pills: ["RRF fusion", "graph expand", "reranker"],
  },
  {
    // Re-timed 2026-09-05: a true no-change reindex of this 396-file repo is
    // 0.54s wall clock with `parsed files: 0`. The older "~5.7s" note here was
    // measured on a run that still had parsing to do, and the "<200ms for a
    // 2,000-file edit" line before that never survived measurement at all.
    tag: "Incremental",
    title: "Reindex what changed, nothing else",
    desc: "A Merkle root over the tree detects real change, so untouched files are never re-parsed — a no-change reindex of this repo is 0.54s with 0 files parsed and 396 unchanged.",
    pills: ["Merkle root", "stable_key", "0.54s · 0 parsed"],
  },
  {
    tag: "Editors",
    title: "One index, every agent",
    desc: "sg init --agent all detects Claude, Cursor, VS Code, OpenCode, Gemini, Copilot, Pi and Codex, writing an MCP entry for each — idempotently.",
    pills: ["8 agents", "idempotent"],
  },
  {
    tag: "Local-first",
    title: "Your code never leaves your machine",
    desc: "The index lives in .sg/index.sqlite inside your repo. No network egress by default — nothing reaches the internet unless you point it at Ollama yourself.",
    pills: ["no cloud", "SQLite WAL"],
  },
];

export const BENCHMARK = {
  caption: "Measured on tests/fixtures/evaluation_repo, fixed token_budget=800",
  rows: [
    { metric: "Definition accuracy", noVectors: "0.83", withVectors: "0.92" },
    { metric: "Mean recall@5", noVectors: "0.78", withVectors: "0.97" },
    { metric: "MRR", noVectors: "0.71", withVectors: "0.94" },
    { metric: "Incremental reindex (unchanged)", noVectors: "<50ms", withVectors: "cache hit rate 1.0" },
  ],
};

// Real token-savings measurements: pre-registered external runs
// (benchmarks/PREREGISTRATION.md — repos, SHAs and 20 original queries each
// committed to git BEFORE the first run, so the history itself proves no
// post-hoc tuning). Full data: benchmarks/results/*.json.
export const TOKEN_SAVINGS = {
  // The pooled headline. Verify with `sg savings` (the "(pooled)" row) —
  // pooled over all 60 individual questions, not an average of the three
  // repos' percentages (that would be 86.3%). Pinned by
  // tests/test_pricing.py::TestPooledClaim so it cannot drift from the data.
  pooled: {
    pct: "87%",
    queries: "60 queries",
    repos: "Django · Fiber · FastAPI",
    recall: "0.95",
    tokens: "382,064 → 48,925",
    perQuery: "5,552 tokens",
    dollars: "$0.011",
    // Scope matters: this is retrieval context size, not an agent's total cost
    // to finish a task. The end-to-end claim would need paired agent runs.
    scope: "Measured on retrieved context, not end-to-end agent cost.",
  },
  headline: "Savings scale with file size — so the claim is segmented, not averaged",
  explainer:
    "A context pack has a fixed structure that costs roughly 800 tokens. On a file smaller than that, packing it costs more than sending it, and the saving goes negative. Those rows are printed rather than dropped — a single blended percentage would hide them.",
  gate: "Every repo shown cleared a pre-declared recall@10 gate of 0.90. Budget 800.",
  dollarsNote: "Input tokens only, sonnet $2.00/1M as of 2026-06-24",
  buckets: [
    { bucket: ">4k tokens", django: "+93.9%", fiber: "+90.4%", fastapi: "+94.4%", verdict: "strong" },
    { bucket: "1k–4k", django: "+65.8%", fiber: "+53.3%", fastapi: "+60.3%", verdict: "good" },
    { bucket: "<1k", django: "+11.3%", fiber: "−21.1%", fastapi: "−293.3%", verdict: "negative" },
  ],
  repos: [
    {
      name: "Django",
      lang: "Python",
      queries: "20 queries",
      recall: "1.00",
      p50: "18.2ms",
      baseline: "8,909 → 811",
      aggregatePct: "+90.9%",
      dollarsPerQuery: "$0.0162",
    },
    {
      name: "Fiber",
      lang: "Go",
      queries: "20 queries",
      recall: "0.95",
      p50: "9.3ms",
      baseline: "5,272 → 804",
      aggregatePct: "+84.7%",
      dollarsPerQuery: "$0.0089",
    },
    {
      name: "FastAPI",
      lang: "Python",
      queries: "20 queries",
      recall: "0.90",
      p50: "3.8ms",
      baseline: "4,923 → 831",
      aggregatePct: "+83.1%",
      dollarsPerQuery: "$0.0082",
    },
  ],
};

// Re-measured 2026-09-05. Verifiable by running the commands in the comment
// at the top of this file — nothing here is an estimate.
export const STATS = [
  ["677", "tests passing"],
  ["80.68%", "branch coverage"],
  ["11", "language profiles"],
  ["15", "MCP tools"],
];

export const LANGUAGES = [
  { lang: "TypeScript", ext: ".ts .tsx" },
  { lang: "JavaScript", ext: ".js .jsx" },
  { lang: "Python", ext: ".py" },
  { lang: "Go", ext: ".go" },
  { lang: "Rust", ext: ".rs" },
  { lang: "Java", ext: ".java" },
  { lang: "C#", ext: ".cs" },
  { lang: "C / C++", ext: ".c .h .cpp .hpp" },
];

export const EDITORS = [
  "Claude Code",
  "Cursor",
  "VS Code",
  "OpenCode",
  "Gemini",
  "Copilot",
  "Pi",
  "Codex",
];

export const FALLBACK_COUNT = "26";
export const FALLBACK_EXAMPLE = "html css scss less json yaml toml xml sql graphql proto tf hcl dockerfile md rb php swift kt sh vue svelte";

export const CLI_COMMANDS = [
  { cmd: "sg init --agent all", desc: "wire every agent + write git hooks" },
  { cmd: "sg index .", desc: "build or update .sg/index.sqlite" },
  { cmd: "sg status --oneline", desc: "generation, symbol and chunk counts" },
  { cmd: 'sg search "auth flow" --top-k 5', desc: "hybrid retrieval, graph-expanded" },
  { cmd: "sg context <query> --budget 800", desc: "a token-budgeted context pack" },
  { cmd: "sg callers <symbol>", desc: "who calls this, resolved cross-file" },
  { cmd: "sg doctor .", desc: "index, lock, git hook, backend — one check" },
  { cmd: "sg dashboard --no-browser", desc: "local ops UI on 127.0.0.1" },
];

export const NAV_LINKS = [
  { label: "Pipeline", href: "#pipeline" },
  { label: "Benchmark", href: "#benchmark" },
  { label: "MCP", href: "#mcp" },
  { label: "Languages", href: "#languages" },
];

export const FOOTER_LINKS = [
  { label: "Source", href: REPO_URL },
  { label: "Issues", href: `${REPO_URL}/issues` },
  { label: "Changelog", href: `${REPO_URL}/blob/main/CHANGELOG.md` },
  { label: "Security", href: `${REPO_URL}/blob/main/SECURITY.md` },
];
