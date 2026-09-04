import { EDITORS, MCP_TOOLS } from "../data/content";
import CopyButton from "./CopyButton";
import { IndexTag, Shell } from "./ui";

const MCP_SNIPPET = `{
  "mcpServers": {
    "symbolgraph": { "command": "sg-mcp" }
  }
}`;

export default function McpTools() {
  return (
    <section id="mcp" className="border-b border-white/25 bg-ultra">
      <Shell className="py-24">
        <div className="flex flex-wrap items-end justify-between gap-6">
          <div>
            <IndexTag>Model context protocol</IndexTag>
            <h2 className="font-display mt-4 text-[clamp(2rem,4vw,3.25rem)] leading-[1.1] tracking-[-0.02em] text-white">
              Fifteen tools your agent gets
            </h2>
          </div>
          <span className="tag-index max-w-xs text-white/45">
            sg init writes this config for every agent it finds
          </span>
        </div>

        {/* Config + detected agents, side by side above the reference. */}
        <div className="mt-12 grid gap-px lg:grid-cols-2">
          <div className="border border-white/25 bg-ultra-deep">
            <div className="flex items-center justify-between border-b border-white/25 px-4 py-2.5">
              <span className="tag-index text-white">.mcp.json</span>
              <CopyButton text={MCP_SNIPPET} className="text-white/50 hover:bg-white/10 hover:text-white" />
            </div>
            <pre className="overflow-x-auto p-5 text-[12px] leading-[1.7] text-white/85">{MCP_SNIPPET}</pre>
          </div>

          <div className="border border-white/25 bg-ultra p-5">
            <IndexTag>Detected automatically</IndexTag>
            <div className="mt-4 flex flex-wrap gap-2">
              {EDITORS.map((e) => (
                <span
                  key={e}
                  className="border border-white/30 px-3 py-1.5 text-[11.5px] text-white/80"
                >
                  {e}
                </span>
              ))}
            </div>
            <p className="mt-4 text-[11.5px] leading-[1.6] text-white/55">
              <code className="text-white/85">sg init --agent all</code> writes an entry for each
              one it finds and leaves the rest alone. Re-running it changes nothing.
            </p>
          </div>
        </div>

        {/* Tool reference. A label column per group means an uneven group (7
            session tools vs 2 index tools) never strands empty cells. */}
        <div className="mt-12 border border-white/25">
          {MCP_TOOLS.map((group, gi) => (
            <div
              key={group.group}
              className={`grid gap-px sm:grid-cols-[160px_1fr] ${gi > 0 ? "border-t border-white/25" : ""}`}
            >
              <div className="bg-ultra-deep px-5 py-5">
                <IndexTag>{group.group}</IndexTag>
                <div className="tag-index mt-2 text-white/30">{group.tools.length} tools</div>
              </div>

              <div className="grid sm:grid-cols-2 xl:grid-cols-3">
                {group.tools.map((t) => (
                  <div
                    key={t.name}
                    className="border-b border-l border-white/12 px-5 py-4 last:border-b-0 sm:border-b"
                  >
                    <code className="text-[12px] text-white">{t.name}</code>
                    <div className="mt-1 text-[10.5px] text-white/40">({t.args})</div>
                    <div className="mt-1.5 text-[11.5px] leading-[1.5] text-white/60">{t.desc}</div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </Shell>
    </section>
  );
}
