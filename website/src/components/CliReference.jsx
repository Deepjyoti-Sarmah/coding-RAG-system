import { CLI_COMMANDS } from "../data/content";

export default function CliReference() {
  return (
    <section className="bg-paper px-6 py-20">
      <div className="mx-auto max-w-[1280px]">
        <p className="font-mono text-xs uppercase tracking-[0.25em] text-blue">CLI</p>
        <h2 className="mt-3 font-display text-3xl font-bold uppercase text-ink sm:text-4xl">
          Six commands cover most of it
        </h2>

        <dl className="mt-10 flex flex-col divide-y divide-ink/10 border-t border-ink/15">
          {CLI_COMMANDS.map((c) => (
            <div key={c.cmd} className="flex flex-col gap-1 py-4 sm:flex-row sm:items-baseline sm:gap-8">
              <dt className="font-mono text-sm font-medium text-ink sm:w-[320px] sm:shrink-0">{c.cmd}</dt>
              <dd className="text-sm text-ink/60">{c.desc}</dd>
            </div>
          ))}
        </dl>
      </div>
    </section>
  );
}
