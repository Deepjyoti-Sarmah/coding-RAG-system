import { PLATFORMS } from "../data/content";

// Hermes platform cards: each has a full-bleed faint duotone engraving texture
// (white on blue, very low opacity, with blueprint-like halftone), centred title
// and a crisp white CTA. We recreate that with inline SVG patterns — high contrast
// card frame, no rounded-xl pastel.
function PlatformTexture({ variant }) {
  if (variant === "macOS") {
    return (
      <svg className="absolute inset-0 h-full w-full opacity-[0.14]" viewBox="0 0 400 320" preserveAspectRatio="xMidYMid slice">
        <defs>
          <pattern id="mac-pat" width="18" height="18" patternUnits="userSpaceOnUse"><circle cx="9" cy="9" r="1" fill="white" opacity="0.9" /></pattern>
        </defs>
        <rect width="400" height="320" fill="url(#mac-pat)" />
        {/* blueprint wing */}
        <path d="M 40 200 C 80 120, 160 80, 240 110 C 300 130, 340 180, 360 240" fill="none" stroke="white" strokeWidth="0.7" opacity="0.9" />
        <path d="M 40 220 C 90 150, 170 110, 250 140" fill="none" stroke="white" strokeWidth="0.5" opacity="0.6" />
        <ellipse cx="210" cy="150" rx="82" ry="64" fill="none" stroke="white" strokeWidth="0.6" opacity="0.35" />
        <path d="M 140 90 L 280 210 M 280 90 L 140 210" stroke="white" strokeWidth="0.4" opacity="0.22" />
      </svg>
    );
  }
  if (variant === "Linux") {
    return (
      <svg className="absolute inset-0 h-full w-full opacity-[0.13]" viewBox="0 0 400 320" preserveAspectRatio="xMidYMid slice">
        <rect width="400" height="320" fill="none" />
        {/* terminal grid + radial */}
        <g stroke="white" strokeWidth="0.5" opacity="0.9">
          {Array.from({ length: 9 }).map((_, i) => (
            <line key={i} x1={40 + i * 38} y1="60" x2={40 + i * 38} y2="260" opacity={0.22 - i * 0.015} />
          ))}
        </g>
        <circle cx="200" cy="160" r="72" fill="none" stroke="white" strokeWidth="0.7" opacity="0.5" />
        <circle cx="200" cy="160" r="96" fill="none" stroke="white" strokeWidth="0.4" opacity="0.25" />
        <path d="M 110 160 L 290 160 M 200 70 L 200 250" stroke="white" strokeWidth="0.45" opacity="0.3" />
        <text x="200" y="165" textAnchor="middle" fontFamily="IBM Plex Mono, monospace" fontSize="22" fill="white" opacity="0.18">$</text>
      </svg>
    );
  }
  return (
    <svg className="absolute inset-0 h-full w-full opacity-[0.14]" viewBox="0 0 400 320" preserveAspectRatio="xMidYMid slice">
      <defs>
        <pattern id="win-pat" width="28" height="28" patternUnits="userSpaceOnUse"><rect width="13" height="13" fill="white" opacity="0.85" /><rect x="15" y="15" width="13" height="13" fill="white" opacity="0.85" /></pattern>
      </defs>
      <rect width="400" height="320" fill="url(#win-pat)" opacity="0.08" />
      <rect x="120" y="92" width="160" height="136" fill="none" stroke="white" strokeWidth="0.8" opacity="0.9" />
      <line x1="200" y1="92" x2="200" y2="228" stroke="white" strokeWidth="0.6" opacity="0.9" />
      <line x1="120" y1="160" x2="280" y2="160" stroke="white" strokeWidth="0.6" opacity="0.9" />
      <path d="M 70 80 C 140 60, 260 60, 330 80" fill="none" stroke="white" strokeWidth="0.5" opacity="0.32" />
    </svg>
  );
}

export default function PlatformCards() {
  return (
    <section className="bg-blue px-6 pb-10 pt-2">
      <div className="mx-auto max-w-[1280px]">
        <p className="text-center font-mono text-[10px] font-normal uppercase tracking-[0.22em] text-white">
          Native app
        </p>
        <h2 className="mt-2 text-center font-display text-[34px] font-[400] uppercase leading-[0.95] tracking-[-0.03em] text-white sm:text-[44px]">
          symbolgraph FOR MACOS,
          <br className="sm:hidden" /> WINDOWS &amp; LINUX
        </h2>

        <div className="mx-auto mt-7 grid max-w-5xl gap-3 sm:grid-cols-3">
          {PLATFORMS.map((p) => (
            <div
              key={p.name}
              className="relative flex min-h-[280px] flex-col items-center justify-center overflow-hidden border border-white bg-blue px-6 py-8 text-center"
            >
              <PlatformTexture variant={p.name} />
              <div className="relative">
                <p className="font-mono text-[10px] font-normal uppercase tracking-[0.18em] text-white">{p.detail}</p>
                <p className="mt-2 font-display text-[32px] font-[400] leading-none tracking-[-0.02em] text-white sm:text-[36px]">
                  {p.name}
                </p>
                <a
                  href="#install"
                  className="mt-4 inline-flex items-center gap-1.5 bg-white px-4 py-2 font-mono text-[10px] font-normal uppercase tracking-[0.12em] text-blue transition hover:bg-white/90"
                >
                  {p.name === "Linux" ? "▣ Install via terminal" : p.name === "Windows" ? "▣ Download desktop app" : " Download desktop app"}
                </a>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
