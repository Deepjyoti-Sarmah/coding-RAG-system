import { FOOTER_LINKS, REPO_URL } from "../data/content";

function GitHubIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" {...props}>
      <path d="M12 .5C5.65.5.5 5.65.5 12c0 5.09 3.29 9.4 7.86 10.93.58.1.79-.25.79-.56 0-.28-.01-1.02-.02-2-3.2.7-3.88-1.54-3.88-1.54-.52-1.33-1.28-1.68-1.28-1.68-1.04-.72.08-.7.08-.7 1.15.08 1.76 1.19 1.76 1.19 1.03 1.75 2.7 1.25 3.36.96.1-.75.4-1.25.73-1.54-2.55-.29-5.23-1.28-5.23-5.68 0-1.25.45-2.28 1.19-3.08-.12-.29-.52-1.46.11-3.05 0 0 .97-.31 3.18 1.18a11.1 11.1 0 0 1 5.79 0c2.2-1.49 3.17-1.18 3.17-1.18.63 1.59.24 2.76.12 3.05.74.8 1.18 1.83 1.18 3.08 0 4.41-2.69 5.38-5.25 5.67.42.36.78 1.07.78 2.16 0 1.56-.02 2.81-.02 3.19 0 .31.21.67.8.56A10.53 10.53 0 0 0 23.5 12C23.5 5.65 18.35.5 12 .5Z" />
    </svg>
  );
}

export default function Footer() {
  return (
    <footer className="bg-ink px-6 py-8">
      <div className="mx-auto flex max-w-[1280px] flex-col gap-8 md:flex-row md:items-start md:justify-between">
        <div className="max-w-[32ch]">
          <p className="font-display text-[22px] font-[400] tracking-[-0.02em] text-white">symbolgraph</p>
          <p className="mt-2 font-mono text-[12.5px] font-normal leading-[1.6] tracking-[0.02em] text-white">
            A local-first symbol graph and hybrid retrieval engine for AI
            coding agents.
          </p>
          <a
            href={REPO_URL}
            target="_blank"
            rel="noreferrer"
            className="mt-4 flex h-8 w-8 items-center justify-center border border-white text-white transition hover:bg-white hover:text-ink"
            aria-label="symbolgraph on GitHub"
          >
            <GitHubIcon className="h-3.5 w-3.5" />
          </a>
        </div>

        <div className="flex flex-wrap gap-x-8 gap-y-4">
          {FOOTER_LINKS.map((l) => (
            <a
              key={l.label}
              href={l.href}
              target="_blank"
              rel="noreferrer"
              className="font-mono text-[11px] font-normal uppercase tracking-[0.14em] text-white transition hover:text-white/70"
            >
              {l.label}
            </a>
          ))}
        </div>
      </div>

      <div className="mx-auto mt-8 flex max-w-[1280px] flex-col gap-1.5 border-t border-white pt-5 font-mono text-[10px] font-normal tracking-[0.12em] text-white sm:flex-row sm:items-center sm:justify-between">
        <span>© 2026 symbolgraph — v0.1.0, MIT licensed</span>
        <span>HERMES-INSPIRED · LOCAL-FIRST · NO CLOUD</span>
      </div>
    </footer>
  );
}
