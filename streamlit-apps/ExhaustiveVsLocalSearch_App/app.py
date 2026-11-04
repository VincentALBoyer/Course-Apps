import os
os.environ.pop("SSLKEYLOGFILE", None)

import time

import pandas as pd
import streamlit as st

import game_logic as gl
import plotting as pl

st.set_page_config(page_title="Exhaustive vs Local Search", page_icon="🎯", layout="wide")
st.warning(
    "⚠️ **This Streamlit version is no longer maintained.** "
    "Please use the [web version](https://vincentalboyer.github.io/Course-Apps/peak-and-valley/) instead."
)

TOTAL_ROUNDS = len(gl.ROUND_XMAX)
MAX_POSSIBLE_SCORE = 1000 * TOTAL_ROUNDS
EXHAUSTIVE_FIXED_SCORE = round(1000 * gl.QUALITY_WEIGHT)
STRATEGY_LABELS = {"exhaustive": "Exhaustive", "local": "Local Search", "greedy": "Greedy"}

CONCEPTS = [
    (
        "Global vs. local optimum",
        "A **global optimum** is the best solution over the *entire* search space. A "
        "**local optimum** is only the best *within its neighborhood* — every neighbor is "
        "equal or worse, but somewhere else in the space could still be better. Local "
        "search and Greedy can only ever guarantee a local optimum, never a global one.",
    ),
    (
        "Exhaustive search",
        "Evaluates *every* candidate solution, so it's the only strategy here that "
        "guarantees the global optimum. The catch is cost: the number of candidates "
        "often grows exponentially with problem size (e.g. 2ⁿ subsets for an n-item "
        "knapsack) — fine for small problems, impossible for real ones.",
    ),
    (
        "Greedy / constructive search",
        "Builds a solution in one shot using a fast rule of thumb — in this game, "
        "literally picking one point and accepting it, no comparison at all. It's the "
        "cheapest possible strategy (one evaluation) but has no way to check or correct "
        "its choice, so solution quality is pure luck.",
    ),
    (
        "Local search & neighborhoods",
        "Start from one solution, look at its **neighborhood** (nearby candidate "
        "solutions), and move to a better neighbor if one exists — repeat until none do. "
        "That stopping point is a local optimum. A wider neighborhood sees more of the "
        "landscape per step (more likely to find an improving move) but costs more "
        "evaluations per step.",
    ),
    (
        "Restarts (multi-start search)",
        "A classic fix for getting trapped in a bad local optimum: rerun local search "
        "from a different starting point and keep the best result across all attempts. "
        "It trades extra evaluations (lower efficiency) for a better shot at the global "
        "optimum.",
    ),
    (
        "Why search strategies matter",
        "Most real optimization problems have far too many candidate solutions to check "
        "exhaustively — a 20-item knapsack already has over a million subsets, and a "
        "200-location p-median problem has more configurations than atoms are easy to "
        "count. Smart search strategies trade a guarantee of optimality for a solution "
        "that's good enough, fast enough.",
    ),
]


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------
def init_state():
    defaults = {
        "phase": "intro",
        "game_code": "",
        "seed": None,
        "rounds": None,
        "round_idx": 0,
        "round_results": [],
        "mode": None,
        "neighborhood_n": 1,
        "max_restarts": 0,
        "revealed": {},
        "round_start": None,
        "game_start": None,
        "ls_current_x": None,
        "ls_started": False,
        "ls_restarts_used": 0,
        "ls_best_x": None,
        "ls_best_y": None,
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)


def start_game(code: str, mode: str, neighborhood_n: int, max_restarts: int):
    seed_code = code.strip() or gl.new_game_code()
    st.session_state.game_code = seed_code.upper()
    st.session_state.seed = gl.code_to_seed(seed_code)
    st.session_state.rounds = gl.generate_all_rounds(st.session_state.seed)
    st.session_state.round_idx = 0
    st.session_state.round_results = []
    st.session_state.game_start = time.time()
    st.session_state.neighborhood_n = neighborhood_n
    st.session_state.max_restarts = max_restarts
    begin_round(mode)
    st.session_state.phase = "playing"


def begin_round(mode: str):
    st.session_state.mode = mode
    st.session_state.revealed = {}
    st.session_state.round_start = time.time()
    st.session_state.ls_current_x = None
    st.session_state.ls_started = False
    st.session_state.ls_restarts_used = 0
    st.session_state.ls_best_x = None
    st.session_state.ls_best_y = None


