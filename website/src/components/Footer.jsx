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
    <footer className="bg-ink px-6 py-14">
      <div className="mx-auto flex max-w-[1280px] flex-col gap-10 md:flex-row md:items-start md:justify-between">
        <div className="max-w-xs">
          <p className="font-display text-2xl font-bold text-white">CKG</p>
          <p className="mt-3 text-sm leading-relaxed text-white/50">
            A local-first symbol graph and hybrid retrieval engine for AI
            coding agents.
          </p>
          <a
            href={REPO_URL}
            target="_blank"
            rel="noreferrer"
            className="mt-5 flex h-9 w-9 items-center justify-center rounded-full border border-white/15 text-white/70 transition hover:border-white/30 hover:text-white"
            aria-label="CKG on GitHub"
          >
            <GitHubIcon className="h-4 w-4" />
          </a>
        </div>

        <div className="flex flex-wrap gap-x-10 gap-y-6">
          {FOOTER_LINKS.map((l) => (
            <a
              key={l.label}
              href={l.href}
              target="_blank"
              rel="noreferrer"
              className="font-mono text-xs uppercase tracking-widest text-white/55 transition hover:text-white"
            >
              {l.label}
            </a>
          ))}
        </div>
      </div>

      <div className="mx-auto mt-12 flex max-w-[1280px] flex-col gap-2 border-t border-line-on-ink pt-6 font-mono text-xs text-white/35 sm:flex-row sm:items-center sm:justify-between">
        <span>© 2026 CKG — v0.1.0, MIT licensed</span>
        <span>Local-first. No cloud, no estimates.</span>
      </div>
    </footer>
  );
}
