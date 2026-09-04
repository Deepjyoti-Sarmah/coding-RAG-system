import { NAV_LINKS, REPO_URL } from "../data/content";
import { Shell } from "./ui";

export default function Nav() {
  return (
    <header className="sticky top-0 z-50 border-b border-white/25 bg-ultra/95 backdrop-blur-md">
      <Shell className="flex h-14 items-center justify-between gap-6">
        <a href="#top" className="flex items-baseline gap-2.5">
          <span className="font-display text-lg tracking-tight text-white">symbolgraph</span>
          <span className="tag-index hidden text-white/70 sm:inline">local code intelligence</span>
        </a>

        <nav className="hidden items-center gap-7 md:flex">
          {NAV_LINKS.map((l) => (
            <a
              key={l.label}
              href={l.href}
              className="tag-index text-white/78 transition hover:text-white"
            >
              {l.label}
            </a>
          ))}
        </nav>

        <div className="flex items-center gap-3">
          <span className="tag-index hidden text-white/70 lg:inline">MIT · v0.1.0</span>
          <a
            href={REPO_URL}
            target="_blank"
            rel="noreferrer"
            className="tag-index border border-white bg-white px-3 py-2 text-ultra transition hover:bg-ultra hover:text-white"
          >
            GitHub
          </a>
        </div>
      </Shell>
    </header>
  );
}
