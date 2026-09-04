import { CLI_COMMANDS } from "../data/content";

export default function CliReference() {
  return (
    <section className="bg-white px-6 py-8 sm:py-10">
      <div className="mx-auto max-w-[1280px]">
        <p className="font-mono text-[10px] font-normal uppercase tracking-[0.22em] text-blue">CLI</p>
        <h2 className="mt-2 font-display text-[22px] font-[300] uppercase leading-[0.95] tracking-[-0.02em] text-blue sm:text-[28px]">
          SIX COMMANDS COVER MOST OF IT
        </h2>

        <dl className="mt-6 overflow-hidden border border-blue bg-white">
          {CLI_COMMANDS.map((c) => (
            <div key={c.cmd} className="flex flex-col gap-1 border-b border-blue/15 px-4 py-3.5 last:border-0 sm:flex-row sm:items-baseline sm:gap-6">
              <dt className="shrink-0 font-mono text-[12px] font-normal tracking-[-0.01em] text-blue sm:w-[280px]">{c.cmd}</dt>
              <dd className="font-mono text-[11px] font-normal tracking-[0.02em] text-blue">{c.desc}</dd>
            </div>
          ))}
        </dl>
      </div>
    </section>
  );
}
