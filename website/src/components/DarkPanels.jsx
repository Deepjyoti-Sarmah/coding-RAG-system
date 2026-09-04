import { FEATURE_ROWS } from "../data/content";
import ExampleGraph from "./ExampleGraph";

const EDITORS = ["claude", "cursor", "vscode", "opencode", "gemini", "copilot", "pi", "codex"];

function IncrementalPanel() {
  return (
    <div className="flex min-h-[220px] w-full flex-col justify-center gap-2 border border-white bg-blue p-5 font-mono text-[11px] font-normal">
      <div className="mb-1 flex items-center justify-between text-[10px] uppercase tracking-[0.14em] text-white">
        <span>scenario</span>
        <span>result</span>
      </div>
      <div className="flex justify-between bg-white px-3 py-2.5">
        <span className="font-normal tracking-[0.02em] text-blue">full index</span>
        <span className="font-normal text-ink">1,842 files · 4.1s</span>
      </div>
      <div className="flex justify-between border border-white bg-white/15 px-3 py-2.5">
        <span className="text-white">edit 1 file</span>
        <span className="font-normal text-white">parsed=1 · 41ms</span>
      </div>
      <div className="flex justify-between border border-white bg-white/15 px-3 py-2.5">
        <span className="text-white">no changes</span>
        <span className="font-normal text-white">parsed=0 · &lt;50ms</span>
      </div>
      <p className="mt-1 text-center text-[10px] font-normal uppercase tracking-[0.14em] text-white">Merkle root · stable_key</p>
    </div>
  );
}

function EditorsPanel() {
  return (
    <div className="grid min-h-[220px] w-full grid-cols-2 gap-2 border border-white bg-blue p-4">
      {EDITORS.map((e) => (
        <div key={e} className="flex items-center gap-2 border border-white bg-white px-3 py-2.5">
          <span className="flex h-5 w-5 items-center justify-center bg-blue font-mono text-[10px] font-normal text-white">✓</span>
          <span className="font-mono text-[11px] font-normal capitalize tracking-[0.02em] text-blue">{e}</span>
        </div>
      ))}
      <div className="col-span-2 mt-1 text-center font-mono text-[10px] font-normal uppercase tracking-[0.14em] text-white">sg init --agent all · idempotent</div>
    </div>
  );
}

function LocalFirstPanel() {
  return (
    <div className="flex min-h-[220px] w-full flex-col items-center justify-center gap-3 border border-white bg-blue p-6">
      <div className="flex items-center gap-2 border border-white bg-white px-4 py-2 font-mono text-[11px] font-normal tracking-[0.04em] text-blue">
        <span className="h-2 w-2 bg-blue" /> your repo
      </div>
      <div className="flex flex-col items-center gap-1">
        <span className="h-6 w-px bg-white" />
        <span className="font-mono text-[10px] font-normal uppercase tracking-[0.14em] text-white">local write</span>
        <span className="h-6 w-px bg-white" />
      </div>
      <div className="border border-white bg-white px-4 py-2.5 font-mono text-[11px] font-normal tracking-[0.04em] text-blue">.sg/index.sqlite</div>
      <span className="font-mono text-[10px] font-normal uppercase tracking-[0.14em] text-white">no network egress</span>
    </div>
  );
}

const VISUALS = [ExampleGraph, IncrementalPanel, EditorsPanel, LocalFirstPanel];

export default function DarkPanels() {
  return (
    <section className="bg-ink px-6 py-10 sm:py-12">
      <div className="mx-auto flex max-w-[1280px] flex-col gap-10 sm:gap-12">
        {FEATURE_ROWS.map((row, i) => {
          const Visual = VISUALS[i % VISUALS.length];
          const reversed = i % 2 === 1;
          return (
            <div
              key={row.tag}
              className={`grid items-center gap-8 md:grid-cols-2 md:gap-10 ${reversed ? "md:[&>*:first-child]:order-2" : ""}`}
            >
              <div>
                <div className="flex items-center gap-2">
                  <span className="h-1.5 w-1.5 bg-white" />
                  <span className="font-mono text-[11px] font-normal uppercase tracking-[0.16em] text-white">{row.tag}</span>
                </div>
                <h3 className="mt-3 font-display text-[26px] font-[400] uppercase leading-[0.9] tracking-[-0.02em] text-white sm:text-[32px]">
                  {row.title.toUpperCase()}
                </h3>
                <p className="mt-3 max-w-[38ch] font-mono text-[12.5px] font-normal leading-[1.65] tracking-[0.02em] text-white">{row.desc}</p>
                <div className="mt-5 flex flex-wrap gap-1.5">
                  {row.pills.map((p) => (
                    <span
                      key={p}
                      className="border border-white px-2.5 py-1 font-mono text-[10px] font-normal uppercase tracking-[0.12em] text-white"
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
