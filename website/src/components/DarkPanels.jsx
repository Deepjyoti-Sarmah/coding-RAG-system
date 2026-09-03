import { FEATURE_ROWS } from "../data/content";
import ExampleGraph from "./ExampleGraph";

const EDITORS = ["claude", "cursor", "vscode", "opencode", "gemini", "copilot", "pi", "codex"];

function IncrementalPanel() {
  return (
    <div className="flex min-h-[220px] w-full flex-col justify-center gap-3 rounded-sm bg-panel border border-white/10 p-6 font-mono text-sm">
      <div className="flex justify-between text-white/40">
        <span>full index</span>
        <span className="text-white/70">1,842 files · 4.1s</span>
      </div>
      <div className="h-px bg-white/10" />
      <div className="flex justify-between text-white/40">
        <span>edit 1 file, reindex</span>
        <span className="text-[#8f8fff]">parsed_files=1 · 41ms</span>
      </div>
      <div className="flex justify-between text-white/40">
        <span>no changes, reindex</span>
        <span className="text-[#8f8fff]">parsed_files=0 · &lt;50ms</span>
      </div>
    </div>
  );
}

function EditorsPanel() {
  return (
    <div className="flex min-h-[220px] w-full flex-col justify-center gap-2 rounded-sm bg-panel border border-white/10 p-6 font-mono text-sm">
      {EDITORS.map((e) => (
        <div key={e} className="flex items-center gap-2 text-white/70">
          <span className="text-[#8f8fff]">✓</span> {e}
        </div>
      ))}
    </div>
  );
}

function LocalFirstPanel() {
  return (
    <div className="flex min-h-[220px] w-full flex-col items-center justify-center gap-4 rounded-sm bg-panel border border-white/10 p-6 font-mono text-sm text-white/70">
      <div className="rounded-sm border border-white/20 px-4 py-2">your repo</div>
      <span className="text-white/30">↓</span>
      <div className="rounded-sm border border-[#8f8fff]/50 px-4 py-2 text-[#8f8fff]">.ckg/index.sqlite</div>
      <span className="mt-2 text-xs text-white/30">no network egress by default</span>
    </div>
  );
}

const VISUALS = [ExampleGraph, IncrementalPanel, EditorsPanel, LocalFirstPanel];

export default function DarkPanels() {
  return (
    <section className="bg-ink px-6 py-20">
      <div className="mx-auto flex max-w-[1280px] flex-col gap-16">
        {FEATURE_ROWS.map((row, i) => {
          const Visual = VISUALS[i % VISUALS.length];
          const reversed = i % 2 === 1;
          return (
            <div
              key={row.tag}
              className={`grid items-center gap-10 md:grid-cols-2 ${reversed ? "md:[&>*:first-child]:order-2" : ""}`}
            >
              <div>
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 bg-[#8f8fff]" />
                  <span className="font-mono text-xs uppercase tracking-widest text-white/50">{row.tag}</span>
                </div>
                <h3 className="mt-4 font-display text-3xl font-bold leading-tight text-white sm:text-4xl">
                  {row.title}
                </h3>
                <p className="mt-4 max-w-md text-white/60">{row.desc}</p>
                <div className="mt-6 flex flex-wrap gap-2">
                  {row.pills.map((p) => (
                    <span
                      key={p}
                      className="rounded-sm border border-white/15 px-2.5 py-1 font-mono text-[11px] uppercase tracking-wider text-white/50"
                    >
                      {p}
                    </span>
                  ))}
                </div>
              </div>
              <Visual />
            </div>
          );
        })}
      </div>
    </section>
  );
}
