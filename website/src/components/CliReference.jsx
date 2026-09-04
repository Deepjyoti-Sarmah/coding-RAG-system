import Section from "./Section";
import { CLI_COMMANDS } from "../data/content";

export default function CliReference() {
  return (
    <Section label="CLI">
      <h2 className="max-w-[36ch] font-mono text-3xl font-semibold leading-tight text-ink sm:text-4xl">
        Six commands cover most of it
      </h2>

      <dl className="mt-8 flex flex-col divide-y divide-line/70 border-t border-line/70">
        {CLI_COMMANDS.map((c) => (
          <div key={c.cmd} className="flex flex-col gap-1 py-3 sm:flex-row sm:items-baseline sm:gap-6">
            <dt className="font-mono text-[13px] font-medium text-ink sm:w-[300px] sm:shrink-0">
              {c.cmd}
            </dt>
            <dd className="text-sm text-ink-soft">{c.desc}</dd>
          </div>
        ))}
      </dl>
    </Section>
  );
}
