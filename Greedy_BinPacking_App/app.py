"""Greedy Heuristics Intro Game — 2D Bin Packing.

Three modes sharing one instance format:

- Game: the in-browser drag-and-drop minigame (5 rounds, live scoring).
- Challenge: generate offline instances (seed + difficulty + count) to
  download as Excel and solve with your own code.
- Scoring: upload your completed instances file (bin/item data plus the
  x/y/rotated columns you filled in offline), get graded (0 profit for any
  infeasible instance), and inspect one submitted layout at a time.

The pedagogical hook: 2D bin packing is NP-hard, so there's no way to
compute the true optimum by hand or reasonably in a class session — so
students fall back on an intuitive rule of thumb (biggest first, best
value-per-area first, etc.). That rule of thumb *is* a greedy heuristic,
which is what the graded write-up asks them to name and describe.
"""

import random
import time

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from bin_component import bin_packer
from excel_io import (
    generate_instances,
    instances_workbook_bytes,
    parse_submission_workbook,
    score_submission,
)
from game_logic import (
    Instance,
    RoundState,
    compute_profit,
    compute_utilization,
    generate_round,
    is_feasible,
    move_placed_item,
    place_item,
    remove_placed_item,
    skip_item,
)
from plotting import build_instance_figure

N_ROUNDS = 5

st.set_page_config(page_title="Greedy Bin Packing", layout="wide")
st.warning(
    "⚠️ **This Streamlit version is no longer maintained.** "
    "Please use the [web version](https://vincentalboyer.github.io/Course-Apps/binpacking/) instead."
)


def init_game():
    st.session_state.game = {
        "phase": "intro",
        "round_idx": 1,
        "round_state": None,
        "round_results": [],
        "last_drop_sig": None,
        "strategy_text": "",
        "completed_instances": [],  # list[Instance], for end-of-game export
        "completed_placements": {},  # {round_idx: list[PlacedItem]}
        "results_xlsx": None,  # built once on the final report
    }


if "game" not in st.session_state:
    init_game()

game = st.session_state.game


def start_round(round_idx: int):
    rs = generate_round(round_idx, random.Random())
    rs.start_time = time.time()
    game["round_state"] = rs
    game["last_drop_sig"] = None


def finish_round():
    rs: RoundState = game["round_state"]
    for it in list(rs.items):
        skip_item(rs, it.id)
    elapsed = time.time() - rs.start_time
    feasible = is_feasible(rs)
    utilization = compute_utilization(rs)
    profit = compute_profit(rs) if feasible else 0
    potential_profit = sum(it.profit for it in rs.all_items)
    game["round_results"].append(
        {
            "round": rs.round_idx,
            "feasible": feasible,
            "profit": profit,
            "potential_profit": potential_profit,
            "utilization": utilization,
            "time_sec": elapsed,
            "items_placed": len(rs.placed),
            "items_total": len(rs.all_items),
        }
    )
    game["completed_instances"].append(
        Instance(id=rs.round_idx, bin_w=rs.bin_w, bin_h=rs.bin_h, items=rs.all_items)
    )
    game["completed_placements"][rs.round_idx] = list(rs.placed)

    if feasible:
        st.toast(f"Round {rs.round_idx} complete — {profit}/{potential_profit} profit captured.")
    else:
        st.toast(f"Round {rs.round_idx} complete — scored 0 (layout was infeasible).", icon="⚠️")

    if rs.round_idx < N_ROUNDS:
        start_round(rs.round_idx + 1)
        game["round_idx"] = rs.round_idx + 1
        game["phase"] = "playing"
    else:
        game["phase"] = "final"


def handle_drop(component_key: str):
    """on_change callback for the board component.

    Callbacks run before the script reruns, so the board, metrics and
    feasibility check below all render with the drop already applied —
    one rerun per drag instead of rendering stale state and forcing a
    second st.rerun().
    """
    game = st.session_state.game
    drop = st.session_state.get(component_key)
    rs = game["round_state"]
    if not drop or rs is None:
        return
    sig = (drop.get("source"), drop.get("remove"), drop["item_id"], drop["x"], drop["y"], drop["rotated"])
    if sig == game["last_drop_sig"]:
        return
    game["last_drop_sig"] = sig
    if drop.get("remove"):
        remove_placed_item(rs, drop["item_id"])
    elif drop.get("source") == "placed":
        move_placed_item(rs, drop["item_id"], drop["x"], drop["y"], drop["rotated"])
    else:
        item = next((it for it in rs.items if it.id == drop["item_id"]), None)
        if item is not None:
            place_item(rs, item, drop["x"], drop["y"], drop["rotated"])