def restart_local_search():
    st.session_state.ls_restarts_used += 1
    st.session_state.ls_started = False
    st.session_state.ls_current_x = None


def finish_round(found_x: int, found_y: float):
    ys = st.session_state.rounds[st.session_state.round_idx]
    evaluations = len(st.session_state.revealed)
    result = gl.score_round(found_y, ys, evaluations)
    result.update({
        "round": st.session_state.round_idx + 1,
        "mode": st.session_state.mode,
        "n_points": len(ys),
        "evaluations": evaluations,
        "found_x": found_x,
        "found_y": found_y,
        "restarts_used": st.session_state.ls_restarts_used if st.session_state.mode == "local" else 0,
        "time": time.time() - st.session_state.round_start,
    })
    st.session_state.round_results.append(result)
    st.session_state.phase = "debrief"


def next_round_or_finish():
    if st.session_state.round_idx < TOTAL_ROUNDS - 1:
        st.session_state.round_idx += 1
        begin_round(st.session_state.mode)
        st.session_state.phase = "playing"
    else:
        st.session_state.phase = "final"


def reveal_exhaustive(x: int, ys: list):
    revealed = st.session_state.revealed
    revealed[x] = ys[x]
    if len(revealed) == len(ys):
        best_x = min(revealed, key=revealed.get)
        finish_round(best_x, revealed[best_x])


def start_local_search(x: int, ys: list):
    xmax = len(ys) - 1
    revealed = st.session_state.revealed
    revealed[x] = ys[x]
    for nb in gl.neighbor_xs(x, st.session_state.neighborhood_n, xmax):
        revealed[nb] = ys[nb]
    st.session_state.ls_current_x = x
    st.session_state.ls_started = True


def move_local_search(new_x: int, ys: list):
    xmax = len(ys) - 1
    revealed = st.session_state.revealed
    if new_x not in revealed:
        revealed[new_x] = ys[new_x]
    for nb in gl.neighbor_xs(new_x, st.session_state.neighborhood_n, xmax):
        if nb not in revealed:
            revealed[nb] = ys[nb]
    st.session_state.ls_current_x = new_x


def pick_greedy(x: int, ys: list):
    """Greedy: a single evaluation, accepted immediately - no neighborhood
    (n=0), no comparison, no take-backs."""
    st.session_state.revealed[x] = ys[x]
    finish_round(x, ys[x])


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------
def clicked_x(event):
    """Extract the x-value of a chart click from a plotly on_select event, or
    None if nothing was clicked this run."""
    try:
        points = event["selection"]["points"]
    except (TypeError, KeyError):
        return None
    if not points:
        return None
    return int(points[0]["x"])


def render_exhaustive(xmax: int, ys: list):
    revealed = st.session_state.revealed
    n_points = xmax + 1
    best_x = min(revealed, key=revealed.get) if revealed else None

    fig = pl.build_live_chart(xmax, revealed, mode="exhaustive", best_x=best_x)
    event = st.plotly_chart(
        fig, width="stretch", key=f"chart_ex_{st.session_state.round_idx}_{len(revealed)}",
        on_select="rerun", selection_mode="points",
    )

    m1, m2 = st.columns(2)
    m1.metric("Evaluations", f"{len(revealed)} / {n_points}")
    m2.metric("Best so far", f"{min(revealed.values()):.2f}" if revealed else "—")
    st.caption("Click any unrevealed point on the chart to evaluate f(x) there — every point must be checked.")

    x = clicked_x(event)
    if x is not None and 0 <= x <= xmax and x not in revealed:
        reveal_exhaustive(x, ys)
        st.rerun()


