import Section from "./Section";
import { PIPELINE } from "../data/content";

export default function Architecture() {
  return (
    <Section id="architecture" label="Architecture" wide>
      <h2 className="max-w-[40ch] font-mono text-3xl font-semibold leading-tight text-ink sm:text-4xl">
        What happens between a file on disk and an answer for your agent
      </h2>
      <p className="mt-4 max-w-[62ch] text-base leading-relaxed text-ink-soft">
        Six stages, in this order, every time you run <code className="rounded bg-paper-2 px-1.5 py-0.5 font-mono text-[13px]">ckg index</code>.
        Each one is a real module in the codebase, not a marketing abstraction.
      </p>

      <ol className="mt-12 flex flex-col">
        {PIPELINE.map((step, i) => (
          <li key={step.stage} className="relative flex gap-6 pb-10 last:pb-0">
            <div className="flex flex-col items-center">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-ink bg-paper font-mono text-sm text-ink">
                {i + 1}
              </span>
              {i < PIPELINE.length - 1 && (
                <span className="mt-1 w-px flex-1 bg-line" aria-hidden="true" />
              )}
            </div>
            <div className="min-w-0 pt-1">
              <h3 className="font-mono text-lg font-semibold text-ink">{step.stage}</h3>
              <p className="mt-2 max-w-[58ch] text-[15px] leading-relaxed text-ink-soft">
                {step.detail}
              </p>
              <p className="mt-2 font-mono text-xs text-ink-soft/70">{step.ref}</p>
            </div>
          </li>
        ))}
      </ol>

      <div className="mt-10 max-w-[62ch] border-l-2 border-blueprint pl-5">
        <p className="text-[15px] leading-relaxed text-ink-soft">
          The identity that makes this work is <span className="font-mono text-ink">stable_key</span> —
          every symbol keeps it across an edit, so step 5 (retrieve) can tell "this
          function moved" from "this function is new," and reindexing a large edit
          touches only what actually changed.
        </p>
      </div>
    </Section>
  );
}
