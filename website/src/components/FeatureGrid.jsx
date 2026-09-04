import { PIPELINE } from "../data/content";

function StageArt({ index }) {
  // Hermes-accurate: full-bleed duotone (white engraving on blue), square, high-contrast,
  // halftone grain, radial bursts — like the Hermes feature images. Each is codebase-honest.
  const arts = [
    // 0 Parse — tree-sitter AST: file bleeds into branching tree, burst behind
    <div key="0" className="absolute inset-0 bg-blue">
      <svg viewBox="0 0 300 300" className="h-full w-full" preserveAspectRatio="xMidYMid slice">
        <defs>
          <pattern id="ht0" width="7" height="7" patternUnits="userSpaceOnUse"><circle cx="3.5" cy="3.5" r="1" fill="white" opacity="0.18" /></pattern>
        </defs>
        <rect width="300" height="300" fill="#1c1cf0" />
        <rect width="300" height="300" fill="url(#ht0)" />
        {/* burst */}
        <g opacity="0.95">
          {Array.from({ length: 20 }).map((_, i) => {
            const a = (-40 + i * 6) * Math.PI / 180;
            const x2 = 150 + Math.cos(a) * 140;
            const y2 = 90 + Math.sin(a) * 140;
            return <line key={i} x1="150" y1="90" x2={x2} y2={y2} stroke="white" strokeWidth="0.7" opacity="0.32" />;
          })}
        </g>
        <rect x="48" y="72" width="78" height="108" rx="4" fill="none" stroke="white" strokeWidth="2" />
        <rect x="58" y="86" width="58" height="7" rx="2" fill="white" />
        <rect x="58" y="100" width="54" height="4" rx="1.5" fill="white" opacity="0.85" />
        <rect x="58" y="110" width="48" height="4" rx="1.5" fill="white" opacity="0.65" />
        <rect x="58" y="120" width="40" height="4" rx="1.5" fill="white" opacity="0.45" />
        <circle cx="150" cy="96" r="3" fill="white" />
        <line x1="150" y1="96" x2="190" y2="76" stroke="white" strokeWidth="1.6" />
        <line x1="150" y1="96" x2="190" y2="120" stroke="white" strokeWidth="1.6" />
        <circle cx="196" cy="76" r="14" fill="white" /><text x="196" y="81" textAnchor="middle" fontFamily="IBM Plex Mono, monospace" fontSize="7" fontWeight="800" fill="#1c1cf0">AST</text>
        <circle cx="196" cy="120" r="14" fill="none" stroke="white" strokeWidth="1.4" /><text x="196" y="124" textAnchor="middle" fontFamily="IBM Plex Mono, monospace" fontSize="6" fontWeight="700" fill="white">TS</text>
        <text x="150" y="210" textAnchor="middle" fontFamily="IBM Plex Mono, monospace" fontSize="9" fontWeight="700" fill="white">tree-sitter · one pass</text>
      </svg>
    </div>,
    // 1 Extract — stable_key ledger
    <div key="1" className="absolute inset-0 bg-blue">
      <svg viewBox="0 0 300 300" className="h-full w-full">
        <rect width="300" height="300" fill="#1c1cf0" />
        <g stroke="white" strokeWidth="0.5" opacity="0.18">
          {Array.from({ length: 32 }).map((_, i) => <line key={i} x1="0" y1={i*9+8} x2="300" y2={i*9+8} />)}
        </g>
        <g opacity="0.12">
          {Array.from({ length: 18 }).map((_, i) => <line key={i} x1={i*16+8} y1="0" x2={i*16+8} y2="300" stroke="white" strokeWidth="0.5"/>)}
        </g>
        {/* 3 rows like engraved ledger */}
        <rect x="18" y="38" width="264" height="56" rx="4" fill="white" />
        <text x="30" y="62" fontFamily="IBM Plex Mono, monospace" fontSize="10" fontWeight="700" fill="#1c1cf0">def login( )</text>
        <text x="30" y="78" fontFamily="IBM Plex Mono, monospace" fontSize="7.5" fill="#1c1cf0" opacity="0.75">stable_key  9f3a·e7c1</text>
        <text x="270" y="68" textAnchor="end" fontFamily="IBM Plex Mono, monospace" fontSize="14" fill="#1c1cf0" opacity="0.18">✓</text>

        <rect x="18" y="102" width="264" height="56" rx="4" fill="none" stroke="white" strokeWidth="1.7" />
        <text x="30" y="126" fontFamily="IBM Plex Mono, monospace" fontSize="10" fontWeight="700" fill="white">class Auth</text>
        <text x="30" y="142" fontFamily="IBM Plex Mono, monospace" fontSize="7.5" fill="white" opacity="0.85">stable_key  2c1e·4a0f</text>

        <rect x="18" y="166" width="264" height="56" rx="4" fill="none" stroke="white" strokeWidth="1.2" opacity="0.9" />
        <text x="30" y="190" fontFamily="IBM Plex Mono, monospace" fontSize="10" fontWeight="700" fill="white">interface Repo</text>
        <text x="30" y="206" fontFamily="IBM Plex Mono, monospace" fontSize="7.5" fill="white" opacity="0.7">stable_key  4bb0·91d2</text>
        <text x="150" y="250" textAnchor="middle" fontFamily="IBM Plex Mono, monospace" fontSize="8" fill="white" opacity="0.92">survives renames · fingerprints.py</text>
      </svg>
    </div>,
    // 2 Relationships — graph burst
    <div key="2" className="absolute inset-0 bg-blue">
      <svg viewBox="0 0 300 300" className="h-full w-full">
        <rect width="300" height="300" fill="#1c1cf0" />
        {/* radial burst */}
        <g opacity="0.9">
          {Array.from({ length: 28 }).map((_, i) => {
            const a = (i*12.8)*Math.PI/180;
            return <line key={i} x1="150" y1="150" x2={150+Math.cos(a)*150} y2={150+Math.sin(a)*150} stroke="white" strokeWidth="0.55" opacity="0.2"/>;
          })}
        </g>
        <circle cx="150" cy="150" r="64" fill="none" stroke="white" strokeWidth="0.6" opacity="0.22"/>
        {/* nodes */}
        <rect x="56" y="56" width="88" height="40" rx="4" fill="white"/><text x="100" y="81" textAnchor="middle" fontFamily="IBM Plex Mono, monospace" fontSize="11" fontWeight="800" fill="#1c1cf0">login</text>
        <rect x="156" y="56" width="88" height="40" rx="4" fill="none" stroke="white" strokeWidth="1.8"/><text x="200" y="81" textAnchor="middle" fontFamily="IBM Plex Mono, monospace" fontSize="11" fontWeight="800" fill="white">createAuth</text>
        <rect x="56" y="204" width="88" height="40" rx="4" fill="none" stroke="white" strokeWidth="1.4"/><text x="100" y="229" textAnchor="middle" fontFamily="IBM Plex Mono, monospace" fontSize="11" fontWeight="700" fill="white">run</text>
        <rect x="156" y="204" width="88" height="40" rx="4" fill="white"/><text x="200" y="229" textAnchor="middle" fontFamily="IBM Plex Mono, monospace" fontSize="11" fontWeight="700" fill="#1c1cf0">logout</text>
        {/* edges */}
        <line x1="144" y1="76" x2="156" y2="76" stroke="white" strokeWidth="2.2"/>
        <line x1="100" y1="96" x2="150" y2="150" stroke="white" strokeWidth="1.5" strokeDasharray="5 4"/>
        <line x1="200" y1="96" x2="150" y2="150" stroke="white" strokeWidth="1.5" strokeDasharray="5 4"/>
        <line x1="100" y1="204" x2="150" y2="150" stroke="white" strokeWidth="1.5"/>
        <line x1="200" y1="204" x2="150" y2="150" stroke="white" strokeWidth="1.5"/>
        <circle cx="150" cy="150" r="4" fill="white" stroke="#1c1cf0" strokeWidth="1.2"/>
        <text x="108" y="128" fontFamily="IBM Plex Mono, monospace" fontSize="7" fontWeight="700" fill="white">CALLS</text>
        <text x="190" y="128" fontFamily="IBM Plex Mono, monospace" fontSize="7" fontWeight="700" fill="white">CALLS</text>
      </svg>
    </div>,
    // 3 Store — SQLite stack
    <div key="3" className="absolute inset-0 bg-blue">
      <svg viewBox="0 0 300 300" className="h-full w-full">
        <rect width="300" height="300" fill="#1c1cf0" />
        {/* halftone */}
        <g opacity="0.18">
          {Array.from({ length: 300/7 }).map((_, r) => Array.from({ length: 300/7 }).map((_, c) => <circle key={`${r}-${c}`} cx={c*7+3.5} cy={r*7+3.5} r="0.8" fill="white"/>))}
        </g>
        <rect x="28" y="32" width="244" height="36" rx="4" fill="white"/>
        <text x="150" y="55" textAnchor="middle" fontFamily="IBM Plex Mono, monospace" fontSize="10" fontWeight="800" fill="#1c1cf0">.sg/index.sqlite  ·  WAL</text>
        {/* 3 cylinders */}
        <g>
          <ellipse cx="72" cy="102" rx="44" ry="16" fill="none" stroke="white" strokeWidth="1.6"/>
          <rect x="28" y="102" width="88" height="74" fill="white" opacity="0.95"/>
          <ellipse cx="72" cy="176" rx="44" ry="16" fill="white"/>
          <text x="72" y="132" textAnchor="middle" fontFamily="IBM Plex Mono, monospace" fontSize="9" fontWeight="800" fill="#1c1cf0">symbols</text>
          <text x="72" y="148" textAnchor="middle" fontFamily="IBM Plex Mono, monospace" fontSize="7" fill="#1c1cf0" opacity="0.7">chunks</text>
        </g>
        <g>
          <ellipse cx="150" cy="102" rx="44" ry="16" fill="none" stroke="white" strokeWidth="1.6"/>
          <rect x="106" y="102" width="88" height="74" fill="none" stroke="white" strokeWidth="1.4"/>
          <ellipse cx="150" cy="176" rx="44" ry="16" fill="none" stroke="white" strokeWidth="1.2"/>
          <text x="150" y="132" textAnchor="middle" fontFamily="IBM Plex Mono, monospace" fontSize="9" fontWeight="800" fill="white">FTS5</text>
          <text x="150" y="148" textAnchor="middle" fontFamily="IBM Plex Mono, monospace" fontSize="7" fill="white" opacity="0.8">full-text</text>
        </g>
        <g>
          <ellipse cx="228" cy="102" rx="44" ry="16" fill="white"/>
          <rect x="184" y="102" width="88" height="74" fill="white"/>
          <ellipse cx="228" cy="176" rx="44" ry="16" fill="white"/>
          <text x="228" y="132" textAnchor="middle" fontFamily="IBM Plex Mono, monospace" fontSize="9" fontWeight="800" fill="#1c1cf0">vec</text>
          <text x="228" y="148" textAnchor="middle" fontFamily="IBM Plex Mono, monospace" fontSize="7" fill="#1c1cf0" opacity="0.7">sqlite-vec</text>
        </g>
        <text x="150" y="220" textAnchor="middle" fontFamily="IBM Plex Mono, monospace" fontSize="8" fill="white" opacity="0.85">one file · no daemon</text>
      </svg>
    </div>,
    // 4 Retrieve — four signals fused (scanline like Hermes)
    <div key="4" className="absolute inset-0 bg-blue">
      <svg viewBox="0 0 300 300" className="h-full w-full">
        <rect width="300" height="300" fill="#1c1cf0" />
        <g opacity="0.14">
          {Array.from({ length: 75 }).map((_, i) => <rect key={i} x="0" y={i*4} width="300" height="1.2" fill="white" />)}
        </g>
        {/* scanline highlight */}
        <rect x="0" y="86" width="300" height="28" fill="white" opacity="0.06"/>
        {/* 4 tags top */}
        <rect x="14" y="28" width="62" height="30" rx="4" fill="white"/><text x="45" y="47" textAnchor="middle" fontFamily="IBM Plex Mono, monospace" fontSize="8.5" fontWeight="800" fill="#1c1cf0">exact</text>
        <rect x="82" y="28" width="62" height="30" rx="4" fill="none" stroke="white" strokeWidth="1.5"/><text x="113" y="47" textAnchor="middle" fontFamily="IBM Plex Mono, monospace" fontSize="8.5" fontWeight="700" fill="white">FTS</text>
        <rect x="150" y="28" width="62" height="30" rx="4" fill="none" stroke="white" strokeWidth="1.5"/><text x="181" y="47" textAnchor="middle" fontFamily="IBM Plex Mono, monospace" fontSize="8.5" fontWeight="700" fill="white">vector</text>
        <rect x="218" y="28" width="68" height="30" rx="4" fill="none" stroke="white" strokeWidth="1.5"/><text x="252" y="47" textAnchor="middle" fontFamily="IBM Plex Mono, monospace" fontSize="8.5" fontWeight="700" fill="white">graph</text>
        {/* converging */}
        <line x1="45" y1="58" x2="120" y2="118" stroke="white" strokeWidth="1.4" opacity="0.9"/>
        <line x1="113" y1="58" x2="138" y2="118" stroke="white" strokeWidth="1.4" opacity="0.9"/>
        <line x1="181" y1="58" x2="162" y2="118" stroke="white" strokeWidth="1.4" opacity="0.9"/>
        <line x1="252" y1="58" x2="180" y2="118" stroke="white" strokeWidth="1.4" opacity="0.9"/>
        {/* fuse */}
        <rect x="36" y="118" width="228" height="52" rx="6" fill="white"/>
        <text x="150" y="141" textAnchor="middle" fontFamily="IBM Plex Mono, monospace" fontSize="11" fontWeight="800" fill="#1c1cf0">RRF fuse → rerank</text>
        <text x="150" y="156" textAnchor="middle" fontFamily="IBM Plex Mono, monospace" fontSize="7" fill="#1c1cf0" opacity="0.7">cap per-file · token budget</text>
        {/* burst below */}
        <g opacity="0.5">
          {Array.from({ length: 14 }).map((_, i) => {
            const x = 80 + i*10;
            return <line key={i} x1="150" y1="170" x2={x} y2="260" stroke="white" strokeWidth="0.6" opacity={0.35}/>;
          })}
        </g>
      </svg>
    </div>,
    // 5 Serve — MCP terminal + badge
    <div key="5" className="absolute inset-0 bg-blue">
      <svg viewBox="0 0 300 300" className="h-full w-full">
        <rect width="300" height="300" fill="#1c1cf0" />
        <rect width="300" height="300" fill="none" stroke="white" strokeWidth="0.6" opacity="0.12"/>
        {/* terminal */}
        <rect x="22" y="28" width="156" height="176" rx="8" fill="white" />
        <circle cx="38" cy="46" r="5" fill="#ff5f56"/><circle cx="54" cy="46" r="5" fill="#ffbd2e"/><circle cx="70" cy="46" r="5" fill="#27c93f"/>
        <rect x="22" y="58" width="156" height="1" fill="#1c1cf0" opacity="0.12"/>
        <text x="34" y="82" fontFamily="IBM Plex Mono, monospace" fontSize="8.5" fontWeight="700" fill="#1c1cf0">$ sg search</text>
        <text x="34" y="100" fontFamily="IBM Plex Mono, monospace" fontSize="8" fill="#1c1cf0" opacity="0.55">sg index .</text>
        <text x="34" y="118" fontFamily="IBM Plex Mono, monospace" fontSize="8" fill="#1c1cf0" opacity="0.55">sg dashboard</text>
        <rect x="34" y="130" width="132" height="22" rx="4" fill="#1c1cf0"/>
        <text x="100" y="145" textAnchor="middle" fontFamily="IBM Plex Mono, monospace" fontSize="7" fontWeight="700" fill="white">▸ definitions, not files</text>
        <text x="34" y="172" fontFamily="IBM Plex Mono, monospace" fontSize="7" fill="#1c1cf0" opacity="0.45">within token budget</text>
        {/* MCP badge */}
        <g>
          <rect x="190" y="72" width="88" height="88" rx="8" fill="none" stroke="white" strokeWidth="2"/>
          <text x="234" y="100" textAnchor="middle" fontFamily="Bodoni Moda, serif" fontSize="22" fontWeight="700" fill="white">MCP</text>
          <text x="234" y="118" textAnchor="middle" fontFamily="IBM Plex Mono, monospace" fontSize="9" fontWeight="700" fill="white">13 tools</text>
          <line x1="208" y1="126" x2="260" y2="126" stroke="white" strokeWidth="0.7" opacity="0.5"/>
          <text x="234" y="140" textAnchor="middle" fontFamily="IBM Plex Mono, monospace" fontSize="6.5" fill="white" opacity="0.85">search · graph</text>
          <text x="234" y="150" textAnchor="middle" fontFamily="IBM Plex Mono, monospace" fontSize="6.5" fill="white" opacity="0.85">status · index</text>
        </g>
        {/* burst lines */}
        <g opacity="0.32">
          <line x1="240" y1="170" x2="220" y2="240" stroke="white" strokeWidth="0.7"/>
          <line x1="250" y1="170" x2="240" y2="240" stroke="white" strokeWidth="0.7"/>
          <line x1="260" y1="170" x2="260" y2="240" stroke="white" strokeWidth="0.7"/>
        </g>
      </svg>
    </div>,
  ];
  return (
    <div className="relative aspect-square w-full overflow-hidden border border-blue/15 bg-blue">
      {arts[index % arts.length]}
      <span className="absolute left-2 top-2 bg-white px-2 py-1 font-mono text-[9px] font-bold tracking-widest text-blue">
        0{index + 1}
      </span>
    </div>
  );
}

