import { TERMINAL_STEPS } from "../data/content";
import { IndexTag, Shell, Ticks } from "./ui";

export default function TerminalShowcase() {
  return (
    <section className="border-b border-white/25 bg-ultra-navy">
      <Shell className="py-20">
        <div className="flex flex-wrap items-end justify-between gap-6">
          <div>
            <IndexTag>CLI runtime</IndexTag>
            <h2 className="font-display mt-4 text-[clamp(1.9rem,3.4vw,2.75rem)] leading-[1.15] text-white">
              What it prints on this repo
            </h2>
          </div>
          <span className="tag-index max-w-xs text-white/45">
            Real output · 381 files · not a mockup
          </span>
        </div>

        <div className="relative mt-12 border border-white/35 bg-ultra-deep">
          <Ticks />
          <div className="flex items-center justify-between border-b border-white/25 px-4 py-2.5">
            <div className="flex items-center gap-2.5">
              <span className="h-2.5 w-2.5 border border-white/45" />
              <span className="tag-index text-white/70">~/coding-RAG-system</span>
            </div>
            <span className="tag-index text-white/40">zsh</span>
          </div>

          <div className="overflow-x-auto p-6">
            <pre className="text-[12.5px] leading-[1.85] text-white/90">
              {TERMINAL_STEPS.map((s) => (
                <div key={s.cmd} className="mb-3 last:mb-0">
                  <div>
                    <span className="select-none text-white/40">~/repo $ </span>
                    <span className="text-white">{s.cmd}</span>
                  </div>
                  <div className="text-white/60">  {s.out}</div>
                </div>
              ))}
              <div className="mt-4 border-t border-white/20 pt-3 text-white/55">
                index complete · <span className="text-white">.sg/index.sqlite</span> · sqlite-vec active
              </div>
            </pre>
          </div>
        </div>
      </Shell>
    </section>
  );
}
