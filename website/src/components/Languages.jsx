import { LANGUAGES, FALLBACK_COUNT, FALLBACK_EXAMPLE } from "../data/content";

export default function Languages() {
  return (
    <section id="languages" className="scroll-mt-16 bg-paper px-6 py-20">
      <div className="mx-auto max-w-[1280px]">
        <p className="font-mono text-xs uppercase tracking-[0.25em] text-blue">Languages</p>
        <h2 className="mt-3 font-display text-3xl font-bold uppercase text-ink sm:text-4xl">
          AST-aware where it counts
        </h2>

        <div className="mt-10 grid gap-10 lg:grid-cols-2">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[380px] border-collapse text-sm">
              <thead>
                <tr className="border-b border-ink/15 text-left font-mono text-xs uppercase tracking-wider text-ink/50">
                  <th className="py-3 pr-4 font-medium">Language</th>
                  <th className="py-3 font-medium">Extensions</th>
                </tr>
              </thead>
              <tbody>
                {LANGUAGES.map((l) => (
                  <tr key={l.lang} className="border-b border-ink/10">
                    <td className="py-3 pr-4 text-ink/70">{l.lang}</td>
                    <td className="py-3 font-mono text-[13px] text-blue">{l.ext}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="rounded-sm bg-ink p-6">
            <p className="font-mono text-xs uppercase tracking-widest text-white/50">
              Fallback — {FALLBACK_COUNT} extensions
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              {FALLBACK_EXAMPLE.split(" ").map((f) => (
                <span key={f} className="rounded-sm border border-white/15 px-2.5 py-1 font-mono text-xs text-white/60">
                  .{f}
                </span>
              ))}
            </div>
            <p className="mt-5 text-sm leading-relaxed text-white/50">
              Everything in this list gets a module-level symbol and stays
              searchable through FTS and vector search. Nothing is silently skipped.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
