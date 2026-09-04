# CKG website

Marketing/landing site for [Code Knowledge Graph](../README.md) — React 19 +
Vite + Tailwind CSS v4.

## Run it

```bash
npm install
npm run dev       # http://localhost:5173
```

```bash
npm run build      # → dist/
npm run preview    # serve the production build locally
```

## Structure

```
src/
  data/content.js     # every number/command on the page — edit this, not the JSX,
                       # to update copy. Sourced from ../README.md and
                       # ../benchmarks/results/*.json — keep it that way.
  components/          # one component per section (Hero, Benchmark, ...)
  App.jsx               # section order
  index.css             # Tailwind v4 theme tokens (@theme), fonts, grain/line-burst decorations
```

## Design notes

- Built with the `frontend-design` skill's plan-first process. Concept:
  blueprint/drafting-table, grounded in the fact that CKG's product *is*
  a graph — not a generic dark-SaaS template. Palette: warm paper
  (`#ece8dc`), ink (`#1b2430`), one accent used deliberately once
  (`#2456c9`, "blueprint blue"). Type: IBM Plex Mono (headlines, labels,
  code) + IBM Plex Sans (body) — one coordinated superfamily, two roles.
- The hero's small graph diagram (`ExampleGraph.jsx`) renders the
  codebase's own canonical test fixture (`login` calls `createAuth`,
  `run` calls `login`) — real product data, not stock content.
- The numbered sequence in `Architecture.jsx` is a genuine sequence (the
  six pipeline stages `ckg index` actually runs in order) — numbering
  elsewhere was deliberately avoided since it isn't earned there.
- Every stat, benchmark number, and CLI command comes from `data/content.js`,
  sourced from the project README/ROADMAP. If a number changes upstream,
  update it there — don't hardcode a new one in a component.
- Install commands currently point at a `git clone` + `uv tool install .`
  checkout flow. Swap `data/content.js`'s `INSTALL` export for a `pip
  install code-knowledge-graph` once the package is published to PyPI
  (see the parent repo's `ROADMAP.md` `P6-8`).
