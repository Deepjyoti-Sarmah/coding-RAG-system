import { INSTALL_TABS, REPO_URL } from "../data/content";
import CopyButton from "./CopyButton";
import { IndexTag, Shell, Ticks } from "./ui";
import { useState } from "react";

export default function Hero() {
  const [tab, setTab] = useState(INSTALL_TABS[0].key);
  const active = INSTALL_TABS.find((t) => t.key === tab) ?? INSTALL_TABS[0];
  const installText = active.lines.join("\n");

  return (
    <section id="top" className="relative overflow-hidden border-b border-white/25">
      {/* Engraved burst, offset right so it frames the diagram rather than
          sitting behind the headline where it would fight the text. */}
      <div
        className="line-burst pointer-events-none absolute -right-40 -top-60 hidden h-[900px] w-[900px] opacity-45 lg:block"
        style={{ "--burst-period": "5deg", "--burst-hole": "22%", "--burst-edge": "70%" }}
        aria-hidden="true"
      />

      <Shell className="relative grid gap-14 pt-16 pb-20 lg:grid-cols-[1.05fr_0.95fr] lg:gap-16 lg:pt-24 lg:pb-28">
        <div className="flex flex-col justify-center">
          <IndexTag>Open source · MIT · zero cloud egress</IndexTag>

          <h1 className="font-display mt-6 text-[clamp(2.5rem,4.6vw,4.25rem)] leading-[1.05] tracking-[-0.03em] text-white">
            The symbol graph
            <span className="block italic text-white/90">for your codebase</span>
          </h1>

          <p className="mt-7 max-w-xl text-[13px] leading-[1.7] text-white/85">
            symbolgraph parses a repository with tree-sitter, resolves every
            function, class and call into a local SQLite graph, and serves exact
            AST-aware context to your coding agent over MCP. Nothing is uploaded.
          </p>

          {/* Install block */}
          <div className="mt-9 max-w-xl border border-white/35 bg-ultra-deep">
            <div className="flex items-center justify-between border-b border-white/25">
              <div className="flex">
                {INSTALL_TABS.map((t) => (
                  <button
                    key={t.key}
                    type="button"
                    onClick={() => setTab(t.key)}
                    className={`tag-index border-r border-white/25 px-4 py-2.5 transition ${
                      t.key === tab ? "bg-white text-ultra" : "text-white/78 hover:text-white"
                    }`}
                  >
                    {t.label}
                  </button>
                ))}
              </div>
              <span className="tag-index px-4 text-white/70">install</span>
            </div>

            <div className="flex items-start justify-between gap-3 px-4 py-3.5">
              {/* The clone URL is longer than the column, so wrap it rather
                  than clipping — a truncated command is not a usable one. */}
              <pre className="min-w-0 flex-1 whitespace-pre-wrap break-words text-[12px] leading-[1.75] text-white/90">
                {active.lines.map((line) => (
                  <div key={line}>
                    <span className="select-none text-white/70">$ </span>
                    {line}
                  </div>
                ))}
              </pre>
              <CopyButton text={installText} className="text-white/70 hover:bg-white/10 hover:text-white" />
            </div>
          </div>

          <p className="tag-index mt-3 text-white/70">
            Not on PyPI yet — v0.1.0 publishes from a checkout
          </p>

          <div className="mt-8 flex flex-wrap gap-3">
            <a
              href={REPO_URL}
              target="_blank"
              rel="noreferrer"
              className="tag-index border border-white bg-white px-5 py-3 text-ultra transition hover:bg-ultra hover:text-white"
            >
              Read the source
            </a>
            <a
              href="#pipeline"
              className="tag-index border border-white/40 px-5 py-3 text-white transition hover:border-white hover:bg-white/10"
            >
              How it works
            </a>
          </div>
        </div>

        <HeroGraph />
      </Shell>
    </section>
  );
}