def render_local_search(xmax: int, ys: list):
    revealed = st.session_state.revealed
    n_points = xmax + 1
    n = st.session_state.neighborhood_n
    max_restarts = st.session_state.max_restarts

    if not st.session_state.ls_started:
        fig = pl.build_live_chart(xmax, revealed, mode="local")
        event = st.plotly_chart(
            fig, width="stretch",
            key=f"chart_ls_start_{st.session_state.round_idx}_{st.session_state.ls_restarts_used}",
            on_select="rerun", selection_mode="points",
        )
        if st.session_state.ls_restarts_used > 0:
            st.caption(
                f"Restart {st.session_state.ls_restarts_used}/{max_restarts}: click anywhere on the "
                "chart to choose a new starting point. Previously revealed points are still shown."
            )
        else:
            st.caption("Click anywhere on the chart to choose your starting point.")

        x = clicked_x(event)
        if x is not None and 0 <= x <= xmax:
            start_local_search(x, ys)
            st.rerun()
        return

    current_x = st.session_state.ls_current_x
    current_y = revealed[current_x]
    candidates = gl.neighbor_xs(current_x, n, xmax)
    improving = {x for x in candidates if gl.is_improving(revealed[x], current_y)}

    fig = pl.build_live_chart(
        xmax, revealed, mode="local", current_x=current_x, improving_xs=improving,
    )
    event = st.plotly_chart(
        fig, width="stretch",
        key=f"chart_ls_{st.session_state.round_idx}_{len(revealed)}_{current_x}",
        on_select="rerun", selection_mode="points",
    )

    metric_cols = st.columns(5 if max_restarts > 0 else 3)
    metric_cols[0].metric("Current position", f"x = {current_x}")
    metric_cols[1].metric("Current value", f"{current_y:.2f}")
    metric_cols[2].metric("Evaluations", f"{len(revealed)} / {n_points}")
    if max_restarts > 0:
        metric_cols[3].metric("Restarts used", f"{st.session_state.ls_restarts_used} / {max_restarts}")
        best_y = st.session_state.ls_best_y
        metric_cols[4].metric("Best so far", f"{min(best_y, current_y):.2f}" if best_y is not None else f"{current_y:.2f}")

    if not improving:
        if st.session_state.ls_best_y is None or current_y < st.session_state.ls_best_y:
            st.session_state.ls_best_x = current_x
            st.session_state.ls_best_y = current_y
        best_x, best_y = st.session_state.ls_best_x, st.session_state.ls_best_y
        restarts_left = max_restarts - st.session_state.ls_restarts_used

        if restarts_left > 0:
            st.warning(
                f"🪤 Attempt {st.session_state.ls_restarts_used + 1} reached a local optimum at "
                f"x={current_x} (f={current_y:.2f}). Best result so far: f={best_y:.2f} at x={best_x}. "
                f"{restarts_left} restart(s) left."
            )
            c1, c2 = st.columns(2)
            if c1.button("🔄 Restart from a new point", width="stretch"):
                restart_local_search()
                st.rerun()
            if c2.button(f"🏁 Accept best result (f={best_y:.2f})", type="primary", width="stretch"):
                finish_round(best_x, best_y)
                st.rerun()
        else:
            if best_x == current_x:
                st.success(f"🏁 Local optimum reached at x={current_x} (f={current_y:.2f}) — neither neighbor is better. Round complete!")
            else:
                st.success(
                    f"🏁 Local optimum reached at x={current_x} (f={current_y:.2f}). Your best across all "
                    f"attempts was f={best_y:.2f} at x={best_x} — that's what counts. Round complete!"
                )
            if st.button("See round results ▶", type="primary"):
                finish_round(best_x, best_y)
                st.rerun()
        return

    st.caption("Click the highlighted neighbor on the chart to move there.")
    x = clicked_x(event)
    if x is not None and x in improving:
        move_local_search(x, ys)
        st.rerun()
    elif x is not None:
        st.toast("That point isn't a strictly better neighbor — pick a highlighted point instead.", icon="⚠️")


def render_greedy(xmax: int, ys: list):
    revealed = st.session_state.revealed
    fig = pl.build_live_chart(xmax, revealed, mode="greedy")
    event = st.plotly_chart(
        fig, width="stretch", key=f"chart_greedy_{st.session_state.round_idx}",
        on_select="rerun", selection_mode="points",
    )
    st.caption("Click any point on the chart — that's your final answer, no comparison, no take-backs.")

    x = clicked_x(event)
    if x is not None and 0 <= x <= xmax:
        pick_greedy(x, ys)
        st.rerun()


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
init_state()

with st.sidebar:
    st.markdown("### 🎯 Search Strategies Minigame")
    if st.session_state.phase != "intro":
        st.divider()
        st.metric("Game code", st.session_state.game_code)
        if st.button("↺ Restart"):
            st.session_state.phase = "intro"
            st.rerun()
    st.divider()
    st.markdown("### 📘 Concepts")
    st.caption("Click any topic for a quick explanation.")
    for title, body in CONCEPTS:
        with st.expander(title):
            st.markdown(body)

