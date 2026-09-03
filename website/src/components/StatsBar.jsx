import { STATS } from "../data/content";

export default function StatsBar() {
  return (
    <section id="benchmark" className="scroll-mt-16 border-t border-line-on-ink bg-ink px-6 py-16">
      <div className="mx-auto max-w-[1280px]">
        <h2 className="font-display text-3xl font-bold uppercase text-white sm:text-4xl">
          Measured, not estimated
        </h2>
        <div className="mt-10 grid grid-cols-2 gap-x-8 gap-y-10 border-t border-line-on-ink pt-10 sm:grid-cols-4">
          {STATS.map(([n, label]) => (
            <div key={label}>
              <div className="font-display text-4xl font-semibold italic text-white">{n}</div>
              <div className="mt-1 font-mono text-xs uppercase tracking-widest text-white/45">
                {label}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
