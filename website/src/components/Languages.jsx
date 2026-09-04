import Section from "./Section";
import { LANGUAGES, FALLBACK_COUNT, FALLBACK_EXAMPLE } from "../data/content";

export default function Languages() {
  return (
    <Section id="languages" label="Languages">
      <h2 className="max-w-[36ch] font-mono text-3xl font-semibold leading-tight text-ink sm:text-4xl">
        AST-aware where it counts
      </h2>

      <div className="mt-8 overflow-x-auto">
        <table className="w-full min-w-[420px] border-collapse text-sm">
          <thead>
            <tr className="border-b border-line text-left font-mono text-xs text-ink-soft">
              <th className="py-2 pr-4 font-medium">Language</th>
              <th className="py-2 font-medium">Extensions</th>
            </tr>
          </thead>
          <tbody>
            {LANGUAGES.map((l) => (
              <tr key={l.lang} className="border-b border-line/60">
                <td className="py-3 pr-4 text-ink-soft">{l.lang}</td>
                <td className="py-3 font-mono text-[13px] text-blueprint">{l.ext}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="mt-6 max-w-[62ch] text-[15px] leading-relaxed text-ink-soft">
        Everything else — {FALLBACK_COUNT} extensions including{" "}
        <code className="rounded bg-paper-2 px-1.5 py-0.5 font-mono text-[13px]">{FALLBACK_EXAMPLE}</code>{" "}
        — still gets a module-level symbol and stays searchable. Nothing is silently skipped.
      </p>
    </Section>
  );
}
