import { REPO_URL } from "../data/content";
import { Shell } from "./ui";

// The monumental footer plate from DESIGN.md: wall-to-wall display serif as the
// architectural foundation. "symbolgraph" is 11 characters, so it is sized to
// fill the viewport width rather than pinned to a fixed vw step that would
// overflow on narrow screens or strand whitespace on wide ones.
export default function BigWordmark() {
  return (
    <section className="relative overflow-hidden border-b border-white/25 bg-ultra">
      <Shell className="pt-24 pb-10">
        <div className="flex flex-wrap items-end justify-between gap-8">
          <div className="max-w-lg">
            <h2 className="font-display text-[clamp(1.75rem,3vw,2.5rem)] leading-[1.15] tracking-[-0.01em] text-white">
              Stop paying for context your agent throws away.
            </h2>
            <p className="mt-5 text-[12.5px] leading-[1.7] text-white/65">
              One local index. No account, no upload, no per-seat pricing —
              it is an MIT-licensed binary that reads your repo and answers
              questions about it.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <a
                href={REPO_URL}
                target="_blank"
                rel="noreferrer"
                className="tag-index border border-white bg-white px-5 py-3 text-ultra transition hover:bg-ultra hover:text-white"
              >
                Clone the repo
              </a>
              <a
                href={`${REPO_URL}#readme`}
                target="_blank"
                rel="noreferrer"
                className="tag-index border border-white/40 px-5 py-3 text-white transition hover:border-white hover:bg-white/10"
              >
                Read the docs
              </a>
            </div>
          </div>

          <dl className="grid grid-cols-2 gap-px bg-white/25 text-white sm:grid-cols-4 lg:w-auto">
            {[
              ["MIT", "licence"],
              ["0", "telemetry"],
              ["100%", "local"],
              ["v0.1.0", "tagged"],
            ].map(([v, k]) => (
              <div key={k} className="bg-ultra px-5 py-4">
                <dt className="font-display text-xl leading-none">{v}</dt>
                <dd className="tag-index mt-2 text-white/45">{k}</dd>
              </div>
            ))}
          </dl>
        </div>
      </Shell>

      <div
        aria-hidden="true"
        className="font-display select-none px-4 text-center text-[clamp(3rem,15.5vw,15rem)] leading-[0.9] tracking-[-0.045em] text-white"
      >
        symbolgraph
      </div>
    </section>
  );
}
