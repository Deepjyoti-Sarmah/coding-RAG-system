import { useState } from "react";
import CopyButton from "./CopyButton";
import { INSTALL_TABS } from "../data/content";

function HeroArt() {
  return (
    <div className="relative flex h-[420px] w-full items-center justify-center overflow-hidden sm:h-[460px] lg:h-[520px]">
      {/* 3 radial bursts like Hermes — crisp, high-contrast */}
      <div className="line-burst absolute -left-8 -top-10 h-[280px] w-[320px] rotate-[-18deg] opacity-100" style={{ "--burst-color": "rgba(255,255,255,0.98)", "--burst-from": " -20deg" }} />
      <div className="line-burst absolute -right-6 -top-4 h-[300px] w-[340px] rotate-[22deg] opacity-100" style={{ "--burst-color": "rgba(255,255,255,0.98)", "--burst-from": " 18deg" }} />
      <div className="line-burst absolute left-1/2 top-[46%] h-[520px] w-[520px] -translate-x-1/2 -translate-y-1/2 opacity-35" style={{ "--burst-color": "rgba(255,255,255,0.9)" }} />
      <div className="line-burst absolute bottom-0 right-10 h-[220px] w-[260px] rotate-[35deg] opacity-90" style={{ "--burst-color": "rgba(255,255,255,0.9)" }} />

      {/* Engraved graph — bold white on blue */}
      <svg viewBox="0 0 360 360" className="relative h-[88%] w-[88%] max-w-[420px] drop-shadow-[0_2px_12px_rgba(0,0,0,0.2)]" role="img" aria-label="Symbol graph engraving">
        <defs>
          <pattern id="hero-halftone" width="6" height="6" patternUnits="userSpaceOnUse">
            <circle cx="1" cy="1" r="0.9" fill="white" opacity="0.14" />
          </pattern>
        </defs>
        <rect x="34" y="28" width="292" height="304" rx="4" fill="white" opacity="0.07" />
        <rect x="34" y="28" width="292" height="304" rx="4" fill="url(#hero-halftone)" opacity="0.35" />
        <circle cx="180" cy="168" r="82" fill="none" stroke="white" strokeWidth="0.7" opacity="0.18" />
        <circle cx="180" cy="168" r="106" fill="none" stroke="white" strokeWidth="0.5" opacity="0.12" />
        {Array.from({ length: 24 }).map((_, i) => {
          const a = (i * 15 * Math.PI) / 180;
          const x1 = 180 + Math.cos(a) * 8;
          const y1 = 168 + Math.sin(a) * 8;
          const x2 = 180 + Math.cos(a) * 122;
          const y2 = 168 + Math.sin(a) * 122;
          return <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke="white" strokeWidth="0.6" opacity="0.22" />;
        })}
        <g>
          <rect x="78" y="52" width="92" height="36" rx="3" fill="white" />
          <text x="124" y="74" textAnchor="middle" fontFamily="IBM Plex Mono, monospace" fontSize="10" fontWeight="700" fill="#1c1cf0">login()</text>
          <text x="124" y="82" textAnchor="middle" fontFamily="IBM Plex Mono, monospace" fontSize="5.5" fill="#1c1cf0" opacity="0.7">CALLS</text>
        </g>
        <g>
          <rect x="190" y="52" width="92" height="36" rx="3" fill="none" stroke="white" strokeWidth="1.6" />
          <text x="236" y="74" textAnchor="middle" fontFamily="IBM Plex Mono, monospace" fontSize="10" fontWeight="700" fill="white">createAuth()</text>
        </g>
        <g>
          <rect x="78" y="248" width="92" height="36" rx="3" fill="none" stroke="white" strokeWidth="1.4" />
          <text x="124" y="270" textAnchor="middle" fontFamily="IBM Plex Mono, monospace" fontSize="10" fontWeight="700" fill="white">run()</text>
        </g>
        <g>
          <rect x="190" y="248" width="92" height="36" rx="3" fill="white" />
          <text x="236" y="270" textAnchor="middle" fontFamily="IBM Plex Mono, monospace" fontSize="10" fontWeight="700" fill="#1c1cf0">logout()</text>
        </g>
        <g>
          <rect x="124" y="148" width="112" height="40" rx="4" fill="white" />
          <text x="180" y="167" textAnchor="middle" fontFamily="IBM Plex Mono, monospace" fontSize="7.5" fontWeight="700" fill="#1c1cf0">sg index .</text>
          <text x="180" y="178" textAnchor="middle" fontFamily="IBM Plex Mono, monospace" fontSize="6" fill="#1c1cf0" opacity="0.75">9201 symbols · 4.1s</text>
        </g>
        <path d="M170 70 L 190 70" stroke="white" strokeWidth="1.8" />
        <path d="M124 88 L 150 148" stroke="white" strokeWidth="1.4" strokeDasharray="4 3" opacity="0.95" />
        <path d="M236 88 L 210 148" stroke="white" strokeWidth="1.4" strokeDasharray="4 3" opacity="0.95" />
        <path d="M136 188 L 124 248" stroke="white" strokeWidth="1.4" />
        <path d="M224 188 L 236 248" stroke="white" strokeWidth="1.4" />
        <circle cx="180" cy="168" r="2.2" fill="#1c1cf0" stroke="white" strokeWidth="1" />
        <rect x="118" y="18" width="124" height="18" rx="9" fill="white" />
        <text x="180" y="29.5" textAnchor="middle" fontFamily="IBM Plex Mono, monospace" fontSize="6.5" fontWeight="700" letterSpacing="1.2" fill="#1c1cf0">SYMBOL GRAPH · MCP</text>
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

            <h1 className="mt-3 max-w-[12ch] font-display text-[44px] font-[300] leading-[0.85] tracking-[-0.035em] text-white sm:text-[56px] lg:text-[64px]">
              A SYMBOL
              <br />
              GRAPH FOR
              <br />
              YOUR
              <br />
              CODEBASE
            </h1>

            <p className="mt-4 max-w-[42ch] font-mono text-[11px] font-normal leading-[1.7] tracking-[0.06em] text-white">
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
