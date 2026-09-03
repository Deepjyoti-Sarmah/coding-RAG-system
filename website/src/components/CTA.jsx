import CopyButton from "./CopyButton";
import { INSTALL_TABS, REPO_URL } from "../data/content";

export default function CTA() {
  const command = INSTALL_TABS[0].lines.join(" && ");

  return (
    <section className="relative overflow-hidden bg-blue px-6 py-28">
      <div
        className="line-burst pointer-events-none absolute left-1/2 top-0 h-[36rem] w-[60rem] -translate-x-1/2 -translate-y-1/3"
        style={{ "--burst-color": "rgba(255,255,255,0.14)" }}
      />

      <div className="relative mx-auto flex max-w-2xl flex-col items-center gap-8 text-center">
        <h2 className="font-display text-4xl font-bold uppercase leading-tight text-balance text-white sm:text-5xl">
          Point it at a repo and see the graph it builds
        </h2>
        <p className="max-w-md text-white/75">
          One index, every editor. Your code never leaves your machine.
        </p>

        <div className="flex w-full max-w-xl items-center justify-between gap-4 rounded-sm bg-white px-4 py-3">
          <code className="block min-w-0 flex-1 whitespace-pre-wrap break-all font-mono text-[13px] text-blue-deep">
            <span className="select-none text-blue-deep/50">$ </span>
            {command}
          </code>
          <CopyButton text={command} />
        </div>

        <a
          href={REPO_URL}
          target="_blank"
          rel="noreferrer"
          className="font-mono text-xs uppercase tracking-widest text-white/70 underline decoration-white/30 underline-offset-4 hover:text-white"
        >
          Read the source on GitHub
        </a>
      </div>
    </section>
  );
}
