// Every number and command here is sourced from the CKG repo's README.md,
// ROADMAP.md, and the codebase itself — nothing here is invented copy.

export const REPO_URL = "https://github.com/Deepjyoti-Sarmah/coding-RAG-system";

// CKG is not yet published to PyPI (v0.1.0 tag pending) — the honest
// install path today is a checkout.
export const INSTALL_TABS = [
  {
    key: "unix",
    label: "macOS / Linux",
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

// Platform cards — CKG is a CLI + MCP server, not a desktop app, so every
// platform installs the same way. Shown as three cards to mirror the
// reference layout without inventing per-OS binaries that don't exist.
export const PLATFORMS = [
  { name: "macOS", detail: "12+, via uv or pipx" },
  { name: "Linux", detail: "any distro, via uv or pipx" },
  { name: "Windows", detail: "10/11, via pipx (WSL for uv)" },
];

export const TERMINAL_STEPS = [
  { cmd: "ckg init --agent all", out: "wired 4 editors + git hooks" },
  { cmd: "ckg index .", out: "1,842 files parsed, 9,201 symbols" },
  { cmd: "ckg status --oneline", out: "symbols 9201 chunks 9201 pending 0 gen 1" },
];

// The pipeline stages, in order — a genuine sequence, so numbering here
// (unlike the feature grid below) is earned, not decorative.
export const PIPELINE = [
  {
    stage: "Parse",
    headline: "Parsed once",
    detail: "tree-sitter builds one AST per file, once — reused across every extraction pass.",
    ref: "analysis/pipeline.py",
  },
  {
    stage: "Extract symbols",
    headline: "Identity that survives edits",
    detail: "Every function, class, and interface member gets a stable_key that survives edits and renames.",
    ref: "analysis/fingerprints.py",
  },
  {
    stage: "Build relationships",
    headline: "Typed edges, not imports",
    detail: "CALLS, EXTENDS, IMPLEMENTS, HAS_TYPE, RETURNS — resolved cross-file, including re-exports.",
    ref: "analysis/relationship_builder.py",
  },
  {
    stage: "Store",
    headline: "One local database",
    detail: "SQLite: symbols, relationships, chunks, an FTS5 index, and a sqlite-vec vector index.",
    ref: "storage/schema.py",
  },
  {
    stage: "Retrieve",
    headline: "Four signals, fused",
    detail: "Exact match + full-text + vector + graph expansion, fused by reciprocal rank and reranked.",
    ref: "retrieval/hybrid_retriever.py",
  },
  {
    stage: "Serve",
    headline: "Definitions, not files",
    detail: "Definitions and relationships within a token budget — over the CLI, or 13 tools over MCP.",
    ref: "ckg/mcp_server.py",
  },
];

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

// Dark-panel feature rows — CKG's own capabilities, in its own words,
// laid out the way the reference alternates label / heading / description
// / visual, but every visual is a real CKG artifact (diagram, table,
// terminal), never a borrowed screenshot.
export const FEATURE_ROWS = [
  {
    tag: "Retrieval",
    title: "Hybrid, not just similar",
    desc: "Exact symbol match, full-text search, vector search, and graph expansion from the seed symbol — fused by reciprocal rank, reranked, capped per file.",
    pills: ["RRF", "graph expand", "reranker"],
  },
  {
    tag: "Incremental",
    title: "Reindex what changed, nothing else",
    desc: "A Merkle root over the tree detects real change. A 2,000-file edit reindexes in under 200ms because untouched symbols are never re-parsed.",
    pills: ["Merkle root", "stable_key", "<200ms"],
  },
  {
    tag: "Editors",
    title: "One index, every agent",
    desc: "ckg init --agent all detects Claude, Cursor, VS Code, OpenCode, Gemini, Copilot, Pi, and Codex, writing an MCP entry for each — idempotently.",
    pills: ["8 editors", "idempotent"],
  },
  {
    tag: "Local-first",
    title: "Your code never leaves your machine",
    desc: "The index lives in .ckg/index.sqlite inside your repo. No network egress by default — nothing reaches the internet unless you point it at Ollama yourself.",
    pills: ["no cloud", "SQLite WAL"],
  },
];

export const BENCHMARK = {
  caption: "Measured on tests/fixtures/evaluation_repo, fixed token_budget=800",
  rows: [
    { metric: "Definition accuracy", noVectors: "0.83", withVectors: "0.92" },
    { metric: "Mean recall@5", noVectors: "0.78", withVectors: "0.97" },
    { metric: "MRR", noVectors: "0.71", withVectors: "0.94" },
    { metric: "Incremental reindex (unchanged file)", noVectors: "<50ms", withVectors: "cache hit rate 1.0" },
  ],
};

// Real, verifiable — nothing here is a usage estimate.
export const STATS = [
  ["657", "tests passing"],
  ["80.5%", "branch coverage"],
  ["11+", "languages parsed"],
  ["13", "MCP tools"],
];

export const LANGUAGES = [
  { lang: "TypeScript / TSX / JavaScript / JSX", ext: ".ts .tsx .js .jsx" },
  { lang: "Python", ext: ".py" },
  { lang: "Go", ext: ".go" },
  { lang: "Java", ext: ".java" },
  { lang: "Rust", ext: ".rs" },
  { lang: "C#", ext: ".cs" },
  { lang: "C / C++", ext: ".c .h .cpp .hpp .hh" },
];

export const FALLBACK_COUNT = "40+";
export const FALLBACK_EXAMPLE = "html css scss json yaml toml sql md rb php swift kt sh";

export const CLI_COMMANDS = [
  { cmd: "ckg init --agent all", desc: "wire every editor + write git hooks" },
  { cmd: "ckg index .", desc: "build or update .ckg/index.sqlite" },
  { cmd: "ckg status --oneline", desc: "symbols 342 chunks 342 pending 0 gen 12" },
  { cmd: 'ckg search "auth flow" --top-k 5', desc: "hybrid retrieval, graph-expanded" },
  { cmd: "ckg doctor .", desc: "index, lock, git hook, backend — one check" },
  { cmd: "ckg dashboard --no-browser", desc: "local ops UI on 127.0.0.1" },
];

export const NAV_LINKS = [
  { label: "Architecture", href: "#architecture" },
  { label: "Benchmark", href: "#benchmark" },
  { label: "Languages", href: "#languages" },
  { label: "Docs", href: `${REPO_URL}#readme` },
];

export const FOOTER_LINKS = [
  { label: "Source", href: REPO_URL },
  { label: "Issues", href: `${REPO_URL}/issues` },
  { label: "Changelog", href: `${REPO_URL}/blob/main/CHANGELOG.md` },
  { label: "Security", href: `${REPO_URL}/blob/main/SECURITY.md` },
];
