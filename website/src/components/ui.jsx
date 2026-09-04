// Shared primitives for the ultramarine system. Every one of these encodes a
// rule from DESIGN.md that would otherwise be retyped (and drifted) per file:
// zero radius, exact 1px hairlines, uppercase tracked index tags.

export function IndexTag({ n, children, tone = "on-blue" }) {
  const color = tone === "on-white" ? "text-ultra/55" : "text-white/55";
  return (
    <div className={`tag-index flex items-center gap-2 ${color}`}>
      {n && <span className={tone === "on-white" ? "text-ultra" : "text-white"}>#{n}</span>}
      <span>{children}</span>
    </div>
  );
}

// Hairline-framed window for diagrams. The grid ground is what makes these
// read as drafting plates rather than empty boxes.
export function Plate({ children, tone = "on-blue", className = "" }) {
  const frame = tone === "on-white" ? "border-ultra/25 engraved-grid-blue" : "border-white/25 engraved-grid";
  return (
    <div className={`relative border ${frame} ${className}`}>{children}</div>
  );
}

export function Rule({ tone = "on-blue" }) {
  return <div className={`h-px w-full ${tone === "on-white" ? "bg-ultra/20" : "bg-white/25"}`} />;
}

// Corner tick brackets — the drafting-reticle accent from DESIGN.md.
export function Ticks({ tone = "on-blue" }) {
  const c = tone === "on-white" ? "border-ultra/40" : "border-white/40";
  return (
    <>
      <span className={`pointer-events-none absolute -left-px -top-px h-2 w-2 border-l border-t ${c}`} />
      <span className={`pointer-events-none absolute -right-px -top-px h-2 w-2 border-r border-t ${c}`} />
      <span className={`pointer-events-none absolute -bottom-px -left-px h-2 w-2 border-b border-l ${c}`} />
      <span className={`pointer-events-none absolute -bottom-px -right-px h-2 w-2 border-b border-r ${c}`} />
    </>
  );
}

export function Shell({ children, className = "" }) {
  return <div className={`mx-auto w-full max-w-320 px-5 sm:px-8 ${className}`}>{children}</div>;
}
