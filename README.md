# CONVERTS Creator Leaderboard

Public standings page for every client video in the CONVERTS™ system.

**Live at https://contentleaderboard.wearelaneymedia.com**

## How it stays current

`build/build_ci.py` pulls the CONVERTS Client Data database from Notion and
writes `index.html` at the repo root from `build/template.html`. The GitHub
Action in `.github/workflows/refresh.yml` runs that every three hours and
commits the result.

A Cloudflare Worker (`content-leaderboard`, source in
`~/Claude Code/content-leaderboard-worker`) serves `index.html` and the two
font files from Cloudflare's edge on the custom domain, so a rebuild reaches
the live page on its own. `https://kendalaney.github.io/converts-leaderboard/`
still serves the same build.

## Styling

The page carries the design system from the CONVERTS asset library at
assets.wearelaneymedia.com: the Laney Media five colour palette, Awesome
Serif for headings, and Jost, Archivo Narrow and Archivo for eyebrows,
labels and body. Cream is the default and dark is the opt in.

Edit `build/template.html`, never `index.html` directly. The next refresh
overwrites `index.html`.
