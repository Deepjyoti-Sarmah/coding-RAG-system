import CopyButton from "./CopyButton";
import { INSTALL_TABS, REPO_URL } from "../data/content";

export default function CTA() {
  const command = INSTALL_TABS[0].lines.join(" && ");

  return (
    <section className="relative overflow-hidden bg-blue px-6 py-10 sm:py-12">
      <div
        className="line-burst pointer-events-none absolute left-1/2 top-0 h-[28rem] w-[48rem] -translate-x-1/2 -translate-y-1/3 opacity-90"
        style={{ "--burst-color": "rgba(255,255,255,0.95)" }}
      />

      <div className="relative mx-auto flex max-w-2xl flex-col items-center gap-5 text-center">
        <h2 className="max-w-[18ch] font-display text-[28px] font-[300] uppercase leading-[0.9] tracking-[-0.02em] text-white sm:text-[38px]">
          POINT IT AT A REPO AND SEE THE GRAPH IT BUILDS
        </h2>
        <p className="max-w-md font-mono text-[11px] font-normal leading-[1.6] tracking-[0.06em] text-white">
          One index, every editor. Your code never leaves your machine.
        </p>

        <div className="flex w-full max-w-[560px] items-center justify-between gap-3 bg-white px-4 py-3">
          <code className="block min-w-0 flex-1 whitespace-pre-wrap break-all font-mono text-[12px] font-normal leading-none tracking-[-0.01em] text-blue">
            <span className="select-none text-blue/40">$ </span>
            {command}
          </code>
          <CopyButton text={command} className="text-blue hover:bg-blue/10 hover:text-blue" />
        </div>

        <a
          href={REPO_URL}
          target="_blank"
          rel="noreferrer"
          className="border border-white bg-white px-4 py-2 font-mono text-[11px] font-normal uppercase tracking-[0.12em] text-blue transition hover:bg-white/90"
        >
          Read the source on GitHub
        </a>
      </div>
    </section>
  );
}
