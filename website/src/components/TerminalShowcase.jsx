import { TERMINAL_STEPS } from "../data/content";

export default function TerminalShowcase() {
  return (
    <section className="relative overflow-hidden bg-blue px-6 pb-24 pt-4">
      <div
        className="line-burst pointer-events-none absolute right-10 top-0 h-64 w-64"
        style={{ "--burst-color": "rgba(255,255,255,0.18)" }}
      />

      <div
        className="relative mx-auto max-w-4xl overflow-hidden rounded-md border border-white/15 p-1"
        style={{
          background:
            "radial-gradient(circle at 30% 20%, rgba(255,255,255,0.14), transparent 55%), radial-gradient(circle at 80% 80%, rgba(255,255,255,0.10), transparent 50%), var(--color-blue-deep)",
        }}
      >
        <div className="rounded-[3px] bg-ink/90 backdrop-blur-sm">
          <div className="flex items-center gap-2 border-b border-white/10 px-4 py-3">
            <span className="h-3 w-3 rounded-full bg-[#ff5f56]" />
            <span className="h-3 w-3 rounded-full bg-[#ffbd2e]" />
            <span className="h-3 w-3 rounded-full bg-[#27c93f]" />
            <span className="ml-3 font-mono text-xs text-white/40">zsh — ckg</span>
          </div>
          <div className="space-y-4 p-6 font-mono text-sm">
            {TERMINAL_STEPS.map((s, i) => (
              <div key={s.cmd}>
                <div className="flex flex-wrap items-baseline gap-2">
                  <span className="text-white/40">~/repo %</span>
                  <span className="text-white">{s.cmd}</span>
                  {i === TERMINAL_STEPS.length - 1 && <span className="caret text-white">▍</span>}
                </div>
                <div className="mt-1 flex items-center gap-2 text-white/55">
                  <span className="text-[#3ddc84]">✓</span>
                  {s.out}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
