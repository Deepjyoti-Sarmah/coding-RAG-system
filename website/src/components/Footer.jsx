import { FOOTER_LINKS } from "../data/content";
import { Shell } from "./ui";

export default function Footer() {
  return (
    <footer className="bg-ultra-navy">
      <Shell className="flex flex-wrap items-center justify-between gap-5 py-8">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          <span className="font-display text-base text-white">symbolgraph</span>
          <span className="tag-index text-white/45">v0.1.0 · MIT licensed</span>
          <span className="tag-index text-white/45">zero telemetry</span>
        </div>

        <nav className="flex flex-wrap items-center gap-x-6 gap-y-2">
          {FOOTER_LINKS.map((l) => (
            <a
              key={l.label}
              href={l.href}
              target="_blank"
              rel="noreferrer"
              className="tag-index text-white/55 transition hover:text-white"
            >
              {l.label}
            </a>
          ))}
        </nav>
      </Shell>
    </footer>
  );
}
