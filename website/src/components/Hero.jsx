import { useState } from "react";
import CopyButton from "./CopyButton";
import { INSTALL_TABS } from "../data/content";

function HeroArt() {
  // One burst, not four. Its centre is masked out (see .line-burst in
  // index.css), so the rays frame the graph instead of sitting on top of it.
  return (
    <div className="relative flex h-[420px] w-full items-center justify-center overflow-hidden sm:h-[460px] lg:h-[520px]">
      <div
        className="line-burst pointer-events-none absolute left-1/2 top-1/2 h-[720px] w-[720px] -translate-x-1/2 -translate-y-1/2"
        style={{
          "--burst-color": "rgba(255,255,255,0.8)",
          "--burst-period": "6deg",
          "--burst-hole": "33%",
          "--burst-edge": "68%",
        }}
      />

      <svg
        viewBox="0 0 360 320"
        className="relative h-full w-full max-w-[440px]"
        role="img"
        aria-label="Symbol graph: login calls createAuth, run calls login, indexed by sg into a local graph"
      >
        <defs>
          <marker id="hero-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
            <path d="M0,0 L8,4 L0,8 Z" fill="white" />
          </marker>
        </defs>

        {/* edges first so the node plates sit on top of them */}
        <path d="M158 60 L 190 60" fill="none" stroke="white" strokeWidth="1.6" markerEnd="url(#hero-arrow)" />
        <text x="174" y="52" textAnchor="middle" fontFamily="IBM Plex Mono, monospace" fontSize="7" letterSpacing="0.8" fill="white" opacity="0.85">CALLS</text>
        <path d="M96 80 C 96 116, 140 118, 140 136" fill="none" stroke="white" strokeWidth="1.2" strokeDasharray="4 4" opacity="0.8" />
        <path d="M264 80 C 264 116, 220 118, 220 136" fill="none" stroke="white" strokeWidth="1.2" strokeDasharray="4 4" opacity="0.8" />
        <path d="M140 190 C 140 214, 96 218, 96 238" fill="none" stroke="white" strokeWidth="1.2" opacity="0.8" />
        <path d="M220 190 C 220 214, 264 218, 264 238" fill="none" stroke="white" strokeWidth="1.2" opacity="0.8" />

        {/* symbol nodes — boxes widened so the longest name has real margin */}
        <g>
          <rect x="30" y="42" width="128" height="38" fill="white" />
          <text x="94" y="66" textAnchor="middle" fontFamily="IBM Plex Mono, monospace" fontSize="12" fontWeight="600" fill="#1c1cf0">login()</text>
        </g>
        <g>
          <rect x="190" y="42" width="140" height="38" fill="none" stroke="white" strokeWidth="1.6" />
          <text x="260" y="66" textAnchor="middle" fontFamily="IBM Plex Mono, monospace" fontSize="12" fontWeight="600" fill="white">createAuth()</text>
        </g>
        <g>
          <rect x="30" y="238" width="128" height="38" fill="none" stroke="white" strokeWidth="1.6" />
          <text x="94" y="262" textAnchor="middle" fontFamily="IBM Plex Mono, monospace" fontSize="12" fontWeight="600" fill="white">run()</text>
        </g>
        <g>
          <rect x="190" y="238" width="140" height="38" fill="white" />
          <text x="260" y="262" textAnchor="middle" fontFamily="IBM Plex Mono, monospace" fontSize="12" fontWeight="600" fill="#1c1cf0">logout()</text>
        </g>

        {/* the index itself, on a solid plate in the middle of the burst hole.
            Numbers are this repo indexed by sg, not illustrative filler. */}
        <g>
          <rect x="108" y="136" width="144" height="54" fill="white" />
          <text x="180" y="158" textAnchor="middle" fontFamily="IBM Plex Mono, monospace" fontSize="11" fontWeight="600" fill="#1c1cf0">sg index .</text>
          <line x1="122" y1="166" x2="238" y2="166" stroke="#1c1cf0" strokeWidth="0.6" opacity="0.25" />
          <text x="180" y="180" textAnchor="middle" fontFamily="IBM Plex Mono, monospace" fontSize="8" fill="#1c1cf0" opacity="0.75">2,023 symbols · 381 files</text>
        </g>

        <rect x="110" y="6" width="140" height="20" fill="none" stroke="white" strokeWidth="1" opacity="0.5" />
        <text x="180" y="19.5" textAnchor="middle" fontFamily="IBM Plex Mono, monospace" fontSize="7.5" letterSpacing="1.6" fill="white" opacity="0.9">SYMBOL GRAPH · MCP</text>
      </svg>
    </div>
  );
}

