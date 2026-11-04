# Exhaustive vs. Local Search — Minigame

> ⚠️ **No longer maintained.** This Streamlit version is kept for reference only. Use the web version, [Peak and Valley](https://vincentalboyer.github.io/Course-Apps/peak-and-valley/), which gives the same games for the same codes.

A Streamlit companion for **IN2041 Session 2** ("Computational Complexity and
Basic Optimization Concepts"), built around the *"An illustrative example of
Exhaustive vs Local Search"* slide: a hidden 1-D function `f(x)` with a global
minimum and a few local-minima traps.

## How it plays

- 5 rounds, each hiding a randomly generated `f(x)` landscape. The x-axis
  **grows every round** (11 → 16 → 21 → 26 → 31 candidate points), echoing the
  combinatorial-explosion discussion earlier in the session.
- Each round, choose a strategy:
  - **Exhaustive search** — click every x one by one; f(x) is revealed each
    time; guaranteed to find the true best value, at the cost of every
    evaluation.
  - **Local search** — pick a starting x (its two neighbors are revealed too),
    then repeatedly step to whichever neighbor is *strictly* better. The round
    ends the instant neither neighbor improves — a local optimum, which may or
    may not be the global one.
- After each round, a debrief chart reveals the full landscape with the true
  global minimum, every local minimum, and where you landed — mirroring the
  professor's own slide legend.
- Round score = 65% solution quality + 35% search efficiency (fewer reveals),
  scaled to 1000 points. Exhaustive always scores a fixed baseline; local
  search can beat it by converging fast, or fall short if trapped.
- A **game code** seeds all 5 landscapes — share it with classmates to compare
  results on identical rounds, or leave it blank for a random one.

## Run it

```bash
streamlit run streamlit-apps/ExhaustiveVsLocalSearch_App/app.py
```

## Files

- `app.py` — Streamlit UI and game state machine.
- `game_logic.py` — landscape generation, seeding, and scoring (pure
  functions, unit-tested in `../test_search_game_logic.py`).
- `plotting.py` — Plotly chart builders for the live board and round debrief.
