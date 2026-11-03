# Greedy Bin Packing — web version

Static port of [`Greedy_BinPacking_App`](../../Greedy_BinPacking_App), served
at `/binpacking/` on the [minigames website](../README.md).

- **Game:** drag items into the bin over 5 rounds, then download your
  results as `.xlsx`.
- **Challenge:** generate instances from a seed, difficulty and count. The
  same inputs give exactly the same Excel file as the Streamlit app.
- **Scoring:** upload a filled-in file to be graded locally in the browser.
  The format, signature check, scores and error messages match
  `excel_io.py`, and files work in both directions between the two
  versions.

| File | Port of |
|---|---|
| `js/game_logic.js` | `game_logic.py` |
| `js/excel_io.js` | `excel_io.py` (uses SheetJS from `../shared/vendor/`) |
| `js/plotting.js` | `plotting.py` (uses Plotly) |
| `js/board.js` | `frontend/index.html` (the drag-and-drop board) |
| `js/app.js` | `app.py` (the three modes) |

Random numbers, the light/dark switch and the shared styles come from
[`../shared/`](../shared).
