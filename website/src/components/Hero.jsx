import { useState } from "react";
import CopyButton from "./CopyButton";
import { INSTALL_TABS } from "../data/content";

export default function Hero() {
  const [tab, setTab] = useState(INSTALL_TABS[0].key);
  const active = INSTALL_TABS.find((t) => t.key === tab);
  const command = active.lines.join(" && ");

  return (
    <section id="top" className="relative overflow-hidden bg-blue px-6 pb-20 pt-16 sm:pt-20">
      <div
        className="line-burst pointer-events-none absolute -right-32 -top-16 h-[42rem] w-[42rem]"
        style={{ "--burst-color": "rgba(255,255,255,0.16)" }}
      />

      <div className="relative mx-auto max-w-[1280px]">
        <p className="mb-5 font-mono text-xs uppercase tracking-[0.25em] text-white/70">
          Open source · MIT license
        </p>

        <h1 className="max-w-3xl font-display text-5xl font-bold uppercase leading-[1.02] text-balance text-white sm:text-6xl lg:text-7xl">
          A symbol graph
          <br />
          for your codebase
        </h1>

        <p className="mt-7 max-w-xl text-lg leading-relaxed text-white/80">
          CKG parses your repository with tree-sitter, resolves every function,
          class, and relationship into a real graph, and serves it to your AI
          coding agent through MCP — not text chunks. Runs entirely on your
          machine.
        </p>

        <div className="mt-10 flex flex-wrap items-center gap-3">
          <a
            href="#install"
            className="rounded-sm bg-white px-6 py-3 font-mono text-sm font-semibold uppercase tracking-widest text-blue-deep transition hover:bg-white/90"
          >
            Install via terminal
          </a>
          <a
            href="#architecture"
            className="rounded-sm border border-white/30 px-6 py-3 font-mono text-sm uppercase tracking-widest text-white/85 transition hover:border-white/60 hover:text-white"
          >
            See how it works
          </a>
        </div>

        <div id="install" className="mt-14 max-w-2xl scroll-mt-24">
          <p className="mb-3 font-mono text-xs uppercase tracking-widest text-white/60">
            Install via terminal
          </p>
          <div className="flex gap-1 font-mono text-xs">
            {INSTALL_TABS.map((t) => (
              <button
                key={t.key}
                type="button"
                onClick={() => setTab(t.key)}
                className={`rounded-t-sm px-3 py-2 uppercase tracking-wider transition ${
                  tab === t.key ? "bg-white text-blue-deep" : "text-white/55 hover:text-white/85"
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>
          <div className="rounded-b-sm rounded-tr-sm bg-white">
            {active.lines.map((line, i) => (
              <div
                key={line}
                className={`flex items-center justify-between gap-4 px-4 py-3 ${
                  i > 0 ? "border-t border-blue-deep/10" : ""
                }`}
              >
                <code className="block min-w-0 flex-1 whitespace-pre-wrap break-all font-mono text-[13px] text-blue-deep">
                  <span className="select-none text-blue-deep/50">$ </span>
                  {line}
                </code>
                {i === active.lines.length - 1 && <CopyButton text={command} />}
              </div>
            ))}
          </div>
          <p className="mt-3 font-mono text-xs text-white/55">
            PyPI publish pending the v0.1.0 tag — installing from a checkout today.
          </p>
        </div>
      </div>
    </section>
  );
}