/* A real slice of this project's own test fixture (tests/fixtures/python_repo),
   verified against build_graph() output — not an invented diagram. The edges
   shown are the ones the extractor actually resolves:
     handle_request  CALLS    Authenticator
     handle_request  CALLS    create_session
     AdminAuthenticator EXTENDS Authenticator */
function HeroGraph() {
  return (
    <div className="relative flex items-center">
      <div className="relative w-full border border-white/35 bg-ultra-deep/70">
        <Ticks />

        <div className="flex items-center justify-between border-b border-white/25 px-4 py-2.5">
          <span className="tag-index text-white">graph resolver</span>
          <span className="tag-index text-white/70">.sg/index.sqlite</span>
        </div>

        <div className="engraved-grid p-5">
          <svg viewBox="0 0 380 260" className="h-auto w-full" role="img" aria-label="Symbol graph: handle_request calls Authenticator and create_session; AdminAuthenticator extends Authenticator">
            <defs>
              <marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
                <path d="M0 0 L10 5 L0 10 z" fill="rgba(255,255,255,0.75)" />
              </marker>
            </defs>

            {/* Edges first so nodes paint over their endpoints.
                fill="none" is mandatory: an open curved path without it is
                filled black by default and renders as a blob.
                Each edge must land on the node it actually names — an edge
                that stops short reads as a relationship that isn't there. */}
            <path d="M98 67 C 152 67, 168 104, 210 108" fill="none" stroke="rgba(255,255,255,0.55)" strokeWidth="1" markerEnd="url(#ar)" />
            <path d="M57 84 L57 180" fill="none" stroke="rgba(255,255,255,0.55)" strokeWidth="1" markerEnd="url(#ar)" />
            <path d="M264 156 L264 130" fill="none" stroke="rgba(255,255,255,0.55)" strokeWidth="1" markerEnd="url(#ar)" />

            <text x="140" y="80" className="fill-white/75" fontSize="8" fontFamily="JetBrains Mono" letterSpacing="1.2">CALLS</text>
            <text x="66" y="138" className="fill-white/75" fontSize="8" fontFamily="JetBrains Mono" letterSpacing="1.2">CALLS</text>
            <text x="272" y="147" className="fill-white/75" fontSize="8" fontFamily="JetBrains Mono" letterSpacing="1.2">EXTENDS</text>

            <GraphNode x={16} y={50} w={82} label="handle_request" kind="function" file="api.py" />
            <GraphNode x={214} y={92} w={96} label="Authenticator" kind="class" file="auth.py" solid />
            <GraphNode x={208} y={158} w={112} label="AdminAuthenticator" kind="class" file="admin.py" />
            <GraphNode x={16} y={184} w={92} label="create_session" kind="function" file="auth.py" />
          </svg>
        </div>

        <div className="flex items-center justify-between border-t border-white/25 px-4 py-2.5">
          <span className="tag-index text-white/70">2,026 symbols · 349 files</span>
          <span className="tag-index text-white/70">36,711 refs resolved</span>
        </div>
      </div>
    </div>
  );
}

function GraphNode({ x, y, w, label, kind, file, solid = false }) {
  return (
    <g>
      <rect
        x={x}
        y={y}
        width={w}
        height={34}
        fill={solid ? "#ffffff" : "rgba(0,0,138,0.85)"}
        stroke={solid ? "#ffffff" : "rgba(255,255,255,0.45)"}
        strokeWidth="1"
      />
      <text
        x={x + w / 2}
        y={y + 14}
        textAnchor="middle"
        fontSize="8.5"
        fontFamily="JetBrains Mono"
        fill={solid ? "#0000f2" : "#ffffff"}
      >
        {label}
      </text>
      <text
        x={x + w / 2}
        y={y + 25}
        textAnchor="middle"
        fontSize="6.5"
        fontFamily="JetBrains Mono"
        letterSpacing="0.6"
        fill={solid ? "rgba(0,0,242,0.6)" : "rgba(255,255,255,0.5)"}
      >
        {kind} · {file}
      </text>
    </g>
  );
}
