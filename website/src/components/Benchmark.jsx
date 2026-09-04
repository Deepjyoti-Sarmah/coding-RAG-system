import { BENCHMARK, STATS, TOKEN_SAVINGS } from "../data/content";
import { IndexTag, Shell } from "./ui";

export default function Benchmark() {
  return (
    <section id="benchmark" className="border-b border-white/25 bg-white text-ultra">
      <Shell className="py-24">
        <div className="flex flex-wrap items-end justify-between gap-6">
          <div>
            <IndexTag tone="on-white">Official benchmark</IndexTag>
            <h2 className="font-display mt-4 text-[clamp(2rem,4vw,3.25rem)] leading-[1.1] tracking-[-0.02em]">
              What it actually scores
            </h2>
          </div>
          <span className="tag-index border border-ultra/30 px-3 py-2 text-ultra/70">
            Reproduce · sg eval --embed
          </span>
        </div>

        {/* Stats */}
        <div className="hairline-matrix-blue mt-12 grid border border-ultra/25 grid-cols-2 lg:grid-cols-4">
          {STATS.map(([value, label]) => (
            <div key={label} className="bg-white px-6 py-8">
              <div className="font-display text-[2.75rem] leading-none tracking-[-0.02em]">{value}</div>
              <div className="tag-index mt-3 text-ultra/70">{label}</div>
            </div>
          ))}
        </div>

        {/* Retrieval quality on the fixture */}
        <div className="mt-16">
          <IndexTag n="A" tone="on-white">Retrieval quality</IndexTag>
          <p className="tag-index mt-3 text-ultra/65">{BENCHMARK.caption}</p>

          <div className="mt-5 overflow-x-auto border border-ultra/25">
            <table className="w-full min-w-[520px] border-collapse text-left">
              <thead>
                <tr className="border-b border-ultra/25 bg-ultra/5">
                  <th className="tag-index px-5 py-3 text-ultra/70">Metric</th>
                  <th className="tag-index px-5 py-3 text-ultra/70">FTS + graph</th>
                  <th className="tag-index px-5 py-3 text-ultra">+ vectors</th>
                </tr>
              </thead>
              <tbody>
                {BENCHMARK.rows.map((r) => (
                  <tr key={r.metric} className="border-b border-ultra/12 last:border-b-0">
                    <td className="px-5 py-3.5 text-[12.5px] text-ultra/75">{r.metric}</td>
                    <td className="px-5 py-3.5 text-[12.5px] text-ultra/70">{r.noVectors}</td>
                    <td className="px-5 py-3.5 text-[12.5px] font-medium text-ultra">{r.withVectors}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Token savings — segmented, including the rows that go negative */}
        <div className="mt-20">
          <IndexTag n="B" tone="on-white">Token savings</IndexTag>
          <h3 className="font-display mt-4 max-w-3xl text-[clamp(1.4rem,2.4vw,2rem)] leading-[1.25]">
            {TOKEN_SAVINGS.headline}
          </h3>
          <p className="mt-5 max-w-2xl text-[12.5px] leading-[1.7] text-ultra/70">
            {TOKEN_SAVINGS.explainer}
          </p>

          <div className="mt-8 overflow-x-auto border border-ultra/25">
            <table className="w-full min-w-[560px] border-collapse text-left">
              <thead>
                <tr className="border-b border-ultra/25 bg-ultra/5">
                  <th className="tag-index px-5 py-3 text-ultra/70">Baseline file size</th>
                  <th className="tag-index px-5 py-3 text-ultra/70">Django</th>
                  <th className="tag-index px-5 py-3 text-ultra/70">Fiber</th>
                  <th className="tag-index px-5 py-3 text-ultra/70">FastAPI</th>
                </tr>
              </thead>
              <tbody>
                {TOKEN_SAVINGS.buckets.map((b) => {
                  const strong = b.verdict === "strong";
                  const negative = b.verdict === "negative";
                  return (
                    <tr
                      key={b.bucket}
                      className={`border-b border-ultra/12 last:border-b-0 ${strong ? "bg-ultra text-white" : ""}`}
                    >
                      <td className={`px-5 py-3.5 text-[12.5px] ${strong ? "text-white" : "text-ultra/75"}`}>
                        {b.bucket}
                      </td>
                      {[b.django, b.fiber, b.fastapi].map((v, i) => (
                        <td
                          key={i}
                          className={`px-5 py-3.5 text-[12.5px] ${
                            strong ? "font-medium text-white" : negative ? "text-ultra/62" : "text-ultra/75"
                          }`}
                        >
                          {v}
                        </td>
                      ))}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <p className="tag-index mt-4 text-ultra/65">{TOKEN_SAVINGS.gate}</p>

          {/* Per-repo aggregates */}
          <div className="hairline-matrix-blue mt-10 grid border border-ultra/25 sm:grid-cols-3">
            {TOKEN_SAVINGS.repos.map((r) => (
              <div key={r.name} className="bg-white p-6">
                <div className="flex items-baseline justify-between">
                  <span className="font-display text-xl">{r.name}</span>
                  <span className="tag-index text-ultra/62">{r.lang}</span>
                </div>
                <div className="font-display mt-4 text-[2.25rem] leading-none">{r.aggregatePct}</div>
                <dl className="mt-5 flex flex-col gap-2 text-[11.5px] text-ultra/72">
                  <Row k="tokens" v={r.baseline} />
                  <Row k="recall@10" v={r.recall} />
                  <Row k="p50" v={r.p50} />
                  <Row k="$/query" v={r.dollarsPerQuery} />
                </dl>
              </div>
            ))}
          </div>

          <p className="tag-index mt-5 text-ultra/62">
            Pre-registered · queries and repo SHAs committed before the first run · {TOKEN_SAVINGS.dollarsNote}
          </p>
        </div>
      </Shell>
    </section>
  );
}

function Row({ k, v }) {
  return (
    <div className="flex items-baseline justify-between gap-3 border-t border-ultra/12 pt-2 first:border-t-0 first:pt-0">
      <dt className="tag-index text-ultra/62">{k}</dt>
      <dd className="text-ultra/80">{v}</dd>
    </div>
  );
}
