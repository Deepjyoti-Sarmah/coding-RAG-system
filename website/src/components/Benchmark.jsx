import Section from "./Section";
import { BENCHMARK } from "../data/content";

export default function Benchmark() {
  return (
    <Section id="benchmark" label="Benchmark">
      <h2 className="max-w-[36ch] font-mono text-3xl font-semibold leading-tight text-ink sm:text-4xl">
        Measured, not estimated
      </h2>
      <p className="mt-4 max-w-[62ch] text-base leading-relaxed text-ink-soft">
        {BENCHMARK.caption}. These four rows are every number this benchmark
        produces — reproducible with <code className="rounded bg-paper-2 px-1.5 py-0.5 font-mono text-[13px]">ckg eval --embed</code>.
      </p>

      <div className="mt-10 grid gap-10 sm:grid-cols-2">
        {BENCHMARK.stats.map(([n, label]) => (
          <div key={label} className="border-l-2 border-blueprint pl-4">
            <div className="font-mono text-3xl font-semibold text-ink">{n}</div>
            <div className="mt-1 text-sm text-ink-soft">{label}</div>
          </div>
        ))}
      </div>

      <div className="mt-10 overflow-x-auto">
        <table className="w-full min-w-[480px] border-collapse text-sm">
          <thead>
            <tr className="border-b border-line text-left font-mono text-xs text-ink-soft">
              <th className="py-2 pr-4 font-medium">Metric</th>
              <th className="py-2 pr-4 font-medium">FTS + graph</th>
              <th className="py-2 font-medium">+ vectors</th>
            </tr>
          </thead>
          <tbody>
            {BENCHMARK.rows.map((r) => (
              <tr key={r.metric} className="border-b border-line/60">
                <td className="py-3 pr-4 text-ink-soft">{r.metric}</td>
                <td className="py-3 pr-4 font-mono font-medium text-blueprint">{r.noVectors}</td>
                <td className="py-3 font-mono text-ink-soft">{r.withVectors}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="mt-6 max-w-[62ch] text-sm leading-relaxed text-ink-soft">
        A benchmark against real, larger repositories with original queries is
        planned next — see <code className="rounded bg-paper-2 px-1.5 py-0.5 font-mono text-[12px]">ROADMAP.md</code> in the repo.
      </p>
    </Section>
  );
}
