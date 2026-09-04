import { PIPELINE } from "../data/content";
import { IndexTag, Shell } from "./ui";

const BLUE = "#0000f2";
const LINE = "rgba(0,0,242,0.45)";
const FILL = "rgba(0,0,242,0.06)";

// One diagram per stage. Each draws the thing the stage actually does, so the
// plate carries information rather than decoration.
const DIAGRAMS = {
  "01": (
    // One AST, built once — a tree with a single root.
    <svg viewBox="0 0 200 96" className="h-auto w-full">
      <path d="M100 20 L58 62 M100 20 L142 62 M58 62 L36 84 M58 62 L80 84" fill="none" stroke={LINE} strokeWidth="1" />
      <circle cx="100" cy="20" r="6" fill={BLUE} />
      <circle cx="58" cy="62" r="4.5" fill="none" stroke={LINE} />
      <circle cx="142" cy="62" r="4.5" fill="none" stroke={LINE} />
      <circle cx="36" cy="84" r="3.5" fill="none" stroke={LINE} />
      <circle cx="80" cy="84" r="3.5" fill="none" stroke={LINE} />
      <text x="112" y="24" fontSize="7" fontFamily="JetBrains Mono" fill={BLUE}>module</text>
    </svg>
  ),
  "02": (
    // stable_key survives an edit: same key, two revisions.
    <svg viewBox="0 0 200 96" className="h-auto w-full">
      <rect x="16" y="26" width="72" height="26" fill={FILL} stroke={LINE} />
      <rect x="112" y="26" width="72" height="26" fill={FILL} stroke={LINE} />
      <text x="52" y="43" textAnchor="middle" fontSize="7.5" fontFamily="JetBrains Mono" fill={BLUE}>login@v1</text>
      <text x="148" y="43" textAnchor="middle" fontSize="7.5" fontFamily="JetBrains Mono" fill={BLUE}>login@v2</text>
      <path d="M92 39 L108 39" fill="none" stroke={LINE} strokeWidth="1" strokeDasharray="2 2" />
      <rect x="52" y="64" width="96" height="18" fill={BLUE} />
      <text x="100" y="76" textAnchor="middle" fontSize="7" fontFamily="JetBrains Mono" fill="#fff">stable_key unchanged</text>
    </svg>
  ),
  "03": (
    // Typed edges between definitions.
    <svg viewBox="0 0 200 96" className="h-auto w-full">
      <rect x="14" y="18" width="60" height="22" fill={FILL} stroke={LINE} />
      <rect x="126" y="18" width="60" height="22" fill={FILL} stroke={LINE} />
      <rect x="70" y="66" width="60" height="22" fill={BLUE} />
      <path d="M74 29 L124 29" fill="none" stroke={LINE} markerEnd="url(#pa)" />
      <path d="M44 40 L96 64" fill="none" stroke={LINE} markerEnd="url(#pa)" />
      <defs>
        <marker id="pa" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="4" markerHeight="4" orient="auto-start-reverse">
          <path d="M0 0 L10 5 L0 10 z" fill={LINE} />
        </marker>
      </defs>
      <text x="99" y="25" textAnchor="middle" fontSize="6.5" fontFamily="JetBrains Mono" fill={BLUE}>EXTENDS</text>
      <text x="100" y="80" textAnchor="middle" fontSize="7" fontFamily="JetBrains Mono" fill="#fff">CALLS</text>
    </svg>
  ),
  "04": (
    // One file on disk holding four tables.
    <svg viewBox="0 0 200 96" className="h-auto w-full">
      <rect x="30" y="16" width="140" height="64" fill="none" stroke={LINE} />
      {["symbols", "edges", "chunks", "vectors"].map((t, i) => (
        <g key={t}>
          <rect x={38} y={24 + i * 14} width={124} height={11} fill={i === 0 ? BLUE : FILL} stroke={LINE} />
          <text x={44} y={32.5 + i * 14} fontSize="6.5" fontFamily="JetBrains Mono" fill={i === 0 ? "#fff" : BLUE}>{t}</text>
        </g>
      ))}
      <text x="100" y="90" textAnchor="middle" fontSize="6.5" fontFamily="JetBrains Mono" fill={BLUE}>.sg/index.sqlite</text>
    </svg>
  ),
  "05": (
    // Four signals converging into one ranked list.
    <svg viewBox="0 0 200 96" className="h-auto w-full">
      {["exact", "fts5", "vector", "graph"].map((t, i) => (
        <g key={t}>
          <rect x="10" y={12 + i * 19} width="52" height="14" fill={FILL} stroke={LINE} />
          <text x="36" y={22 + i * 19} textAnchor="middle" fontSize="6.5" fontFamily="JetBrains Mono" fill={BLUE}>{t}</text>
          <path d={`M62 ${19 + i * 19} C 90 ${19 + i * 19}, 96 48, 118 48`} fill="none" stroke={LINE} strokeWidth="1" />
        </g>
      ))}
      <rect x="120" y="36" width="64" height="24" fill={BLUE} />
      <text x="152" y="51" textAnchor="middle" fontSize="7" fontFamily="JetBrains Mono" fill="#fff">RRF fuse</text>
    </svg>
  ),
  "06": (
    // A budget bar: definitions in, cut at the budget line.
    <svg viewBox="0 0 200 96" className="h-auto w-full">
      <rect x="16" y="22" width="168" height="20" fill={FILL} stroke={LINE} />
      <rect x="16" y="22" width="96" height="20" fill={BLUE} />
      <text x="64" y="36" textAnchor="middle" fontSize="7" fontFamily="JetBrains Mono" fill="#fff">definitions</text>
      <path d="M112 14 L112 50" fill="none" stroke={BLUE} strokeWidth="1.5" strokeDasharray="3 2" />
      <text x="116" y="60" fontSize="6.5" fontFamily="JetBrains Mono" fill={BLUE}>budget 800</text>
      <text x="16" y="78" fontSize="6.5" fontFamily="JetBrains Mono" fill={BLUE}>whole files never sent</text>
    </svg>
  ),
};

export default function Pipeline() {
  return (
    <section id="pipeline" className="border-b border-white/25 bg-white text-ultra">
      <Shell className="py-24">
        <div className="flex flex-wrap items-end justify-between gap-6">
          <div>
            <IndexTag tone="on-white">The resolution pipeline</IndexTag>
            <h2 className="font-display mt-4 text-[clamp(2rem,4vw,3.25rem)] leading-[1.1] tracking-[-0.02em]">
              Six stages, in order
            </h2>
          </div>
          <span className="tag-index border border-ultra/30 px-3 py-2 text-ultra/70">
            Strictly deterministic · on‑device
          </span>
        </div>

        <div className="hairline-matrix-blue mt-14 grid border border-ultra/25 md:grid-cols-2 lg:grid-cols-3">
          {PIPELINE.map((s) => (
            <article key={s.n} className="flex flex-col gap-5 bg-white p-7">
              <div className="flex items-center justify-between gap-3">
                <IndexTag n={s.n} tone="on-white">{s.stage}</IndexTag>
                <code className="text-[10px] text-ultra/40">{s.ref}</code>
              </div>

              <h3 className="font-display text-[1.6rem] leading-[1.2]">{s.headline}</h3>

              <div className="engraved-grid-blue border border-ultra/20 px-4 py-3">
                {DIAGRAMS[s.n]}
              </div>

              <p className="text-[12.5px] leading-[1.65] text-ultra/70">{s.detail}</p>
            </article>
          ))}
        </div>
      </Shell>
    </section>
  );
}
