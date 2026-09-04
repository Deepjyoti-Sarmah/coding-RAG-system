export default function BigWordmark() {
  // "symbolgraph" is 11 characters where the old name was 3, so the old
  // 22vw/15vw sizing ran past both edges of the viewport. clamp() keeps it
  // near-edge-to-edge but inside, and leading >1 stops the g/p descenders
  // colliding with the line beneath. The subtitle no longer repeats the
  // wordmark that is directly above it.
  return (
    <section className="overflow-hidden border-y border-blue bg-white py-8 sm:py-10">
      <p className="select-none px-6 text-center font-display text-[clamp(2.5rem,10.5vw,10rem)] font-[400] leading-[1.05] tracking-[-0.03em] text-blue">
        symbolgraph
      </p>
      <p className="mt-3 text-center font-mono text-[10px] font-normal uppercase tracking-[0.22em] text-blue/70">
        Local-first · open source · MIT
      </p>
    </section>
  );
}
