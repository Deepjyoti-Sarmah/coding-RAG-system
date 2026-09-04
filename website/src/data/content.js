// Every number and command here is sourced from the CKG repo's README.md,
// ROADMAP.md, and the codebase itself — nothing here is invented copy.

export const REPO_URL = "https://github.com/Deepjyoti-Sarmah/coding-RAG-system";

// CKG is not yet published to PyPI (v0.1.0 tag pending) — the honest
// install path today is a checkout. Swap for `pip install
// code-knowledge-graph` once the tag ships.
export const INSTALL = {
  unix: [
    "git clone https://github.com/Deepjyoti-Sarmah/coding-RAG-system",
    "cd coding-RAG-system && uv tool install .",
  ],
  pipx: [
    "git clone https://github.com/Deepjyoti-Sarmah/coding-RAG-system",
    "cd coding-RAG-system && pipx install .",
  ],
};

// The pipeline stages, in order — this genuinely is a sequence, so a
// stepped layout is the honest structure, not decoration.
export const PIPELINE = [
  {
    stage: "Parse",
    detail:
      "tree-sitter builds one AST per file, once. The tree is kept in memory and reused across every extraction pass — parsing twice is a bug, not a feature.",
    ref: "analysis/pipeline.py",
  },
  {
    stage: "Extract symbols",
    detail:
      "Each function, class, and interface member gets a stable_key derived from its structural position — the same symbol keeps its identity across edits and renames.",
    ref: "analysis/fingerprints.py",
  },
  {
    stage: "Build relationships",
    detail:
      "CALLS, EXTENDS, IMPLEMENTS, HAS_TYPE, and RETURNS edges connect symbols, including cross-file resolution through re-exports and member paths.",
    ref: "analysis/relationship_builder.py",
  },
  {
    stage: "Store",
    detail:
      "Everything lands in SQLite — symbols, relationships, and semantic chunks, plus an FTS5 index and a sqlite-vec vector index (numpy fallback where the extension can't load).",
    ref: "storage/schema.py",
  },
  {
    stage: "Retrieve",
    detail:
      "A query fans out to exact match, full-text search, vector search, and graph expansion from the seed symbol. Results are fused by reciprocal rank and reranked.",
    ref: "retrieval/hybrid_retriever.py",
  },
  {
    stage: "Serve",
    detail:
      "The result is handed to an agent as definitions and relationships within a token budget — over the CLI directly, or as one of 13 tools over MCP.",
    ref: "ckg/mcp_server.py",
  },
];

// The graph fragment shown in the hero — this is the codebase's own
// canonical fixture example (tests/test_reranker.py, tests/test_cli.py,
// tests/fixtures/evaluation_repo), not invented sample data.
export const EXAMPLE_GRAPH = {
  file: "auth.ts",
  nodes: [
    { id: "login", kind: "function", x: 40, y: 30 },
    { id: "createAuth", kind: "function", x: 220, y: 30 },
    { id: "logout", kind: "function", x: 220, y: 110 },
    { id: "run", kind: "function", x: 40, y: 110, file: "api.ts" },
  ],
  edges: [
    { from: "login", to: "createAuth", kind: "CALLS" },
    { from: "run", to: "login", kind: "CALLS" },
  ],
};

export const BENCHMARK = {
  caption: "Measured on tests/fixtures/evaluation_repo, fixed token_budget=800",
  rows: [
    { metric: "Definition accuracy", noVectors: "0.83", withVectors: "0.92" },
    { metric: "Mean recall@5", noVectors: "0.78", withVectors: "0.97" },
    { metric: "MRR", noVectors: "0.71", withVectors: "0.94" },
    { metric: "Incremental reindex (unchanged file)", noVectors: "<50ms", withVectors: "cache hit rate 1.0" },
  ],
  stats: [
    ["657", "tests passing"],
    ["80.5%", "branch coverage"],
    ["11+", "languages parsed"],
    ["13", "MCP tools"],
  ],
};

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
