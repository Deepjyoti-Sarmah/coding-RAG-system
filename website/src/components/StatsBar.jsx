import { STATS } from "../data/content";

export default function StatsBar() {
  return (
    <section id="benchmark" className="scroll-mt-16 border-t border-white bg-ink px-6 py-8 sm:py-10">
      <div className="mx-auto max-w-[1280px]">
        <p className="font-mono text-[10px] font-normal uppercase tracking-[0.22em] text-white">Measured, not estimated</p>
        <div className="mt-6 grid grid-cols-2 gap-x-6 gap-y-8 border-t border-white pt-6 sm:grid-cols-4">
          {STATS.map(([n, label]) => (
            <div key={label}>
              <div className="font-display text-[30px] font-[300] tracking-[-0.02em] text-white sm:text-[34px]">{n}</div>
              <div className="mt-1 font-mono text-[10px] font-normal uppercase tracking-[0.16em] text-white">
                {label}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
