# Optimization Minigames website

Static (HTML/CSS/JavaScript) versions of the classroom minigames, published
on GitHub Pages at **https://vincentalboyer.github.io/Course-Apps/**.

Everything runs in each student's browser, so a whole class playing at once
puts no load on any server. There is nothing to install and no sign-in.

| Path | Game | Ported from |
|---|---|---|
| `/` | Home page with a card for each game | — |
| `/binpacking/` | 📦 Greedy Bin Packing | [`Greedy_BinPacking_App`](../streamlit-apps/Greedy_BinPacking_App) |
| `/ga-wordgame/` | 🧬 GA Word Game | [`GA_WordGame_App`](../streamlit-apps/GA_WordGame_App) |
| `/tabu-search/` | 🔀 Tabu Search: The Grid Game | [`TabuSearch_GridGame_App`](../streamlit-apps/TabuSearch_GridGame_App) |
| `/peak-and-valley/` | ⛰️ Peak and Valley | [`ExhaustiveVsLocalSearch_App`](../streamlit-apps/ExhaustiveVsLocalSearch_App) |

Home page links ending in `#game`, `#challenge` or `#scoring` (the old bin
packing links) open that mode of `/binpacking/`.

## Same game codes as the Streamlit apps

A game code (or seed) gives the same game here as in the Streamlit version:

- **Bin packing, GA, Tabu:** `shared/rng.js` is an exact port of Python's
  `random.Random`, including `choice`, `choices`, `sample` and `randint`.
  The page also reproduces Python's `round()` and its compensated float
  `sum()`. Instances, starting populations and grids match bit for bit.
- **Peak and Valley:** `shared/rng.js` also ports NumPy's `SeedSequence`,
  `PCG64` and `Generator.uniform` / `.normal`. Uniform draws are
  bit-identical. Normal draws differ by about 1e-11 because NumPy's
  ziggurat tables are slightly different. Across 1,500 test landscapes, the
  global minimum, local minima, shown values and scores were all identical.

## Layout

```
website/
  index.html            home page
  shared/               used by every game
    base.css            theme tokens (light/dark), layout, controls
    ui.js               light/dark toggle, toasts, tables, Plotly helper
    rng.js, sha256.js   Python/NumPy-compatible random numbers, code → seed
    vendor/             Plotly basic 2.35.2, SheetJS 0.20.3 (no CDN needed)
  <game>/index.html     one folder per game, with its own js/ and css/
```

There is no build step. To try it locally, run the following from the repo
root, then open http://localhost:8000:

```bash
python3 -m http.server -d website 8000
```

Asset links end in `?v=dev`. The deploy replaces that with the commit hash,
so browsers never mix an old cached page with new scripts.

## Deployment

`.github/workflows/pages.yml` publishes this folder whenever a change to it
is pushed to `main`. Pages lets browsers cache files for up to 10 minutes,
so publish updates at least 10 minutes before a class.

## Differences from the Streamlit versions

- **Peak and Valley** is the new name of "Exhaustive vs. Local Search". Its
  "Your result" ring is now visible on the debrief chart (it was drawn
  transparent).
- **Bin packing:** the Game's final report has no strategy text box and no
  `.txt` download.
- **All games:**
  - Timers tick live.
  - A light/dark switch sits in the top bar. The page starts from the system
    setting, and each browser remembers its own choice.
  - The page warns before you leave in the middle of a game.
- **GA and Tabu:** auto-play animates in the browser. Tabu keeps the reason
  auto-play stopped (deadlock or cycling) on screen.
- Drag and drop (bin packing) needs a mouse or trackpad. Click-based games
  (GA, Tabu, Peak and Valley) also work on tablets and phones.
