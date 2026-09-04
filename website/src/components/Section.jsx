/**
 * Every section shares one content width and one label treatment: a plain
 * sentence-case name in a fixed left rail, at the same baseline as the
 * heading, not a centered ALL-CAPS eyebrow stacked above it.
 */
export default function Section({ id, label, tone = "paper", children, wide = false }) {
  const isInk = tone === "ink";
  const bg = isInk ? "bg-ink text-paper" : "bg-paper text-ink";
  const labelColor = isInk ? "text-paper/50" : "text-ink-soft/70";
  const border = isInk ? "border-paper/15" : "border-line/60";

  return (
    <section id={id} className={`scroll-mt-16 border-t ${border} ${bg}`}>
      <div className={`mx-auto grid gap-6 px-6 py-16 md:py-20 ${wide ? "max-w-[1100px]" : "max-w-[880px]"} md:grid-cols-[120px_1fr]`}>
        <div className="hidden md:block">
          {label && (
            <span className={`sticky top-24 font-mono text-[13px] leading-tight ${labelColor}`}>
              {label}
            </span>
          )}
        </div>
        <div className="min-w-0">
          {label && (
            <span className={`mb-4 block font-mono text-[13px] md:hidden ${labelColor}`}>
              {label}
            </span>
          )}
          {children}
        </div>
      </div>
    </section>
  );
}
