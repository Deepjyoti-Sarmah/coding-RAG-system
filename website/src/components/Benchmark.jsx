import { BENCHMARK } from "../data/content";

export default function Benchmark() {
  return (
    <section className="bg-paper px-6 py-20">
      <div className="mx-auto max-w-[1280px]">
        <p className="font-mono text-xs uppercase tracking-[0.25em] text-blue">Benchmark</p>
        <h2 className="mt-3 max-w-xl font-display text-3xl font-bold uppercase leading-tight text-ink sm:text-4xl">
          {BENCHMARK.caption}
        </h2>
        <p className="mt-3 max-w-lg text-ink/60">
          Every number below is reproducible with{" "}
          <code className="font-mono text-[0.9em] text-blue">ckg eval --embed</code>.
        </p>

        <div className="mt-10 overflow-x-auto">
          <table className="w-full min-w-[480px] border-collapse text-sm">
            <thead>
              <tr className="border-b border-ink/15 text-left font-mono text-xs uppercase tracking-wider text-ink/50">
                <th className="py-3 pr-4 font-medium">Metric</th>
                <th className="py-3 pr-4 font-medium">FTS + graph</th>
                <th className="py-3 font-medium">+ vectors</th>
              </tr>
            </thead>
            <tbody>
              {BENCHMARK.rows.map((r) => (
                <tr key={r.metric} className="border-b border-ink/10">
                  <td className="py-4 pr-4 text-ink/70">{r.metric}</td>
                  <td className="py-4 pr-4 font-mono font-semibold text-blue">{r.noVectors}</td>
                  <td className="py-4 font-mono text-ink/50">{r.withVectors}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <p className="mt-6 max-w-lg text-sm text-ink/50">
          A benchmark against real, larger repositories with original queries
          is planned next — see <code className="font-mono text-[0.9em]">ROADMAP.md</code> in the repo.
        </p>
      </div>
    </section>
  );
}
