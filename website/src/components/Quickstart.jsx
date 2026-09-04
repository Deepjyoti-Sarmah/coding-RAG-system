import { PLATFORMS, QUICKSTART } from "../data/content";
import CopyButton from "./CopyButton";
import { IndexTag, Shell } from "./ui";

export default function Quickstart() {
  return (
    <section className="border-b border-white/25 bg-ultra-deep">
      <Shell className="py-20">
        <div className="flex flex-wrap items-end justify-between gap-6">
          <div>
            <IndexTag n="00">Quickstart</IndexTag>
            <h2 className="font-display mt-4 text-[clamp(1.9rem,3.4vw,2.75rem)] leading-[1.15] tracking-[-0.01em] text-white">
              Indexed and wired in three commands
            </h2>
          </div>
          <p className="tag-index max-w-xs text-white/45">
            Same three on every platform — there is no per-OS binary to pick
          </p>
        </div>

        <div className="hairline-matrix mt-12 grid border border-white/25 sm:grid-cols-3">
          {QUICKSTART.map((step) => (
            <div key={step.n} className="flex flex-col gap-4 bg-ultra-deep p-6">
              <IndexTag n={step.n}>{step.cmd.split(" ")[1] ?? "run"}</IndexTag>

              <div className="flex items-center justify-between gap-2 border border-white/25 bg-ultra-navy px-3 py-2.5">
                <code className="overflow-x-auto text-[12.5px] text-white">
                  <span className="select-none text-white/40">$ </span>
                  {step.cmd}
                </code>
                <CopyButton text={step.cmd} className="text-white/50 hover:bg-white/10 hover:text-white" />
              </div>

              <p className="text-[12.5px] leading-[1.65] text-white/65">{step.desc}</p>
            </div>
          ))}
        </div>

        {/* Platform strip — same install everywhere, so this is a note, not
            three big cards pretending to be different downloads. */}
        <div className="hairline-matrix mt-px grid border border-white/25 border-t-0 sm:grid-cols-3">
          {PLATFORMS.map((p) => (
            <div key={p.name} className="flex items-baseline justify-between gap-3 bg-ultra-deep px-6 py-4">
              <span className="font-display text-lg text-white">{p.name}</span>
              <span className="tag-index text-right text-white/45">{p.tag}</span>
            </div>
          ))}
        </div>
      </Shell>
    </section>
  );
}
