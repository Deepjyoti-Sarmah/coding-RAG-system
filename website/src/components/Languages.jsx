import { LANGUAGES, FALLBACK_COUNT, FALLBACK_EXAMPLE } from "../data/content";

export default function Languages() {
  return (
    <section id="languages" className="scroll-mt-16 bg-white px-6 py-8 sm:py-10">
      <div className="mx-auto max-w-[1280px]">
        <p className="font-mono text-[10px] font-normal uppercase tracking-[0.22em] text-blue">Languages</p>
        <h2 className="mt-2 font-display text-[26px] font-[300] uppercase leading-[0.95] tracking-[-0.02em] text-blue sm:text-[32px]">
          AST-AWARE WHERE IT COUNTS
        </h2>

        <div className="mt-6 grid gap-4 lg:grid-cols-2">
          <div className="overflow-x-auto border border-blue bg-white">
            <table className="w-full min-w-[380px] border-collapse">
              <thead>
                <tr className="border-b border-blue bg-blue text-left font-mono text-[11px] font-normal uppercase tracking-[0.14em] text-white">
                  <th className="py-3 pl-4 pr-4 font-normal">Language</th>
                  <th className="py-3 pr-4 font-normal">Extensions</th>
                </tr>
              </thead>
              <tbody>
                {LANGUAGES.map((l) => (
                  <tr key={l.lang} className="border-b border-blue/15 last:border-0">
                    <td className="py-3 pl-4 pr-4 font-mono text-[12px] font-normal tracking-[0.01em] text-blue">{l.lang}</td>
                    <td className="py-3 pr-4 font-mono text-[11px] font-normal tracking-[-0.01em] text-blue">{l.ext}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="border border-blue bg-blue p-6">
            <p className="font-mono text-[10px] font-normal uppercase tracking-[0.16em] text-white">
              Fallback — {FALLBACK_COUNT} extensions
            </p>
            <div className="mt-3 flex flex-wrap gap-1.5">
              {FALLBACK_EXAMPLE.split(" ").map((f) => (
                <span key={f} className="border border-white bg-white px-2.5 py-1 font-mono text-[11px] font-normal tracking-[0.02em] text-blue">
                  .{f}
                </span>
              ))}
            </div>
            <p className="mt-4 font-mono text-[11px] font-normal leading-[1.65] tracking-[0.02em] text-white">
              Everything here gets a module-level symbol and stays searchable through FTS and vector search. Nothing is silently skipped.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
