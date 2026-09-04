import Section from "./Section";

const ITEMS = [
  {
    term: "Local-first",
    detail:
      "The index lives in .ckg/index.sqlite inside your repo. Nothing leaves your machine unless you point it at an Ollama endpoint yourself.",
  },
  {
    term: "Incremental",
    detail:
      "A Merkle root over the tree detects what changed. Reindexing a 2,000-file edit takes under 200ms because untouched symbols are never re-parsed.",
  },
  {
    term: "Multi-editor",
    detail:
      "ckg init --agent all detects Claude, Cursor, VS Code, OpenCode, Gemini, Copilot, Pi, and Codex, and writes an MCP entry for each — idempotently.",
  },
  {
    term: "Ops",
    detail:
      "A local dashboard (HMAC auth, CSRF checks) for index status and reindex, plus ckg doctor — one command that checks the index, the lock, the git hook, and the embedding backend.",
  },
];

export default function Capabilities() {
  return (
    <Section label="Also">
      <dl className="flex flex-col gap-8">
        {ITEMS.map((item) => (
          <div key={item.term} className="grid gap-1 sm:grid-cols-[160px_1fr] sm:gap-6">
            <dt className="font-mono text-[15px] font-medium text-ink">{item.term}</dt>
            <dd className="max-w-[56ch] text-[15px] leading-relaxed text-ink-soft">
              {item.detail}
            </dd>
          </div>
        ))}
      </dl>
    </Section>
  );
}
