import { PLATFORMS } from "../data/content";

export default function PlatformCards() {
  return (
    <section className="bg-blue px-6 pb-24">
      <div className="mx-auto max-w-[1280px]">
        <p className="text-center font-mono text-xs uppercase tracking-[0.25em] text-white/60">
          One tool, every machine
        </p>
        <h2 className="mt-3 text-center font-display text-3xl font-bold uppercase text-white sm:text-4xl">
          CKG for macOS, Linux &amp; Windows
        </h2>

        <div className="mt-12 grid gap-px overflow-hidden rounded-sm border border-white/15 sm:grid-cols-3">
          {PLATFORMS.map((p) => (
            <div
              key={p.name}
              className="flex flex-col items-center gap-4 border-white/15 bg-blue-deep/40 px-8 py-14 text-center sm:border-l first:border-l-0"
            >
              <span className="font-mono text-xs uppercase tracking-widest text-white/55">
                {p.detail}
              </span>
              <span className="font-display text-3xl font-bold text-white">{p.name}</span>
              <a
                href="#install"
                className="mt-2 rounded-sm bg-white px-5 py-2.5 font-mono text-xs font-semibold uppercase tracking-widest text-blue-deep transition hover:bg-white/90"
              >
                Install via terminal
              </a>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
