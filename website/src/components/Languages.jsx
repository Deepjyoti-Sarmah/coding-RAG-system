import { CLI_COMMANDS, FALLBACK_COUNT, FALLBACK_EXAMPLE, LANGUAGES } from "../data/content";
import CopyButton from "./CopyButton";
import { IndexTag, Shell } from "./ui";

export default function Languages() {
  return (
    <section id="languages" className="border-b border-white/25 bg-white text-ultra">
      <Shell className="py-24">
        <div className="grid gap-16 lg:grid-cols-2">
          {/* Languages */}
          <div>
            <IndexTag tone="on-white">Full graph support</IndexTag>
            <h2 className="font-display mt-4 text-[clamp(1.9rem,3.4vw,2.75rem)] leading-[1.15] tracking-[-0.01em]">
              Languages parsed
            </h2>
            <p className="mt-5 max-w-md text-[12.5px] leading-[1.7] text-ultra/70">
              Eleven tree-sitter profiles resolve symbols, typed edges and
              imports into the graph. Everything else still indexes for
              full-text and vector search — it just has no AST.
            </p>

            <div className="hairline-matrix-blue mt-8 grid border border-ultra/25 sm:grid-cols-2">
              {LANGUAGES.map((l) => (
                <div key={l.lang} className="flex items-baseline justify-between gap-3 bg-white px-5 py-3.5">
                  <span className="text-[12.5px] text-ultra">{l.lang}</span>
                  <code className="text-[10.5px] text-ultra/62">{l.ext}</code>
                </div>
              ))}
            </div>

            <div className="mt-px border border-ultra/25 border-t-0 bg-ultra/5 px-5 py-4">
              <div className="tag-index text-ultra/72">{FALLBACK_COUNT} more · text-indexed only</div>
              <code className="mt-2 block text-[10.5px] leading-[1.6] text-ultra/62">
                {FALLBACK_EXAMPLE}
              </code>
            </div>
          </div>

          {/* CLI */}
          <div>
            <IndexTag tone="on-white">Command line</IndexTag>
            <h2 className="font-display mt-4 text-[clamp(1.9rem,3.4vw,2.75rem)] leading-[1.15] tracking-[-0.01em]">
              Everything, without an agent
            </h2>
            <p className="mt-5 max-w-md text-[12.5px] leading-[1.7] text-ultra/70">
              The MCP server is a wrapper. Every capability is reachable from
              the terminal first — which is also how you debug it.
            </p>

            <ul className="mt-8 flex flex-col border border-ultra/25">
              {CLI_COMMANDS.map((c) => (
                <li
                  key={c.cmd}
                  className="group flex items-center justify-between gap-4 border-b border-ultra/12 px-5 py-3.5 last:border-b-0"
                >
                  <div className="min-w-0">
                    <code className="block truncate text-[12px] text-ultra">{c.cmd}</code>
                    <div className="mt-1 text-[11px] text-ultra/65">{c.desc}</div>
                  </div>
                  <CopyButton text={c.cmd} />
                </li>
              ))}
            </ul>
          </div>
        </div>
      </Shell>
    </section>
  );
}
