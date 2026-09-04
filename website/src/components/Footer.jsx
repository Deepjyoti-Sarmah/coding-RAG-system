import { REPO_URL } from "../data/content";

const LINKS = [
  { label: "Source", href: REPO_URL },
  { label: "Issues", href: `${REPO_URL}/issues` },
  { label: "Changelog", href: `${REPO_URL}/blob/main/CHANGELOG.md` },
  { label: "Security", href: `${REPO_URL}/blob/main/SECURITY.md` },
];

export default function Footer() {
  return (
    <footer className="bg-ink px-6 py-10 text-paper/60">
      <div className="mx-auto flex max-w-[1100px] flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-baseline gap-2 font-mono text-sm text-paper">
          <span className="text-blueprint">◇</span>
          CKG — v0.1.0, MIT licensed
        </div>
        <div className="flex flex-wrap gap-x-6 gap-y-2 font-mono text-sm">
          {LINKS.map((l) => (
            <a key={l.label} href={l.href} target="_blank" rel="noreferrer" className="hover:text-paper">
              {l.label}
            </a>
          ))}
        </div>
      </div>
    </footer>
  );
}
