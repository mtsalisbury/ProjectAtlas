# Project Atlas Design System v1

This update establishes one shared visual system without changing deployment or repository architecture.

## Files
- `docs/assets/css/atlas.css` — shared colors, typography, spacing, buttons, cards, navigation, footer, paper layout, and responsive rules.
- `docs/assets/js/site.js` — mobile navigation and automatic footer year.
- `docs/index.html` — refreshed homepage using the shared system.
- `docs/research/index.html` — refreshed research hub using the shared system.
- `docs/page-template.html` — reusable starting template for future static pages.

## Rules
1. Keep GitHub Pages on `main /docs`.
2. Do not add a second site directory or build system.
3. New pages link to `assets/css/atlas.css` and `assets/js/site.js`, adjusting relative paths as needed.
4. Reuse existing classes before adding page-specific CSS.
5. Preserve `docs/index.html` as the publishing entry point.