export default function Hero() {
  const [tab, setTab] = useState(INSTALL_TABS[0].key);
  const active = INSTALL_TABS.find((t) => t.key === tab);
  const command = active.lines.join(" && ");

  return (
    <section id="top" className="relative overflow-hidden bg-blue px-6 pb-6 pt-6 sm:pb-8 sm:pt-8">
      <div className="relative mx-auto max-w-[1280px]">
        <div className="grid items-center gap-6 lg:grid-cols-[1.05fr_1fr] lg:gap-4">
          {/* left — type: display headline light, mono label/body like Hermes */}
          <div className="min-w-0">
            <p className="font-mono text-[10px] font-normal uppercase tracking-[0.22em] text-white">
              Open source · MIT license
            </p>

            <h1 className="mt-3 max-w-[12ch] font-display text-[44px] font-[400] leading-[0.85] tracking-[-0.035em] text-white sm:text-[56px] lg:text-[64px]">
              A SYMBOL
              <br />
              GRAPH FOR
              <br />
              YOUR
              <br />
              CODEBASE
            </h1>

            <p className="mt-5 max-w-[52ch] font-mono text-[13px] font-normal leading-[1.75] tracking-[0.01em] text-white/90">
              symbolgraph parses your repo with tree-sitter, resolves every function
              and class into a real graph, and serves it to your agent over
              MCP — not text chunks. Entirely on your machine.
            </p>

            <div className="mt-5 flex flex-wrap items-center gap-3">
              <a
                href="#install"
                className="inline-flex items-center gap-2 bg-white px-5 py-2.5 font-mono text-[11px] font-normal uppercase tracking-[0.12em] text-blue transition hover:bg-white/90"
              >
                <span className="text-[13px]">⬢</span> Install via terminal
              </a>
              <a
                href="#architecture"
                className="hidden font-mono text-[11px] font-normal uppercase tracking-[0.14em] text-white underline decoration-white/40 underline-offset-4 hover:text-white sm:inline"
              >
                See how it works →
              </a>
            </div>

            <div id="install" className="mt-6 max-w-[520px] scroll-mt-20">
              <p className="mb-2 font-mono text-[10px] font-normal uppercase tracking-[0.2em] text-white">Install via terminal</p>
              <div className="flex gap-1 font-mono text-[11px]">
                {INSTALL_TABS.map((t) => (
                  <button
                    key={t.key}
                    type="button"
                    onClick={() => setTab(t.key)}
                    className={`px-3 py-1.5 font-mono text-[10px] font-normal uppercase tracking-[0.14em] transition ${
                      tab === t.key ? "bg-white text-blue" : "bg-white/12 text-white hover:bg-white/18 hover:text-white"
                    }`}
                  >
                    {t.label}
                  </button>
                ))}
              </div>
              <div className="bg-white">
                {active.lines.map((line, i) => (
                  <div
                    key={line}
                    className={`flex items-center justify-between gap-4 px-3 py-2.5 ${i > 0 ? "border-t border-blue/15" : ""}`}
                  >
                    <code className="min-w-0 flex-1 whitespace-pre-wrap break-all font-mono text-[12px] font-normal leading-none tracking-[-0.01em] text-blue">
                      <span className="select-none text-blue/45">$ </span>
                      {line}
                    </code>
                    {i === active.lines.length - 1 && <CopyButton text={command} className="text-blue/60 hover:bg-blue/10 hover:text-blue" />}
                  </div>
                ))}
              </div>
              <p className="mt-1.5 font-mono text-[10px] font-normal tracking-[0.04em] text-white/70">
                PyPI pending v0.1.0 tag — clone &amp; <span className="text-white">uv tool install .</span> today.
              </p>
            </div>
          </div>

          {/* right — Hermes-style engraving, no cropping on desktop */}
          <div className="min-w-0 lg:pl-2">
            <HeroArt />
          </div>
        </div>
      </div>
    </section>
  );
}
