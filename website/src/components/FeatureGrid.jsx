import { PIPELINE } from "../data/content";

function StageMark({ index }) {
  // A generated abstract mark per stage — not a borrowed illustration.
  const angle = (index * 47) % 360;
  return (
    <div className="relative aspect-[4/3] w-full overflow-hidden rounded-sm bg-blue">
      <div
        className="line-burst absolute -inset-1/4"
        style={{ "--burst-color": "rgba(255,255,255,0.5)", transform: `rotate(${angle}deg)` }}
      />
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="font-display text-6xl font-semibold italic text-white/90">{index + 1}</span>
      </div>
    </div>
  );
}

export default function FeatureGrid() {
  return (
    <section id="architecture" className="scroll-mt-16 bg-paper px-6 py-24">
      <div className="mx-auto max-w-[1280px]">
        <p className="font-mono text-xs uppercase tracking-[0.25em] text-blue">
          Architecture — six stages, in order
        </p>
        <h2 className="mt-3 max-w-2xl font-display text-4xl font-bold uppercase leading-tight text-ink sm:text-5xl">
          What happens between a file on disk and an answer for your agent
        </h2>
        <p className="mt-4 max-w-xl text-ink/65">
          Every one of these is a real module in the codebase, run in this
          order, every time <code className="font-mono text-[0.85em] text-blue">ckg index</code> runs.
        </p>

        <div className="mt-14 grid gap-x-10 gap-y-16 sm:grid-cols-2 lg:grid-cols-3">
          {PIPELINE.map((step, i) => (
            <div key={step.stage}>
              <p className="font-mono text-xs uppercase tracking-widest text-blue">
                #{i + 1} {step.stage}
              </p>
              <h3 className="mt-2 font-display text-2xl font-bold leading-snug text-ink">
                {step.headline}
              </h3>
              <div className="mt-5">
                <StageMark index={i} />
              </div>
              <p className="mt-5 text-[15px] leading-relaxed text-ink/70">{step.detail}</p>
              <p className="mt-2 font-mono text-xs text-ink/40">{step.ref}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
