import Section from "./Section";
import CopyButton from "./CopyButton";
import { INSTALL, REPO_URL } from "../data/content";

export default function CTA() {
  const command = INSTALL.unix.join(" && ");

  return (
    <Section tone="ink">
      <h2 className="max-w-[30ch] font-mono text-3xl font-semibold leading-tight text-paper sm:text-4xl">
        Point it at a repo and see the graph it builds
      </h2>

      <div className="mt-8 max-w-xl border border-paper/20 bg-paper/5">
        <div className="flex items-center justify-between gap-4 px-4 py-3">
          <code className="block min-w-0 flex-1 whitespace-pre-wrap break-all font-mono text-[13px] text-paper">
            <span className="select-none text-paper/50">$ </span>
            {command}
          </code>
          <CopyButton text={command} className="text-paper/60 hover:bg-paper/10 hover:text-paper" />
        </div>
      </div>

      <a
        href={REPO_URL}
        target="_blank"
        rel="noreferrer"
        className="mt-6 inline-block font-mono text-sm text-paper/70 underline decoration-paper/25 underline-offset-4 hover:text-paper hover:decoration-paper/50"
      >
        Read the source
      </a>
    </Section>
  );
}
