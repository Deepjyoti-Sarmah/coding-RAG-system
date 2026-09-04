import { useState } from "react";
import CopyButton from "./CopyButton";
import ExampleGraph from "./ExampleGraph";
import { INSTALL } from "../data/content";

const TABS = [
  { key: "unix", label: "uv" },
  { key: "pipx", label: "pipx" },
];

export default function Hero() {
  const [tab, setTab] = useState("unix");
  const lines = INSTALL[tab];
  const command = lines.join(" && ");

  return (
    <section id="top" className="bg-paper px-6 pb-16 pt-14 md:pt-20">
      <div className="mx-auto grid max-w-[1100px] gap-12 md:grid-cols-[1fr_340px] md:items-start">
        <div>
          <p className="mb-6 font-mono text-sm text-ink-soft">
            Open source, MIT licensed
          </p>

          <h1 className="max-w-[16ch] font-mono text-[2.6rem] font-semibold leading-[1.08] text-balance text-ink sm:text-6xl">
            A symbol graph for your codebase, not a pile of text chunks
          </h1>

          <p className="mt-6 max-w-[58ch] text-lg leading-relaxed text-ink-soft">
            CKG parses your repository with tree-sitter, resolves every function,
            class, and relationship into a real graph, and serves it to your AI
            coding agent through MCP — so it reads definitions and callers
            instead of re-reading whole files. Runs entirely on your machine.
          </p>

          <div id="install" className="mt-9 max-w-xl scroll-mt-24">
            <div className="mb-0 flex gap-4 border-b border-line">
              {TABS.map((t) => (
                <button
                  key={t.key}
                  type="button"
                  onClick={() => setTab(t.key)}
                  className={`border-b-2 pb-2 font-mono text-sm transition ${
                    tab === t.key
                      ? "border-blueprint text-ink"
                      : "border-transparent text-ink-soft hover:text-ink"
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>
            <div className="border border-t-0 border-line bg-paper-2/60">
              {lines.map((line, i) => (
                <div
                  key={line}
                  className={`flex items-center justify-between gap-4 px-4 py-3 ${
                    i > 0 ? "border-t border-line/70" : ""
                  }`}
                >
                  <code className="block min-w-0 flex-1 whitespace-pre-wrap break-all font-mono text-[13px] text-ink">
                    <span className="select-none text-ink-soft">$ </span>
                    {line}
                  </code>
                  {i === lines.length - 1 && <CopyButton text={command} />}
                </div>
              ))}
            </div>
            <p className="mt-2 font-mono text-xs text-ink-soft/80">
              PyPI publish pending the v0.1.0 tag — installing from a checkout today.
            </p>
          </div>
        </div>

        <div className="flex flex-col gap-4 md:pt-2">
          <ExampleGraph />
          <a
            href="#architecture"
            className="font-mono text-sm text-blueprint underline decoration-blueprint/30 underline-offset-4 hover:decoration-blueprint"
          >
            See how the whole pipeline works
          </a>
        </div>
      </div>
    </section>
  );
}