def render_bin_packer(rs: RoundState):
    items_payload = [
        {"id": it.id, "w": it.w, "h": it.h, "profit": it.profit, "color": it.color}
        for it in rs.items
    ]
    placed_payload = [
        {
            "id": p.item.id, "x": p.x, "y": p.y, "w": p.w, "h": p.h,
            "rotated": p.rotated, "color": p.item.color, "profit": p.item.profit,
        }
        for p in rs.placed
    ]
    key = f"bin_packer_r{rs.round_idx}"
    bin_packer(
        bin_w=rs.bin_w, bin_h=rs.bin_h,
        items=items_payload, placed=placed_payload,
        key=key, on_change=lambda: handle_drop(key),
    )


def render_game_mode():
    st.title("📦 Greedy Bin Packing — Game")

    if game["phase"] == "intro":
        st.markdown(
            """
### The challenge

You have **one fixed bin**. Items arrive for each round — drag them from
the list on the left and drop them into the bin. You can drag a placed
item again later to reposition it, or drag it back onto the list to
remove it. There are **5 rounds**, and each one is harder than the last.

Overlaps and out-of-bounds placements are allowed while you're playing —
but if your layout still has any when the round ends, that round scores
**0 profit**, no matter what you packed.

Each item has a **profit** (its color — pale to deep red — tells you how
valuable it is; hover an item to see the exact numbers) and a size. There's
no way to work out the perfect layout by hand here (packing rectangles
into a bin for maximum value is a genuinely hard problem) — so just go
with your gut. Whatever rule of thumb you end up using without thinking
about it too hard — biggest first? most valuable first? — is worth
remembering. You'll be asked to describe it afterwards.

**Scoring:** your score is the total profit of everything you packed,
across all 5 rounds. Your total time is tracked too.
            """
        )
        if st.button("Start", type="primary"):
            game["phase"] = "playing"
            start_round(1)
            st.rerun()

    elif game["phase"] == "playing":
        rs: RoundState = game["round_state"]
        st.subheader(f"Round {rs.round_idx} of {N_ROUNDS}")
        elapsed = time.time() - rs.start_time
        c1, c2, c3 = st.columns(3)
        c1.metric("Elapsed", f"{elapsed:.0f}s")
        c2.metric("Profit so far", compute_profit(rs))
        c3.metric("Utilization", f"{compute_utilization(rs):.0f}%")

        feasible = is_feasible(rs)

        st.caption(
            "Drag a card from the list into the bin. Once placed, drag an item to move "
            "it, click ⟳ to rotate it, or click ✕ to remove it. Hover a card to see its "
            "profit and size."
        )

        render_bin_packer(rs)

        next_label = "See final report" if rs.round_idx == N_ROUNDS else "Next round"
        confirm = True
        if not feasible:
            confirm = st.checkbox(
                "I understand this round will score 0 profit because of the overlap/out-of-bounds items above",
                key=f"confirm_infeasible_r{rs.round_idx}",
            )

        if st.button(next_label, type="primary", disabled=not confirm):
            finish_round()
            st.rerun()

    elif game["phase"] == "final":
        st.subheader("🏁 Final report")
        df = pd.DataFrame(game["round_results"])
        total_score = df["profit"].sum()
        total_time = df["time_sec"].sum()
        avg_utilization = df["utilization"].mean()

        c1, c2, c3 = st.columns(3)
        c1.metric("Total score (profit)", int(total_score))
        c2.metric("Total time", f"{total_time:.0f}s")
        c3.metric("Avg. utilization", f"{avg_utilization:.0f}%")

        st.dataframe(
            df.rename(columns={
                "round": "Round", "profit": "Your profit",
                "potential_profit": "Potential profit", "utilization": "Utilization (%)",
                "time_sec": "Time (s)", "items_placed": "Items placed", "items_total": "Items offered",
                "feasible": "Feasible",
            })[[
                "Round", "Feasible", "Your profit", "Potential profit",
                "Utilization (%)", "Time (s)", "Items placed", "Items offered",
            ]],
            hide_index=True, width="stretch",
        )

        fig = go.Figure()
        fig.add_bar(x=df["round"], y=df["profit"], name="Your profit")
        fig.update_layout(
            xaxis_title="Round", yaxis_title="Profit",
            height=350, margin=dict(l=10, r=10, t=30, b=10),
        )
        st.plotly_chart(fig, width="stretch")

        st.markdown("### Describe your strategy")
        st.caption(
            "This is the part that gets graded. Think about how you decided *which* "
            "item to drag next, and *where* — that decision rule is a greedy heuristic, "
            "whether or not you were thinking of it that way."
        )
        game["strategy_text"] = st.text_area(
            "What rule(s) did you follow?", value=game["strategy_text"], height=150,
        )

        report_lines = [
            "Greedy Bin Packing — Results",
            f"Total score (profit): {int(total_score)}",
            f"Total time: {total_time:.0f}s",
            f"Average utilization: {avg_utilization:.0f}%",
            "",
            "Round-by-round:",
        ]
        for _, row in df.iterrows():
            feasible_note = "" if row["feasible"] else " [INFEASIBLE — scored 0]"
            report_lines.append(
                f"  Round {int(row['round'])}: {int(row['profit'])}/{int(row['potential_profit'])} "
                f"profit{feasible_note}, {row['utilization']:.0f}% utilization, {row['time_sec']:.0f}s, "
                f"{int(row['items_placed'])}/{int(row['items_total'])} items placed"
            )
        report_lines += ["", "Strategy description:", game["strategy_text"] or "(not yet written)"]
        report_text = "\n".join(report_lines)

        c1, c2 = st.columns(2)
        c1.download_button(
            "Download report (.txt)", data=report_text,
            file_name="greedy_bin_packing_report.txt", mime="text/plain",
        )

        # Results can't change once the game is over, so build the workbook
        # once instead of on every rerun (e.g. each strategy-text edit).
        if game.get("results_xlsx") is None:
            game["results_xlsx"] = instances_workbook_bytes(
                game["completed_instances"], seed="game-mode", difficulty="1-5", n_instances=N_ROUNDS,
                placements_by_instance=game["completed_placements"],
            )
        c2.download_button(
            "Download my results (.xlsx)", data=game["results_xlsx"],
            file_name="game_results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        if st.button("Play again"):
            init_game()
            st.rerun()


def render_challenge_mode():
    st.title("🧪 Challenge Mode — Instance Generator")
    st.markdown(
        """
Generate a batch of bin-packing instances to solve **offline** with your own
code. Same rules as the game: one fixed bin per instance, pack items to
maximize profit, no overlaps or out-of-bounds placements allowed.

Pick a **seed** so your batch is reproducible, a **difficulty** level (higher
= more items, a bigger bin, and tighter capacity — difficulty 10 means
hundreds of items, well past anything solvable by hand), and how many
instances you want bundled into one file.
        """
    )

    col1, col2, col3 = st.columns(3)
    seed = col1.number_input("Seed / code", min_value=0, value=42, step=1)
    difficulty = col2.slider("Difficulty", 1, 10, 5)
    n_instances = col3.number_input("Number of instances", min_value=1, max_value=50, value=10, step=1)

    if st.button("Generate instances", type="primary"):
        seed_p, diff_p, n_p = int(seed), int(difficulty), int(n_instances)
        instances = generate_instances(seed_p, float(diff_p), n_p)
        # Build the workbook once here and keep only its bytes — rebuilding it
        # on every rerun cost ~1s of shared server CPU at high difficulty, and
        # keeping the Instance objects around held thousands of items per session.
        st.session_state["challenge_file"] = {
            "params": (seed_p, diff_p, n_p),
            "n_generated": len(instances),
            "total_items": sum(len(inst.items) for inst in instances),
            "xlsx": instances_workbook_bytes(instances, seed_p, diff_p, n_p),
        }

    challenge_file = st.session_state.get("challenge_file")
    if challenge_file:
        seed_p, diff_p, n_p = challenge_file["params"]
        st.success(
            f"Generated {challenge_file['n_generated']} instance(s) — seed {seed_p}, difficulty {diff_p}, "
            f"{challenge_file['total_items']} items total."
        )

        st.download_button(
            "Download instances (.xlsx)",
            data=challenge_file["xlsx"],
            file_name=f"instances_seed{seed_p}_d{diff_p}_n{n_p}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
        )
        st.caption(
            "One row per item, with blank x, y, and rotated columns. Fill those in "
            "(TRUE/FALSE for rotated) for whichever items your algorithm decides to "
            "pack, and leave them blank for anything you skip — then upload this same "
            "file, filled in, to Scoring mode to get graded."
        )


def render_scoring_mode():
    st.title("📊 Scoring Mode — Grade a Submission")
    st.markdown(
        """
Upload your completed instances file (the one from Challenge mode, with the
x/y/rotated columns filled in offline). Each instance is graded
independently — an instance with any overlapping or out-of-bounds item
scores **0 profit**, regardless of what else was packed correctly.

The file is also checked against the signature recorded when it was
generated, to flag whether the underlying instance data (bin size, item
dimensions, profits) was altered.
        """
    )

    submission_file = st.file_uploader("Completed instances file (.xlsx)", type=["xlsx"])

    if st.button("Score submission", type="primary", disabled=not submission_file):
        try:
            df, integrity = parse_submission_workbook(submission_file)
            st.session_state["scoring_results"] = (*score_submission(df), integrity)
        except Exception as exc:
            st.session_state.pop("scoring_results", None)
            st.error(f"Could not score this submission: {exc}")

    results = st.session_state.get("scoring_results")
    if results:
        results_df, summary, reconstructed, integrity = results

        if integrity["checked"] and not integrity["ok"]:
            st.error(f"⚠️ Integrity check failed: {integrity['message']}")
        elif integrity["checked"]:
            st.success(f"✓ Integrity check passed: {integrity['message']}")
        else:
            st.info(integrity["message"])

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total score", summary["total_score"])
        c2.metric("Potential", summary["total_potential"])
        c3.metric("Feasible instances", f"{summary['n_feasible']}/{summary['n_instances']}")
        c4.metric("Avg. utilization", f"{summary['avg_utilization']:.0f}%")

        st.dataframe(
            results_df.rename(columns={
                "instance_id": "Instance", "feasible": "Feasible", "error": "Issue",
                "profit": "Profit", "potential_profit": "Potential profit",
                "utilization": "Utilization (%)", "items_placed": "Items placed",
                "items_total": "Items offered",
            }),
            hide_index=True, width="stretch",
        )

        report_lines = [
            "Greedy Bin Packing — Scoring Report",
            f"Integrity check: {'PASSED' if integrity['ok'] else 'FAILED'} — {integrity['message']}",
            f"Total score: {summary['total_score']} / {summary['total_potential']}",
            f"Feasible instances: {summary['n_feasible']}/{summary['n_instances']}",
            f"Average utilization: {summary['avg_utilization']:.0f}%",
            "",
            "Per-instance:",
        ]
        for _, row in results_df.iterrows():
            note = "" if row["feasible"] else f" [INFEASIBLE — {row['error']}, scored 0]"
            report_lines.append(
                f"  Instance {int(row['instance_id'])}: {int(row['profit'])}/{int(row['potential_profit'])} "
                f"profit{note}, {row['utilization']:.0f}% utilization, "
                f"{int(row['items_placed'])}/{int(row['items_total'])} items placed"
            )
        st.download_button(
            "Download report (.txt)", data="\n".join(report_lines),
            file_name="scoring_report.txt", mime="text/plain",
        )

        st.markdown("### Inspect a solution")
        instance_ids = sorted(reconstructed.keys())
        selected = st.selectbox("Instance to plot", instance_ids, format_func=lambda i: f"Instance {i}")
        if selected is not None:
            data = reconstructed[selected]
            if not data["feasible"]:
                st.error("This instance's solution is infeasible (overlap or out-of-bounds) — scored 0 profit.")
            fig = build_instance_figure(
                data["bin_w"], data["bin_h"], data["items_by_id"], data["placed"], data["feasible"],
            )
            st.plotly_chart(fig, width="stretch")


mode = st.sidebar.radio("Mode", ["🎮 Game", "🧪 Challenge", "📊 Scoring"])
if mode == "🎮 Game":
    render_game_mode()
elif mode == "🧪 Challenge":
    render_challenge_mode()
else:
    render_scoring_mode()
