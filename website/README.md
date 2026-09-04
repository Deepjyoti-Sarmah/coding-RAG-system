# symbolgraph website

Marketing/landing site for [symbolgraph](../README.md) — React 19 +
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
                       # the parent repo — keep it that way.
  components/          # one component per section (Hero, Benchmark, DarkPanels, ...)
  App.jsx               # section order
  index.css             # Tailwind v4 theme tokens (@theme), fonts, line-burst decoration
```

## Design notes

- Visual direction follows two references the user supplied (Hermes Agent,
  Traycer): bold ultramarine (`#1c1cf0`) as the dominant field, an
  upright bold Bodoni Moda display serif for headlines, IBM Plex Mono for
  labels/terminal/code, alternating light (`#f6f5f0`) and near-black
  (`#0a0a0c`) panels for the feature-deep-dive sections. Every visual
  artifact (the graph diagram, the terminal transcript, the incremental-
  reindex numbers, the editor checklist) is real symbolgraph content or a
  generated pattern — none of it is a borrowed screenshot or illustration
  from either reference.
- `Hero.jsx`'s graph diagram (`ExampleGraph.jsx`) renders the codebase's
  own canonical test fixture (`login` calls `createAuth`, `run` calls
  `login`) — real product data, not stock content.
- `FeatureGrid.jsx`'s numbered #1–#6 grid is a genuine sequence (the six
  pipeline stages `sg index` actually runs, in order) — this is also the
  section that answers "how does symbolgraph work."
- `StatsBar.jsx` and the hero's install-box footnote only ever show
  measured numbers (tests passing, branch coverage, languages parsed) —
  never invented adoption/usage metrics, and there is no testimonials or
  pricing section, since symbolgraph has neither real user quotes to cite nor
  paid tiers to sell.
- Every stat, benchmark number, and CLI command comes from `data/content.js`,
  sourced from the project README/ROADMAP. If a number changes upstream,
  update it there — don't hardcode a new one in a component.
- Install commands currently point at a `git clone` + `uv tool install .`
  checkout flow. Swap `data/content.js`'s `INSTALL_TABS` export for a
  `pip install symbolgraph` once the package is published to
  PyPI.
