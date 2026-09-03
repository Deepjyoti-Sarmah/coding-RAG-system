import { BENCHMARK, TOKEN_SAVINGS } from "../data/content";

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

        <div className="mt-16 border-t border-ink/15 pt-10">
          <p className="font-mono text-xs uppercase tracking-[0.25em] text-blue">
            Token savings — measured, including the part that isn't flattering
          </p>
          <p className="mt-3 max-w-2xl text-ink/70">
            11 original queries, written by hand against this repo's own{" "}
            <code className="font-mono text-[0.9em] text-blue">retrieval/</code>{" "}
            package — not derived from any other project. Recall was{" "}
            <span className="font-mono font-semibold text-blue">{TOKEN_SAVINGS.recall}</span> ({TOKEN_SAVINGS.recallLabel}).
          </p>

          <div className="mt-8 grid gap-8 sm:grid-cols-2">
            <div className="border-l-2 border-blue pl-4">
              <div className="font-display text-3xl font-bold text-blue">{TOKEN_SAVINGS.aggregatePct}</div>
              <div className="mt-1 text-sm text-ink/60">
                tokens saved in aggregate — the number to cite, weighted by
                actual token volume
              </div>
            </div>
            <div className="border-l-2 border-ink/20 pl-4">
              <div className="font-display text-3xl font-bold text-ink/40 line-through decoration-2">
                {TOKEN_SAVINGS.meanPct}
              </div>
              <div className="mt-1 text-sm text-ink/60">
                naive mean of per-query ratios — misleading here, kept
                visible on purpose
              </div>
            </div>
          </div>

          <p className="mt-6 max-w-2xl text-sm leading-relaxed text-ink/60">
            On the two largest files ({TOKEN_SAVINGS.biggestWin.file}),{" "}
            {TOKEN_SAVINGS.biggestWin.detail}. {TOKEN_SAVINGS.caveat}
          </p>
          <p className="mt-4 text-sm text-ink/50">
            Full per-query breakdown:{" "}
            <code className="font-mono text-[0.9em]">benchmarks/results/self_retrieval.json</code>
          </p>
        </div>
      </div>
    </section>
  );
}