if st.session_state.phase == "intro":
    st.title("🎯 Exhaustive vs. Local Search")
    st.caption("A companion minigame for IN2041 Session 2 — Searching Strategies for Optimization")
    st.markdown(
        "Each round hides a function **f(x)** behind a wall of unrevealed points, and you try "
        "to land on the lowest value. The x-axis **grows every round**, just like the "
        "combinatorial explosion of solutions we discussed in class. Pick your strategy once "
        "below — you'll play **all 5 rounds** with it."
    )
    with st.expander("How scoring works", expanded=False):
        st.markdown(f"""
- **Exhaustive search** evaluates every point, so it always finds the true best value —
  but it never earns an efficiency bonus. Its score is therefore always a fixed
  **{EXHAUSTIVE_FIXED_SCORE} points** per round: guaranteed, never impressive.
- **Local search** starts wherever you pick and only moves to a neighbor that's *strictly*
  better than where you are. It stops the instant neither neighbor improves — that's a
  **local optimum**, which may or may not be the **global** one.
- **Greedy** picks one point and commits — a single evaluation, no comparison, no
  neighborhood at all (think of it as local search with a neighborhood of size 0). It's
  the cheapest possible strategy, so it can score very high efficiency — but quality is
  pure luck, with zero guarantee of even a local optimum.
- Each round's score = 65% **solution quality** (how close your result is to the true best)
  + 35% **efficiency** (how few points you had to reveal), scaled to 1000. Local search and
  Greedy can beat exhaustive's fixed score by converging fast — or fall short if they land poorly.
""")

    mode_choice = st.radio(
        "Strategy for all 5 rounds", ["Exhaustive Search", "Local Search", "Greedy"], horizontal=True,
    )
    strategy_captions = {
        "Exhaustive Search": "Exhaustive: click every point one by one — guaranteed to find the best, costs the most evaluations.",
        "Local Search": "Local Search: pick a start, step to a strictly better neighbor each time — stops at the first local optimum.",
        "Greedy": "Greedy: click one point and that's your final answer — no exploration, no comparison, no take-backs.",
    }
    st.caption(strategy_captions[mode_choice])

    neighborhood_n, max_restarts = 1, 0
    if mode_choice == "Local Search":
        with st.expander("Advanced settings", expanded=False):
            neighborhood_n = st.radio(
                "Neighborhood size (closest neighbors per side)", gl.NEIGHBORHOOD_CHOICES, horizontal=True,
                help="How many candidate points are revealed on each side of your current position. "
                     "2 reveals more of the landscape per step (easier to find an improving move) but "
                     "costs more evaluations, hurting efficiency.",
            )
            max_restarts = st.slider(
                "Restarts allowed", min_value=0, max_value=gl.MAX_RESTARTS_CAP, value=0,
                help="If you get trapped in a local optimum, restart from a new point instead of ending "
                     "the round immediately. Your best result across all attempts counts toward quality — "
                     "but every restart adds to your evaluation cost, hurting efficiency.",
            )

    code = st.text_input(
        "Game code (optional)", value="", placeholder="Leave blank for a random code", max_chars=12,
        help="Use the same code as a classmate to play on identical landscapes.",
    )
    mode_map = {"Exhaustive Search": "exhaustive", "Local Search": "local", "Greedy": "greedy"}
    if st.button("▶ Start Game", type="primary"):
        start_game(code, mode_map[mode_choice], neighborhood_n, max_restarts)
        st.rerun()

elif st.session_state.phase == "playing":
    idx = st.session_state.round_idx
    xmax = gl.ROUND_XMAX[idx]
    n_points = xmax + 1
    ys = st.session_state.rounds[idx]

    top = st.columns([2, 1.2, 0.9, 0.9])
    top[0].subheader(f"Round {idx + 1} / {TOTAL_ROUNDS} — x from 0 to {xmax} ({n_points} points)")
    top[1].metric("Strategy", STRATEGY_LABELS[st.session_state.mode])
    total_score_so_far = sum(r["score"] for r in st.session_state.round_results)
    top[2].metric("Score so far", f"{total_score_so_far}")
    top[3].metric("Total time", f"{time.time() - st.session_state.game_start:.0f}s")
    st.progress(idx / TOTAL_ROUNDS)
    st.divider()

    if st.session_state.mode == "exhaustive":
        render_exhaustive(xmax, ys)
    elif st.session_state.mode == "local":
        render_local_search(xmax, ys)
    else:
        render_greedy(xmax, ys)

