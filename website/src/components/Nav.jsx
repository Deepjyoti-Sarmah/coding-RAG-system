import { useState } from "react";
import { NAV_LINKS, REPO_URL } from "../data/content";

export default function Nav() {
  const [open, setOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 border-b border-white/[0.08] bg-blue/95 backdrop-blur supports-[backdrop-filter]:bg-blue/85">
      <nav className="mx-auto flex max-w-[1280px] items-center justify-between px-6 py-3.5">
        <a href="#top" className="font-display text-[17px] font-normal tracking-[-0.02em] text-white">
          symbolgraph
        </a>

        <div className="hidden items-center gap-8 md:flex">
          {NAV_LINKS.map((l) => (
            <a
              key={l.label}
              href={l.href}
              className="font-mono text-[11px] font-normal uppercase tracking-[0.14em] text-white transition hover:text-white/70"
            >
              {l.label}
            </a>
          ))}
          <a
            href={REPO_URL}
            target="_blank"
            rel="noreferrer"
            className="font-mono text-[11px] font-normal uppercase tracking-[0.14em] text-white transition hover:text-white/70"
          >
            GitHub
          </a>
        </div>

        <a
          href="#install"
          className="hidden bg-white px-4 py-1.5 font-mono text-[11px] font-normal uppercase tracking-[0.12em] text-blue transition hover:bg-white/90 md:inline-block"
        >
          Install →
        </a>

        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="flex h-8 w-8 items-center justify-center text-white md:hidden"
          aria-label="Toggle menu"
          aria-expanded={open}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round">
            {open ? <path d="M18 6 6 18M6 6l12 12" /> : <path d="M3 6h18M3 12h18M3 18h18" />}
          </svg>
        </button>
      </nav>

      {open && (
        <div className="border-t border-white/20 bg-blue px-6 py-4 md:hidden">
          <div className="flex flex-col gap-4">
            {NAV_LINKS.map((l) => (
              <a
                key={l.label}
                href={l.href}
                onClick={() => setOpen(false)}
                className="font-mono text-xs uppercase tracking-widest text-white"
              >
                {l.label}
              </a>
            ))}
            <a href={REPO_URL} target="_blank" rel="noreferrer" className="font-mono text-xs uppercase tracking-widest text-white">
              GitHub
            </a>
            <a
              href="#install"
              onClick={() => setOpen(false)}
              className="mt-2 bg-white px-4 py-2 text-center font-mono text-xs font-semibold uppercase tracking-widest text-blue"
            >
              Install →
            </a>
          </div>
        </div>
      )}
    </header>
  );
}
