# Greedy Bin Packing — HTML version

A static (HTML/CSS/JavaScript) version of
[`Greedy_BinPacking_App`](../Greedy_BinPacking_App), published on GitHub Pages:
**https://vincentalboyer.github.io/MyStreamlitApp/**

Everything runs in each student's browser, so there is no server to slow
down when a whole class plays at once. Nothing is uploaded anywhere: Scoring
mode reads the Excel file locally.

## Same results as the Streamlit app

- **Instances:** `js/rng.js` is a port of Python's `random.Random`. The same
  seed, difficulty and count give exactly the same instances, so a seed
  handed out in either version produces the same file.
- **Files:** the Excel format (`items` / `meta` / `notes` sheets) and its
  signature are the same, so files move freely between the two versions.
- **Grading:** feasibility checks, scores and error messages match the
  Python `excel_io.py`.

Differences from the Streamlit version:

- The Game's final report has no "Describe your strategy" box and no `.txt`
  report download.
- The Elapsed timer ticks live.
- The Scoring plot lets Plotly choose its axis ticks.
- The page warns before you leave in the middle of a game.
- A ☀️/🌙 button in the top bar switches between light and dark mode. The
  page starts from the system setting, and each browser remembers its own
  choice.

## Layout

| File | Port of |
|---|---|
| `js/rng.js` | Python's `random` (MT19937, `uniform`, `normalvariate`, `round`) |
| `js/game_logic.js` | `game_logic.py` |
| `js/excel_io.js` | `excel_io.py` (uses SheetJS) |
| `js/plotting.js` | `plotting.py` (uses Plotly) |
| `js/board.js` | `frontend/index.html` (the drag-and-drop board) |
| `js/app.js` | `app.py` (the three modes) |
| `vendor/` | SheetJS 0.20.3 and Plotly basic 2.35.2, saved here so the page needs no CDN |

There is no build step. To try it locally, run
`python3 -m http.server -d Greedy_BinPacking_HTML 8000` from the repo root and
open http://localhost:8000. Opening `index.html` directly from disk also
works.

## Deployment

`.github/workflows/pages-binpacking.yml` publishes this folder whenever a
change to it is pushed to `main`. One-time setup: in the repo, go to
**Settings → Pages → Build and deployment → Source** and choose
**GitHub Actions**.

Drag and drop uses the browser's built-in HTML5 drag-and-drop, which works
with a mouse or trackpad but not on phones or tablets (the same as the
Streamlit version).
