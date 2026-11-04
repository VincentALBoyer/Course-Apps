import os
os.environ.pop("SSLKEYLOGFILE", None)

import time

import pandas as pd
import streamlit as st

import game_logic as gl
import plotting as pl

st.set_page_config(page_title="Tabu Search Grid Game", page_icon="\U0001f500", layout="wide")
st.warning(
    "⚠️ **This Streamlit version is no longer maintained.** "
    "Please use the [web version](https://vincentalboyer.github.io/Course-Apps/tabu-search/) instead."
)

COLOR_PATH = "#2a78d6"     # blue - a cell currently in the path (unchanged in a selection)
COLOR_REMOVED = "#eb6834"  # orange - the cell a selected candidate would remove
COLOR_ADDED = "#1a9c5e"    # green - the cell a selected candidate would add

# Streamlit's default "primary" button color (this app ships no theme config)
# is a red that clashes with COLOR_PATH - grid cells rendered as real (enabled)
# primary buttons need to match the blue used on static path cells, so the
# app's whole primary-button color is overridden to COLOR_PATH here.
st.markdown(
    f"""
    <style>
    button[kind="primary"], [data-testid="stBaseButton-primary"] {{
        background-color: {COLOR_PATH} !important;
        border-color: {COLOR_PATH} !important;
        color: #fff !important;
    }}
    button[kind="primary"]:hover, [data-testid="stBaseButton-primary"]:hover {{
        background-color: #1f5fa8 !important;
        border-color: #1f5fa8 !important;
        color: #fff !important;
    }}
    button[kind="primary"]:disabled, [data-testid="stBaseButton-primary"]:disabled {{
        background-color: {COLOR_PATH} !important;
        border-color: {COLOR_PATH} !important;
        color: #fff !important;
        opacity: 0.35 !important;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

CONCEPTS = [
    (
        "Two swap moves: replace & shift",
        "A **replace** trades one cell currently in your path for one cell outside it, at a chosen "
        "position - the grid version of the slide's 'Replace' move. It's only **feasible** if the "
        "new cell keeps the path connected: adjacent (no diagonals) to whichever path neighbors sit "
        "on either side of that position. Any position can be replaced, including the very first cell "
        "(the **head**) or the very last one (the **tail**) - an endpoint only needs to stay connected "
        "to its single neighbor, not two.\n\n"
        "A **shift** only applies at an extremity, matching the slide's 'Shift' move: instead of "
        "replacing the head or tail in place, drop it entirely and grow the path from the "
        "**opposite** end with a cell adjacent to *that* extremity. Both moves keep the path "
        "connected; most cells you could imagine picking are infeasible for either one - the grid's "
        "geometry does most of the filtering for you.",
    ),
    (
        "Neighborhood",
        "The **neighborhood** of your current path is every feasible swap you could make from it - "
        "one change away. Local search moves from neighborhood to neighborhood, one step at a time; "
        "a bigger neighborhood means more options per step, at the cost of more to evaluate.",
    ),
    (
        "Tabu list & tenure",
        "The **tabu list** remembers the cell removed by each of your last few moves and temporarily "
        "forbids bringing it back in. **Tenure** is how many future iterations that ban lasts. "
        "Tenure = 0 means no memory at all - nothing is ever forbidden.",
    ),
    (
        "Why tenure = 0 can cycle",
        "With no memory, the best available move right after escaping a local optimum can simply be "
        "**reversing your last swap** - undoing the very move that got you out, straight back into "
        "the trap. Tenure exists specifically to block that reversal for a while, forcing the search "
        "into genuinely new territory.",
    ),
    (
        "Escaping local optima on purpose",
        "At a **local optimum**, every feasible swap makes things worse. Local search would simply "
        "stop here. Tabu search doesn't: it accepts the *least-bad* move anyway (even a worsening "
        "one), then relies on the tabu list to stop it from immediately climbing back to the same "
        "spot - that's how it explores past a trap that pure hill-climbing can't.",
    ),
    (
        "Aspiration criterion",
        "A rigid tabu list can accidentally forbid a genuinely great move. The **aspiration "
        "criterion** is the escape clause: a tabu move is allowed anyway if it would produce a new "
        "**best solution overall** - the one exception worth breaking the rule for.",
    ),
    (
        "Deadlock",
        "If tenure is set too high relative to the neighborhood size, *every* feasible move can end "
        "up tabu at once, with nothing good enough to trigger aspiration either - a **deadlock** with "
        "no admissible move left. It's a real failure mode, not just a corner case: tune tenure "
        "relative to how big your neighborhood actually is.",
    ),
    (
        "Why not just brute force it?",
        "The number of possible paths grows roughly exponentially with path length - a few thousand "
        "on Easy, but well into the millions on Hard (see the setup screen's estimate). Exhaustive "
        "search still guarantees the true optimum, but it stops being realistic long before Hard "
        "difficulty. Tabu search trades that guarantee for a search that stays fast at any size.",
    ),
]


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------
def init_state():
    defaults = {
        "phase": "setup",
        "game_id": 0,
        "game_code": "",
        "difficulty": "easy",
        "grid_size": 6,
        "path_length": 5,
        "grid": [],
        "start_time": None,
        "build_path": [],
        "redo_stack": [],
        "current_path": [],
        "previous_path": None,
        "initial_path": [],
        "initial_sum": 0,
        "best_path": [],
        "best_sum": 0,
        "iteration": 0,
        "tenure": 0,
        "tabu_remaining": {},
        "tabu_source": {},
        "neighbor_mode": "manual",
        "candidate_list": [],
        "selected_out_pos": None,
        "selected_candidate_idx": None,
        "history": [],
        "visited_paths": set(),
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)


def fmt_cell(cell: tuple) -> str:
    """1-indexed (row,col) display, matching the slide's own path notation."""
    return f"({cell[0] + 1},{cell[1] + 1})"


def start_game(difficulty_key: str, code: str):
    diff = gl.DIFFICULTIES[difficulty_key]
    seed_code = (code or "").strip() or gl.new_game_code()
    seed = gl.code_to_seed(seed_code)
    rng = gl.make_rng(seed)
    grid = gl.generate_grid(diff["grid_size"], rng)

    game_id = st.session_state.get("game_id", 0) + 1
    st.session_state.update({
        "game_id": game_id,
        "game_code": seed_code.upper(),
        "difficulty": difficulty_key,
        "grid_size": diff["grid_size"],
        "path_length": diff["path_length"],
        "grid": grid,
        "phase": "construct",
        "build_path": [],
        "redo_stack": [],
        "start_time": time.time(),
    })


# ---------------------------------------------------------------------------
# Construction phase
# ---------------------------------------------------------------------------
def handle_construct_click(cell):
    st.session_state.build_path.append(cell)
    st.session_state.redo_stack = []


def undo_construct():
    if st.session_state.build_path:
        st.session_state.redo_stack.append(st.session_state.build_path.pop())


def redo_construct():
    if st.session_state.redo_stack:
        st.session_state.build_path.append(st.session_state.redo_stack.pop())


def clear_construct():
    st.session_state.build_path = []
    st.session_state.redo_stack = []


def confirm_initial_solution():
    ss = st.session_state
    path = list(ss.build_path)
    total = gl.path_sum(ss.grid, path)
    ss.update({
        "current_path": path,
        "previous_path": None,
        "initial_path": path,
        "initial_sum": total,
        "best_path": path,
        "best_sum": total,
        "iteration": 0,
        "tenure": 0,
        "tabu_remaining": {},
        "tabu_source": {},
        "neighbor_mode": "manual",
        "candidate_list": [],
        "selected_out_pos": None,
        "selected_candidate_idx": None,
        "history": [{
            "iteration": 0, "sum": total, "best": total, "delta": 0,
            "tenure": 0, "tabu": False, "aspiration": False, "repeat": False,
        }],
        "visited_paths": {tuple(path)},
        "phase": "search",
    })


# ---------------------------------------------------------------------------
# Search phase
# ---------------------------------------------------------------------------
def candidate_already_found(candidate_list: list, pos: int, in_cell: tuple, move_type: str) -> bool:
    """True if this exact (position, replacement cell, move type) already
    exists in the candidate list - i.e. it would re-identify a solution
    already found by a previous move this round, not add anything new.
    move_type matters because the same (pos, in_cell) pair can produce two
    genuinely different paths - a replace and a shift - at an extremity."""
    return any(
        c["pos"] == pos and c["in_cell"] == in_cell and c["move_type"] == move_type
        for c in candidate_list
    )


def new_valid_moves(ss, cell: tuple) -> list:
    """Which move types ('replace', 'shift') would produce a genuinely new
    candidate if `cell` is chosen as the swap-in target for the currently
    selected out-position - feasible, and not a duplicate of a candidate
    already discovered this round. A cell can offer both at once: e.g. at
    an extremity, one candidate cell might be a legal in-place replacement
    AND a legal shift target for the opposite end."""
    pos = ss.selected_out_pos
    if pos is None:
        return []
    moves = []
    if gl.swap_is_feasible(ss.current_path, pos, cell) and not candidate_already_found(
        ss.candidate_list, pos, cell, "replace"
    ):
        moves.append("replace")
    if gl.shift_is_feasible(ss.current_path, pos, cell) and not candidate_already_found(
        ss.candidate_list, pos, cell, "shift"
    ):
        moves.append("shift")
    return moves


def is_new_valid_target(ss, cell: tuple) -> bool:
    """Whether `cell` is worth highlighting as a swap-in target for the
    currently selected out-position."""
    return len(new_valid_moves(ss, cell)) > 0


def handle_search_click(cell):
    ss = st.session_state
    if cell in ss.current_path:
        pos = ss.current_path.index(cell)
        # Click the already-selected cell again to deselect it; click a
        # different path cell to move the selection there instead.
        ss.selected_out_pos = None if ss.selected_out_pos == pos else pos
        ss.selected_candidate_idx = None
        return

    pos = ss.selected_out_pos
    if pos is None:
        return
    moves = new_valid_moves(ss, cell)
    if not moves:
        return  # not clickable in practice (button is disabled), but guard defensively
    for move_type in moves:
        cand = gl.score_candidate(ss.grid, ss.current_path, pos, cell, ss.tabu_remaining, ss.best_sum, move_type)
        cand["reverses_last"] = ss.previous_path is not None and cand["new_path"] == ss.previous_path
        ss.candidate_list.append(cand)
    ss.selected_out_pos = None


def reveal_full_neighborhood():
    ss = st.session_state
    candidates = gl.enumerate_neighborhood(ss.grid, ss.current_path, ss.tabu_remaining, ss.best_sum)
    for cand in candidates:
        cand["reverses_last"] = ss.previous_path is not None and cand["new_path"] == ss.previous_path
    ss.candidate_list = candidates
    ss.selected_candidate_idx = None


def clear_candidates():
    st.session_state.candidate_list = []
    st.session_state.selected_out_pos = None
    st.session_state.selected_candidate_idx = None


def select_candidate(idx: int):
    """Toggles which candidate is selected on the grid - click the already
    selected row again to go back to showing the current solution."""
    ss = st.session_state
    ss.selected_candidate_idx = None if ss.selected_candidate_idx == idx else idx
    ss.selected_out_pos = None


def accept_move(cand: dict):
    ss = st.session_state
    ss.tabu_remaining = gl.advance_tabu(ss.tabu_remaining, ss.tenure, cand["out_cell"], cand["in_cell"])
    # tabu_source mirrors tabu_remaining but records *why* each cell is tabu -
    # the swap whose reversal it blocks - purely for display, so prune it to
    # match whatever advance_tabu just aged out or dropped.
    ss.tabu_source = {
        cell: reason for cell, reason in ss.tabu_source.items() if cell in ss.tabu_remaining
    }
    if cand["out_cell"] in ss.tabu_remaining:
        ss.tabu_source[cand["out_cell"]] = cand["in_cell"]
    ss.previous_path = ss.current_path
    ss.current_path = cand["new_path"]
    ss.iteration += 1
    was_repeat = tuple(ss.current_path) in ss.visited_paths
    ss.visited_paths.add(tuple(ss.current_path))
    if cand["new_sum"] > ss.best_sum:
        ss.best_sum = cand["new_sum"]
        ss.best_path = ss.current_path
    ss.history.append({
        "iteration": ss.iteration, "sum": cand["new_sum"], "best": ss.best_sum,
        "delta": cand["delta"], "tenure": ss.tenure, "tabu": cand["tabu"],
        "aspiration": cand["aspiration"], "repeat": was_repeat,
    })
    ss.candidate_list = []
    ss.selected_out_pos = None
    ss.selected_candidate_idx = None


def auto_play(n_iterations: int, delay: float = 0.6):
    """Plays tabu search iterations with no human input: reveals the full
    neighborhood, takes the best admissible move (or the best
    aspiration-allowed tabu move), and repeats - pausing to redraw so the
    user can watch it happen. Stops early on deadlock or on repeating a
    solution already visited (cycling)."""
    ss = st.session_state
    status = st.empty()
    board = st.empty()

    for _ in range(n_iterations):
        candidates = gl.enumerate_neighborhood(ss.grid, ss.current_path, ss.tabu_remaining, ss.best_sum)
        best = gl.pick_best_admissible(candidates)
        if best is None:
            status.error(
                f"\U0001f9f1 Deadlock at iteration {ss.iteration} — tenure={ss.tenure} blocks every "
                "feasible swap. Auto-play stopped early."
            )
            time.sleep(delay)
            break
        if tuple(best["new_path"]) in ss.visited_paths:
            status.warning(
                f"\U0001f501 Cycling detected at iteration {ss.iteration} — tenure={ss.tenure} isn't "
                "enough memory to avoid repeating a past solution. Auto-play stopped early."
            )
            time.sleep(delay)
            break

        accept_move(best)
        with board.container():
            move_label = "shift" if best["move_type"] == "shift" else "replace"
            st.markdown(
                f"**Iteration {ss.iteration}** — {move_label}: out {fmt_cell(best['out_cell'])} for "
                f"in {fmt_cell(best['in_cell'])} (Δ{best['delta']:+d})"
            )
            st.markdown(f"Current sum: **{best['new_sum']}** &nbsp; | &nbsp; Best so far: **{ss.best_sum}**")
        status.info(f"\U0001f916 Auto-play — iteration {ss.iteration} / {n_iterations}")
        time.sleep(delay)

    status.empty()
    board.empty()


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------
def static_cell_html(label: str, bg: str) -> str:
    """A non-interactive colored block standing in for a grid cell. Used
    instead of a disabled st.button because Streamlit's disabled buttons
    lose their primary/secondary color distinction - this is the only way
    to keep a cell visibly colored once it's no longer clickable."""
    return (
        f"<div style='background:{bg};color:#fff;text-align:center;"
        f"padding:0.45rem 0.3rem;margin:1px 0;border-radius:0.5rem;"
        f"font-weight:600;font-size:0.95rem;line-height:1.3;'>{label}</div>"
    )


def render_grid(grid: list, size: int, cell_state_fn, on_click_fn, key_prefix: str):
    """Renders `grid` with 1-indexed row/col headers. `cell_state_fn(cell)`
    returns a dict describing how to render that cell:
      - {"kind": "button", "label", "type", "disabled"} - a real clickable
        button.
      - {"kind": "static", "label", "bg"} - a non-interactive colored block
        (see static_cell_html) for cells that are part of the current
        selection/path but shouldn't be clickable right now.
    `on_click_fn(cell)` handles a click on an enabled button cell."""
    header = st.columns([0.6] + [1] * size, gap="small")
    for c in range(size):
        header[c + 1].markdown(
            f"<div style='text-align:center;color:#888;font-size:0.72rem;'>{c + 1}</div>",
            unsafe_allow_html=True,
        )
    for r in range(size):
        row = st.columns([0.6] + [1] * size, gap="small")
        row[0].markdown(
            f"<div style='text-align:right;color:#888;font-size:0.72rem;padding-top:10px;'>{r + 1}</div>",
            unsafe_allow_html=True,
        )
        for c in range(size):
            cell = (r, c)
            state = cell_state_fn(cell)
            if state["kind"] == "static":
                row[c + 1].markdown(static_cell_html(state["label"], state["bg"]), unsafe_allow_html=True)
                continue
            clicked = row[c + 1].button(
                state["label"], key=f"{key_prefix}_{r}_{c}", type=state["type"],
                disabled=state["disabled"], width="stretch",
            )
            if clicked:
                on_click_fn(cell)
                st.rerun()


def render_candidate_panel():
    ss = st.session_state
    grid = ss.grid
    candidates = ss.candidate_list
    total = len(gl.enumerate_neighborhood(ss.grid, ss.current_path, ss.tabu_remaining, ss.best_sum))

    st.markdown(f"**Candidate neighbors** — {len(candidates)} / {total} found")
    if not candidates:
        st.info("No candidates yet — generate at least one swap to see it here.")
        return

    st.caption(
        "Click a row to select that swap on the grid — including a worse one, on purpose, to "
        "escape a local optimum. Then confirm with ▶ Next round."
    )
    rows = st.container(height=380, border=False) if len(candidates) > 6 else st.container()
    admissible_count = 0
    with rows:
        for i, c in enumerate(candidates):
            out_val = grid[c["out_cell"][0]][c["out_cell"][1]]
            in_val = grid[c["in_cell"][0]][c["in_cell"][1]]
            if c["tabu"] and not c["aspiration"]:
                status = "\U0001f6ab TABU"
            elif c["tabu"]:
                status = "\U0001f31f aspiration"
            else:
                status = "✅"
            if c.get("reverses_last"):
                status += " ↩️"

            is_selected = ss.selected_candidate_idx == i
            c0, c1, c2, c3 = st.columns([0.35, 2.5, 1.1, 1.3])
            c0.markdown(f"**#{i + 1}**")
            if c["move_type"] == "shift":
                end = "head" if c["pos"] == 0 else "tail"
                other_end = "tail" if c["pos"] == 0 else "head"
                c1.markdown(
                    f"↔️ shift: drop {end} {fmt_cell(c['out_cell'])}={out_val} → grow {other_end} "
                    f"with {fmt_cell(c['in_cell'])}={in_val}"
                )
            else:
                c1.markdown(
                    f"pos {c['pos'] + 1}: out {fmt_cell(c['out_cell'])}={out_val} → "
                    f"in {fmt_cell(c['in_cell'])}={in_val}"
                )
            c2.markdown(f"sum **{c['new_sum']}** (Δ{c['delta']:+d}) · {status}")
            if c["admissible"]:
                admissible_count += 1
                label = "✓ Shown" if is_selected else "Select"
                if c3.button(
                    label, key=f"selrow_{ss.game_id}_{ss.iteration}_{i}",
                    type="primary" if is_selected else "secondary", width="stretch",
                ):
                    select_candidate(i)
                    st.rerun()
            else:
                c3.caption("blocked")

    if admissible_count == 0:
        st.warning(
            "⚠️ Every candidate here is blocked by the tabu list — a deadlock. Lower the "
            "tenure, or clear the tabu list to escape (a deliberate rule-break, for demonstration)."
        )
        if st.button("\U0001f9f9 Clear tabu list & continue"):
            ss.tabu_remaining = {}
            ss.tabu_source = {}
            st.rerun()
        return

    b1, b2 = st.columns(2)
    if b1.button(
        "▶ Next round", type="primary", width="stretch", disabled=ss.selected_candidate_idx is None,
    ):
        accept_move(candidates[ss.selected_candidate_idx])
        st.rerun()
    if b2.button("\U0001f5d1 Clear candidate list", width="stretch"):
        clear_candidates()
        st.rerun()


def render_setup():
    st.title("\U0001f500 Tabu Search: The Grid Game")
    st.caption("A hands-on Tabu Search minigame for IN2041 - Metaheuristics")
    st.markdown(
        "Build a **connected path** of cells on the grid — up, down, left, right, no diagonals, no "
        "revisits — that **maximizes the sum** of the values it passes through. Then improve it with "
        "a **swap**: trade one cell in your path for one cell outside it, keeping the path connected. "
        "A **tabu list** remembers your recent swaps and forbids reversing them for a few iterations — "
        "the mechanism that lets you escape a local optimum instead of cycling straight back to it."
    )

    diff_labels = [gl.DIFFICULTIES[k]["label"] for k in gl.DIFFICULTY_ORDER]
    choice = st.radio("Difficulty", diff_labels, index=0, horizontal=True)
    diff_key = gl.DIFFICULTY_ORDER[diff_labels.index(choice)]
    diff = gl.DIFFICULTIES[diff_key]
    est = gl.estimate_max_paths(diff["grid_size"], diff["path_length"])
    scale_note = (
        "Small enough you could imagine checking a lot of them by hand."
        if est < 10_000 else
        "Far too many to check by hand — this is why we need a smart search strategy."
    )
    st.caption(f"{diff['blurb']} — up to roughly **{est:,}** possible paths of this length "
               f"(rough upper bound). {scale_note}")

    code = st.text_input(
        "Game code (optional)", value="", placeholder="Leave blank for a random code", max_chars=12,
        help="Use the same code as a classmate to play on the identical grid — great for comparing "
             "tabu search runs, like the two teams in the in-class slides.",
    )

    if st.button("▶ Start Game", type="primary"):
        start_game(diff_key, code)
        st.rerun()


def render_construct():
    ss = st.session_state
    grid, size, L = ss.grid, ss.grid_size, ss.path_length
    build_path = ss.build_path

    st.subheader(f"Step 1 — Build your initial solution ({len(build_path)} / {L} cells)")
    st.caption("Click a cell to start your path. After that, only cells adjacent to your last pick are selectable.")

    available = set(gl.available_next_cells(size, build_path))

    def cell_state(cell):
        val = grid[cell[0]][cell[1]]
        if cell in build_path:
            return {"kind": "static", "label": str(val), "bg": COLOR_PATH}
        if len(build_path) < L and cell in available:
            return {"kind": "button", "label": str(val), "type": "secondary", "disabled": False}
        return {"kind": "button", "label": str(val), "type": "secondary", "disabled": True}

    render_grid(grid, size, cell_state, handle_construct_click, f"bc_{ss.game_id}")

    total = gl.path_sum(grid, build_path)
    path_str = " → ".join(str(grid[r][c]) for r, c in build_path) or "—"
    st.markdown(f"**Path so far:** {path_str} &nbsp; (sum = **{total}**)")

    if build_path and len(build_path) < L and not available:
        st.error("\U0001f6a7 Dead end — no unused adjacent cells from here. Undo a step and try a different direction.")

    c1, c2, c3, c4 = st.columns(4)
    if c1.button("↺ Undo", disabled=not build_path, width="stretch"):
        undo_construct()
        st.rerun()
    if c2.button("↷ Redo", disabled=not ss.redo_stack, width="stretch"):
        redo_construct()
        st.rerun()
    if c3.button("✖ Clear", disabled=not build_path, width="stretch"):
        clear_construct()
        st.rerun()
    if len(build_path) == L:
        if c4.button("▶ Confirm & Start Local Search", type="primary", width="stretch"):
            confirm_initial_solution()
            st.rerun()
    else:
        c4.button("▶ Confirm & Start Local Search", disabled=True, width="stretch")


def render_search():
    ss = st.session_state
    grid, size = ss.grid, ss.grid_size

    top = st.columns([1.4, 1, 1, 1, 1.4])
    top[0].subheader(f"Step 2 — Local Search (iteration {ss.iteration})")
    top[1].metric("Current sum", gl.path_sum(grid, ss.current_path))
    top[2].metric("Best found", ss.best_sum)
    top[3].metric("Tabu entries", len(ss.tabu_remaining))
    top[4].metric("Elapsed", f"{time.time() - ss.start_time:.0f}s")

    if ss.tabu_remaining:
        entries = sorted(ss.tabu_remaining.items(), key=lambda item: (-item[1], item[0]))
        lines = []
        for out_cell, remaining in entries:
            in_cell = ss.tabu_source.get(out_cell)
            move_desc = (
                f"swap out {fmt_cell(out_cell)} → in {fmt_cell(in_cell)}" if in_cell is not None
                else f"a move that removed {fmt_cell(out_cell)}"
            )
            lines.append(
                f"- **{move_desc}**: bringing {fmt_cell(out_cell)} back is forbidden for "
                f"{remaining} more move(s)"
            )
        st.markdown("\U0001f6ab **Tabu list** (recent swaps that can't be reversed yet):\n" + "\n".join(lines))
    else:
        st.caption("\U0001f6ab Tabu list: empty — no recent swap is currently forbidden from being reversed.")
    st.divider()

    last = ss.history[-1] if ss.history else None
    if last and last.get("repeat") and ss.iteration > 0:
        st.warning(
            "\U0001f501 You've returned to a solution you've already visited — a sign of cycling. "
            "Try raising the tabu tenure."
        )

    ctrl1, ctrl2 = st.columns([1.3, 2])
    with ctrl1:
        st.slider(
            "Tabu tenure", 0, gl.MAX_TENURE, key="tenure",
            help="How many future iterations the cell a swap just removed stays forbidden from being "
                 "brought back in. 0 = no memory at all (can cycle). Very high values can forbid every "
                 "feasible move at once — a deadlock.",
        )
    with ctrl2:
        st.radio(
            "Neighbor generation", ["manual", "auto"], key="neighbor_mode", horizontal=True,
            format_func=lambda m: (
                "\U0001f590 Manual — try one swap at a time" if m == "manual"
                else "⚡ Auto — reveal the full neighborhood"
            ),
        )

    with st.expander("\U0001f916 Auto-Play (watch tabu search run itself)", expanded=False):
        ac1, ac2 = st.columns([2, 1])
        n_iters = ac1.number_input(
            "Iterations to auto-play", min_value=1, max_value=gl.MAX_AUTOPLAY_ITERATIONS, value=10,
            key=f"autoplay_n_{ss.game_id}",
            help="Automatically reveals the full neighborhood, picks the best admissible move (or the "
                 "best aspiration-allowed tabu move), and repeats — so you can watch tabu search escape "
                 "local optima on its own. Stops early on deadlock or on repeating a past solution.",
        )
        if ac2.button("▶ Start", key=f"autoplay_btn_{ss.game_id}_{ss.iteration}", width="stretch"):
            auto_play(int(n_iters))
            st.rerun()

    left, right = st.columns([0.55, 0.45])

    with left:
        cur_sum = gl.path_sum(grid, ss.current_path)
        path_str = " → ".join(str(grid[r][c]) for r, c in ss.current_path)
        st.markdown(f"**Current path:** {path_str} &nbsp; (sum = **{cur_sum}**)")

        previewing = ss.selected_candidate_idx is not None
        if previewing:
            cand = ss.candidate_list[ss.selected_candidate_idx]
            preview_str = " → ".join(str(grid[r][c]) for r, c in cand["new_path"])
            st.markdown(
                f"**Selected:** {preview_str} &nbsp; (sum = **{cand['new_sum']}**, Δ{cand['delta']:+d}) "
                f"— 🟧 leaving, 🟩 arriving"
            )
            st.caption("Confirm with ▶ Next round, or click the row again (or another row) to change the selection.")

            def cell_state(cell):
                val = grid[cell[0]][cell[1]]
                if cell == cand["out_cell"]:
                    return {"kind": "static", "label": str(val), "bg": COLOR_REMOVED}
                if cell == cand["in_cell"]:
                    return {"kind": "static", "label": str(val), "bg": COLOR_ADDED}
                if cell in cand["new_path"]:
                    return {"kind": "static", "label": str(val), "bg": COLOR_PATH}
                return {"kind": "button", "label": str(val), "type": "secondary", "disabled": True}

            render_grid(grid, size, cell_state, lambda cell: None, f"bs_{ss.game_id}_{ss.iteration}_preview")
        elif ss.neighbor_mode == "manual":
            if ss.selected_out_pos is None:
                st.caption(
                    "Click a cell **in your path** to select it for swapping (click it again to "
                    "deselect) — valid replacement cells will light up."
                )
            else:
                out_cell = ss.current_path[ss.selected_out_pos]
                out_val = grid[out_cell[0]][out_cell[1]]
                st.caption(
                    f"Selected {fmt_cell(out_cell)}={out_val} — click a highlighted cell to swap it "
                    "in, or click it again to deselect."
                )

            def cell_state(cell):
                val = grid[cell[0]][cell[1]]
                if cell in ss.current_path:
                    return {"kind": "button", "label": str(val), "type": "primary", "disabled": False}
                highlighted = ss.selected_out_pos is not None and is_new_valid_target(ss, cell)
                return {"kind": "button", "label": str(val), "type": "secondary", "disabled": not highlighted}

            render_grid(grid, size, cell_state, handle_search_click, f"bs_{ss.game_id}_{ss.iteration}")
        else:
            def cell_state(cell):
                val = grid[cell[0]][cell[1]]
                if cell in ss.current_path:
                    return {"kind": "static", "label": str(val), "bg": COLOR_PATH}
                return {"kind": "button", "label": str(val), "type": "secondary", "disabled": True}

            render_grid(grid, size, cell_state, lambda cell: None, f"bs_{ss.game_id}_{ss.iteration}")
            if st.button("⚡ Reveal full neighborhood", type="primary"):
                reveal_full_neighborhood()
                st.rerun()

    with right:
        render_candidate_panel()


def render_finished():
    ss = st.session_state
    st.title("\U0001f3c1 Search Complete")

    improvement = ss.best_sum - ss.initial_sum
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Initial sum", ss.initial_sum)
    c2.metric("Best sum found", ss.best_sum, delta=improvement if improvement else None)
    c3.metric("Iterations run", ss.iteration)
    c4.metric("Total time", f"{time.time() - ss.start_time:.0f}s")

    n_aspiration = sum(1 for h in ss.history if h.get("aspiration"))
    n_repeat = sum(1 for h in ss.history if h.get("repeat"))
    st.caption(
        f"Aspiration overrides used: {n_aspiration} · Repeated solutions visited: {n_repeat} · "
        f"Difficulty: {gl.DIFFICULTIES[ss.difficulty]['label']} · Game code: {ss.game_code}"
    )

    st.plotly_chart(pl.build_progress_chart(ss.history, ss.initial_sum), width="stretch", key="progress_chart")

    df = pd.DataFrame(ss.history)
    df = df.rename(columns={
        "iteration": "Iteration", "sum": "Sum", "best": "Best", "delta": "Δ",
        "tenure": "Tenure", "tabu": "Was tabu", "aspiration": "Aspiration used", "repeat": "Repeated solution",
    })
    st.dataframe(df, width="stretch", hide_index=True)

    path_str = " → ".join(str(ss.grid[r][c]) for r, c in ss.best_path)
    st.markdown(f"**Best path found:** {path_str}")

    b1, b2 = st.columns(2)
    if b1.button("\U0001f501 Replay same grid (new initial solution)", width="stretch"):
        ss.phase = "construct"
        ss.build_path = []
        ss.redo_stack = []
        st.rerun()
    if b2.button("\U0001f195 New Game", width="stretch"):
        ss.phase = "setup"
        st.rerun()


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
init_state()

with st.sidebar:
    st.markdown("### \U0001f500 Tabu Search Grid Game")
    if st.session_state.phase != "setup":
        st.divider()
        st.metric("Game code", st.session_state.game_code)
        st.metric("Difficulty", gl.DIFFICULTIES[st.session_state.difficulty]["label"])
        if st.session_state.phase == "search":
            st.metric("Best sum so far", st.session_state.best_sum)
            if st.button("\U0001f3c1 Finish & See Report", width="stretch"):
                st.session_state.phase = "finished"
                st.rerun()
        if st.button("↺ New Game", width="stretch"):
            st.session_state.phase = "setup"
            st.rerun()
    st.divider()
    st.markdown("### \U0001f4d8 Concepts")
    st.caption("Click any topic for a quick explanation.")
    for title, body in CONCEPTS:
        with st.expander(title):
            st.markdown(body)

if st.session_state.phase == "setup":
    render_setup()
elif st.session_state.phase == "construct":
    render_construct()
elif st.session_state.phase == "search":
    render_search()
elif st.session_state.phase == "finished":
    render_finished()