export default function FeatureGrid() {
  return (
    <section id="architecture" className="scroll-mt-16 border-y border-blue/15 bg-white px-6 py-8 sm:py-10">
      <div className="mx-auto max-w-[1280px]">
        <div className="flex items-center justify-between gap-4 border-b border-blue/15 pb-3">
          <p className="font-mono text-[10px] font-normal uppercase tracking-[0.22em] text-blue">
            Architecture — six stages, in order
          </p>
          <span className="hidden border border-blue px-2 py-1 font-mono text-[10px] font-normal uppercase tracking-[0.14em] text-blue sm:inline">
            Feature · Preview
          </span>
        </div>

        <div className="mt-6 grid gap-x-6 gap-y-10 sm:grid-cols-2 lg:grid-cols-3">
          {PIPELINE.map((step, i) => (
            <div key={step.stage} className="flex flex-col">
              <p className="font-mono text-[10px] font-normal uppercase tracking-[0.2em] text-blue">
                #{String(i + 1).padStart(2, "0")} — {step.stage.toUpperCase()}
              </p>
              <h3 className="mt-1.5 font-display text-[23px] font-[400] uppercase leading-[0.95] tracking-[-0.02em] text-blue sm:text-[25px]">
                {step.headline.toUpperCase()}
              </h3>
              <div className="mt-3.5">
                <StageArt index={i} />
              </div>
              <p className="mt-3 max-w-[32ch] font-mono text-[12.5px] font-normal leading-[1.65] tracking-[0.02em] text-blue">
                {step.detail}
              </p>
              <p className="mt-2 font-mono text-[10px] font-normal uppercase tracking-[0.12em] text-blue/60">{step.ref}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
