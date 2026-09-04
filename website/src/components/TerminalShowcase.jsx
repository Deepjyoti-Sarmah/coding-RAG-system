import { TERMINAL_STEPS } from "../data/content";

export default function TerminalShowcase() {
  return (
    <section className="relative overflow-hidden bg-blue px-6 pb-10 pt-2">
      {/* Hermes terminal is framed by a thick blue border with a blurred water-lily backdrop — we keep it high-contrast */}
      <div className="relative mx-auto max-w-[860px] border-[10px] border-blue-deep/35 bg-white/[0.04] p-2 sm:border-[14px] sm:p-3">
        <div className="overflow-hidden border border-white/20 bg-[#0f0f12] shadow-[0_12px_40px_rgba(0,0,0,0.35)]">
          <div className="flex items-center gap-2 border-b border-white/10 bg-white/[0.04] px-4 py-2.5">
            <span className="h-2.5 w-2.5 rounded-full bg-[#ff5f56]" />
            <span className="h-2.5 w-2.5 rounded-full bg-[#ffbd2e]" />
            <span className="h-2.5 w-2.5 rounded-full bg-[#27c93f]" />
            <span className="ml-2 font-mono text-[11px] font-normal tracking-[0.04em] text-white">Terminal — zsh</span>
            <span className="ml-auto hidden items-center gap-1.5 font-mono text-[10px] font-normal uppercase tracking-[0.14em] text-white/70 sm:flex">
              <span className="h-1.5 w-1.5 rounded-full bg-[#3ddc84] animate-pulse" /> live
            </span>
          </div>
          <div className="space-y-3.5 p-5 font-mono text-[13px] font-normal leading-[1.7]">
            {TERMINAL_STEPS.map((s, i) => (
              <div key={s.cmd}>
                <div className="flex flex-wrap items-baseline gap-2">
                  <span className="font-mono text-[12px] tracking-[-0.01em] text-white/60">~/repo %</span>
                  <span className="font-mono text-[13px] font-normal tracking-[-0.01em] text-white">{s.cmd}</span>
                  {i === TERMINAL_STEPS.length - 1 && <span className="caret text-white">▍</span>}
                </div>
                <div className="mt-1 flex items-center gap-1.5 text-white">
                  <span className="text-[#3ddc84]">✓</span>
                  <span className="font-mono text-[12px] font-normal tracking-[0.01em]">{s.out}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
      <p className="mt-3 text-center font-mono text-[11px] font-normal tracking-[0.04em] text-white">
        Three commands to a searchable graph — no API keys, no daemon.
      </p>
    </section>
  );
}
