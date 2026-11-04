# Tabu Search: The Grid Game

> ⚠️ **No longer maintained.** This Streamlit version is kept for reference only. Use the [web version](https://vincentalboyer.github.io/Course-Apps/tabu-search/), which gives the same grids for the same codes.

A Streamlit companion for **IN2041 - Metaheuristics**, built around the
*"Tabu Search: The Grid Game"* in-class activity (`TabuSearch_Game.tex`):
find a connected path of cells on a grid that maximizes the sum of its
values, then improve it by hand-running a tiny tabu search.

## How it plays

1. **Setup** - pick a difficulty (grid size and required path length grow
   from Easy to Hard) and an optional game code, so a class can compare
   runs on the identical grid (like the slide deck's side-by-side Team 1 /
   Team 2 boards).
2. **Build your initial solution** - click a cell to start a path, then
   only its unused up/down/left/right neighbors are selectable next -
   no diagonals, no revisits. Undo, redo, and clear are all available
   while building. A dead end (no unused neighbors left) is called out
   explicitly so you know to undo and try another direction.
3. **Local search** - once your path is complete, improve it with **swap**
   moves: trade one cell in your path for one cell outside it, keeping the
   path connected. Two ways to explore the neighborhood:
   - **Manual** - click a path cell to remove, then a replacement cell to
     swap in; infeasible swaps (ones that would break the path) are
     rejected with an explanation instead of silently allowed.
   - **Auto** - one click reveals the *entire* feasible neighborhood at
     once.

   Every feasible swap is scored and added to a **candidate list** you
   choose from - including deliberately picking a *worse* solution to
   escape a local optimum, exactly like the in-class discussion.
4. **Tabu tenure** - starts at **0** (no memory), which is enough on its
   own to demonstrate cycling: escaping a local optimum with a worse move
   only for the very next best move to reverse it right back. Raising
   tenure to 1-3 forbids touching the two cells from a recent swap for
   that many iterations, breaking the cycle. Push tenure high enough
   (up to 8) and every feasible move can end up tabu at once - a
   **deadlock** - illustrating why tenure has to be tuned, not maximized.
   An **aspiration criterion** always lets a tabu move through anyway if
   it would beat the best solution found so far.
5. **Auto-Play** - watch tabu search run itself for a chosen number of
   iterations: full neighborhood each step, best admissible move taken
   automatically, stopping early on deadlock or on detecting an exact
   repeat of a past solution (cycling).
6. **Report** - best path found vs. your initial solution, a chart of
   current/best sum per iteration, and the full move history (tenure,
   tabu status, aspiration overrides, repeated solutions).

The setup screen also estimates how many possible paths exist at each
difficulty - a few thousand on Easy, well into the millions on Hard -
making the case for local/tabu search over brute force concrete.

## Run it

```bash
streamlit run streamlit-apps/TabuSearch_GridGame_App/app.py
```

## Files

- `app.py` - Streamlit UI and game state machine.
- `game_logic.py` - grid generation, swap feasibility, neighborhood
  enumeration, and tabu-list bookkeeping (pure functions, unit-tested in
  `../test_tabu_search_game_logic.py`).
- `plotting.py` - Plotly chart of path sum (current vs. best) per iteration.
