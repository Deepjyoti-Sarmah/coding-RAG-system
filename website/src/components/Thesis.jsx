import { THESIS } from "../data/content";
import { IndexTag, Shell } from "./ui";

export default function Thesis() {
  return (
    <section className="relative overflow-hidden border-b border-white/25 bg-ultra">
      <div
        className="line-burst pointer-events-none absolute -left-72 top-1/2 hidden h-[760px] w-[760px] -translate-y-1/2 opacity-25 lg:block"
        style={{ "--burst-period": "6.5deg", "--burst-hole": "30%" }}
        aria-hidden="true"
      />

      <Shell className="relative py-24">
        <div className="max-w-3xl">
          <IndexTag>{THESIS.tag}</IndexTag>
          <h2 className="font-display mt-4 text-[clamp(2rem,4vw,3.25rem)] leading-[1.1] tracking-[-0.02em] text-white">
            {THESIS.headline}
          </h2>
          <p className="mt-6 text-[13px] leading-[1.75] text-white/72">{THESIS.body}</p>
        </div>

        <div className="hairline-matrix mt-14 grid border border-white/25 md:grid-cols-2">
          {THESIS.columns.map((col, i) => {
            const isUs = i === 1;
            return (
              <div key={col.label} className={isUs ? "bg-white p-8 text-ultra" : "bg-ultra p-8"}>
                <IndexTag tone={isUs ? "on-white" : "on-blue"}>{col.label}</IndexTag>

                <ul className="mt-6 flex flex-col">
                  {col.points.map((p) => (
                    <li
                      key={p}
                      className={`flex gap-3 border-t py-3.5 text-[12.5px] leading-[1.6] first:border-t-0 ${
                        isUs ? "border-ultra/15 text-ultra/80" : "border-white/15 text-white/65"
                      }`}
                    >
                      <span className={isUs ? "text-ultra" : "text-white/45"}>{isUs ? "+" : "−"}</span>
                      <span>{p}</span>
                    </li>
                  ))}
                </ul>
              </div>
            );
          })}
        </div>
      </Shell>
    </section>
  );
}
