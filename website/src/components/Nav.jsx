import { useState } from "react";
import { NAV_LINKS, REPO_URL } from "../data/content";

export default function Nav() {
  const [open, setOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 border-b border-line/60 bg-paper/95 backdrop-blur">
      <nav className="mx-auto flex max-w-[1100px] items-center justify-between px-6 py-4">
        <a href="#top" className="flex items-baseline gap-2 font-mono text-[15px] font-medium text-ink">
          <span className="text-blueprint">◇</span>
          CKG
        </a>

        <div className="hidden items-center gap-7 md:flex">
          {NAV_LINKS.map((l) => (
            <a
              key={l.label}
              href={l.href}
              className="font-mono text-sm text-ink-soft transition hover:text-ink"
            >
              {l.label}
            </a>
          ))}
          <a
            href={REPO_URL}
            target="_blank"
            rel="noreferrer"
            className="font-mono text-sm text-ink-soft transition hover:text-ink"
          >
            Source
          </a>
          <a
            href="#install"
            className="font-mono text-sm font-medium text-blueprint underline decoration-blueprint/30 underline-offset-4 transition hover:decoration-blueprint"
          >
            Install
          </a>
        </div>

        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="flex h-8 w-8 items-center justify-center text-ink md:hidden"
          aria-label="Toggle menu"
          aria-expanded={open}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round">
            {open ? <path d="M18 6 6 18M6 6l12 12" /> : <path d="M3 6h18M3 12h18M3 18h18" />}
          </svg>
        </button>
      </nav>

      {open && (
        <div className="border-t border-line/60 px-6 py-4 md:hidden">
          <div className="flex flex-col gap-3">
            {NAV_LINKS.map((l) => (
              <a
                key={l.label}
                href={l.href}
                onClick={() => setOpen(false)}
                className="font-mono text-sm text-ink-soft"
              >
                {l.label}
              </a>
            ))}
            <a href={REPO_URL} target="_blank" rel="noreferrer" className="font-mono text-sm text-ink-soft">
              Source
            </a>
            <a href="#install" onClick={() => setOpen(false)} className="font-mono text-sm font-medium text-blueprint">
              Install
            </a>
          </div>
        </div>
      )}
    </header>
  );
}
