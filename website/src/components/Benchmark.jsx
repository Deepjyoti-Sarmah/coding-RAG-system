import { BENCHMARK, TOKEN_SAVINGS } from "../data/content";

export default function Benchmark() {
  return (
    <section className="bg-white px-6 py-8 sm:py-10">
      <div className="mx-auto max-w-[1280px]">
        <p className="font-mono text-[10px] font-normal uppercase tracking-[0.22em] text-blue">Benchmark</p>
        {/* The caption ("Measured on tests/fixtures/... token_budget=800") used
            to be the headline, force-uppercased — a path with slashes and an
            underscore set in a Didone, wrapping to three lines. It reads as
            what it is: a caption. Demoted below a real headline. */}
        <h2 className="mt-2 max-w-xl font-display text-[34px] font-[400] uppercase leading-[0.95] tracking-[-0.02em] text-blue sm:text-[44px]">
          What it actually scores
        </h2>
        <p className="mt-3 max-w-[58ch] font-mono text-[12px] font-normal leading-[1.7] tracking-[0.01em] text-blue/80">
          {BENCHMARK.caption}. Every number below is reproducible with{" "}
          <code className="bg-blue px-1 py-0.5 font-mono text-[12px] font-normal tracking-[-0.01em] text-white">sg eval --embed</code>.
        </p>

        <div className="mt-6 overflow-x-auto border border-blue bg-white">
          <table className="w-full min-w-[480px] border-collapse">
            <thead>
              <tr className="border-b border-blue bg-blue text-left font-mono text-[11px] font-normal uppercase tracking-[0.14em] text-white">
                <th className="py-3 pl-4 pr-4 font-normal">Metric</th>
                <th className="py-3 pr-4 font-normal">FTS + graph</th>
                <th className="py-3 pr-4 font-normal">+ vectors</th>
              </tr>
            </thead>
            <tbody>
              {BENCHMARK.rows.map((r) => (
                <tr key={r.metric} className="border-b border-blue/15 last:border-0">
                  <td className="py-3.5 pl-4 pr-4 font-mono text-[12px] font-normal tracking-[0.01em] text-blue">{r.metric}</td>
                  <td className="py-3.5 pr-4 font-mono text-[12px] font-normal tracking-[-0.01em] text-blue">{r.noVectors}</td>
                  <td className="py-3.5 pr-4 font-mono text-[12px] font-normal tracking-[-0.01em] text-blue/60">{r.withVectors}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="mt-8 border border-blue bg-white p-6 sm:p-6">
          <p className="font-mono text-[10px] font-normal uppercase tracking-[0.2em] text-blue">
            Token savings — measured, including the part that isn't flattering
          </p>
          <p className="mt-2 max-w-[62ch] font-mono text-[12.5px] font-normal leading-[1.6] tracking-[0.02em] text-blue">
            11 original queries, written by hand against this repo's own{" "}
            <code className="bg-blue px-1 py-0.5 font-normal text-white">retrieval/</code>{" "}
            package. Recall was{" "}
            <span className="font-normal tracking-[-0.01em] text-blue">{TOKEN_SAVINGS.recall}</span> ({TOKEN_SAVINGS.recallLabel}).
          </p>

          <div className="mt-6 grid gap-4 sm:grid-cols-2">
            <div className="border border-blue bg-blue px-4 py-4">
              <div className="font-display text-2xl font-[400] tracking-[-0.02em] text-white">{TOKEN_SAVINGS.aggregatePct}</div>
              <div className="mt-1 font-mono text-[11px] font-normal leading-[1.5] tracking-[0.02em] text-white">
                tokens saved in aggregate — the number to cite, weighted by
                actual token volume
              </div>
            </div>
            <div className="border border-blue px-4 py-4">
              <div className="font-display text-2xl font-[400] tracking-[-0.02em] text-blue/30 line-through decoration-1">
                {TOKEN_SAVINGS.meanPct}
              </div>
              <div className="mt-1 font-mono text-[11px] font-normal leading-[1.5] tracking-[0.02em] text-blue">
                naive mean of per-query ratios — misleading here, kept
                visible on purpose
              </div>
            </div>
          </div>

          <p className="mt-5 max-w-[62ch] font-mono text-[12.5px] font-normal leading-[1.6] tracking-[0.02em] text-blue">
            On the two largest files ({TOKEN_SAVINGS.biggestWin.file}),{" "}
            {TOKEN_SAVINGS.biggestWin.detail}. {TOKEN_SAVINGS.caveat}
          </p>
          <p className="mt-3 font-mono text-[10px] font-normal tracking-[0.06em] text-blue/60">
            Full per-query breakdown: <span className="tracking-[-0.01em] text-blue">benchmarks/results/self_retrieval.json</span>
          </p>
        </div>
      </div>
    </section>
  );
}