elif st.session_state.phase == "debrief":
    idx = st.session_state.round_idx
    ys = st.session_state.rounds[idx]
    result = st.session_state.round_results[-1]

    global_idx = min(range(len(ys)), key=lambda i: ys[i])
    local_idxs = set(gl.local_minima_indices(ys)) - {global_idx}
    player_x = result["found_x"]

    st.subheader(f"Round {idx + 1} results — {STRATEGY_LABELS[result['mode']]}")

    if player_x == global_idx:
        st.success("🎉 You found the **global optimum**!")
    elif result["mode"] == "greedy":
        st.warning(f"🎲 Your greedy pick landed at x={player_x} — not the best. The global minimum was at x={global_idx}.")
    else:
        st.warning(f"🪤 You landed on a **local optimum** at x={player_x}. The global minimum was at x={global_idx}.")

    fig = pl.build_debrief_chart(ys, global_idx, local_idxs, player_x)
    st.plotly_chart(fig, width="stretch", key=f"debrief_{idx}")

    show_restarts = result["mode"] == "local" and st.session_state.max_restarts > 0
    cols = st.columns(5 if show_restarts else 4)
    cols[0].metric("Evaluations used", f"{result['evaluations']} / {result['n_points']}")
    cols[1].metric("Quality", f"{result['quality'] * 100:.0f}%")
    cols[2].metric("Efficiency", f"{result['efficiency'] * 100:.0f}%")
    cols[3].metric("Round score", result["score"])
    if show_restarts:
        cols[4].metric("Restarts used", f"{result['restarts_used']} / {st.session_state.max_restarts}")
    st.caption(f"Round time: {result['time']:.1f}s")

    label = "Next Round ▶" if idx < TOTAL_ROUNDS - 1 else "See Final Results 🏁"
    if st.button(label, type="primary"):
        next_round_or_finish()
        st.rerun()

elif st.session_state.phase == "final":
    st.title("🏁 Game Complete!")

    total_score = sum(r["score"] for r in st.session_state.round_results)
    total_time = sum(r["time"] for r in st.session_state.round_results)

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Score", f"{total_score} / {MAX_POSSIBLE_SCORE}")
    c2.metric("Total Time", f"{total_time:.1f}s")
    c3.metric("Game Code", st.session_state.game_code)
    st.caption("Share this game code with a classmate to compare results on the exact same 5 landscapes.")

    df = pd.DataFrame(st.session_state.round_results)
    cols_to_show = ["round", "mode", "n_points", "evaluations", "quality", "efficiency", "score", "time"]
    col_names = ["Round", "Strategy", "Points", "Evaluations", "Quality", "Efficiency", "Score", "Time (s)"]
    if st.session_state.mode == "local" and st.session_state.max_restarts > 0:
        cols_to_show.append("restarts_used")
        col_names.append("Restarts")
    df_display = df[cols_to_show].copy()
    df_display["mode"] = df_display["mode"].map(STRATEGY_LABELS)
    df_display["quality"] = (df_display["quality"] * 100).round(0).astype(int).astype(str) + "%"
    df_display["efficiency"] = (df_display["efficiency"] * 100).round(0).astype(int).astype(str) + "%"
    df_display["time"] = df_display["time"].round(1)
    df_display.columns = col_names
    st.dataframe(df_display, width="stretch", hide_index=True)

    c1, c2 = st.columns(2)
    if c1.button("🔁 Replay Same Code", width="stretch"):
        start_game(st.session_state.game_code, st.session_state.mode, st.session_state.neighborhood_n, st.session_state.max_restarts)
        st.rerun()
    if c2.button("🎲 New Random Landscapes", width="stretch"):
        start_game("", st.session_state.mode, st.session_state.neighborhood_n, st.session_state.max_restarts)
        st.rerun()
    st.caption("Both replay with the same strategy and settings you just used. Use ↺ Restart in the sidebar to pick different ones.")
