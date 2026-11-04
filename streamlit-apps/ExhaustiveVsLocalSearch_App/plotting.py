"""Plotly chart builders for the Exhaustive vs. Local Search minigame.

Two charts:
  - build_live_chart: the in-round board, clicked directly to play (see
    app.py's on_select handling). Unrevealed x's sit on a fixed "shelf" right
    on the x-axis (their height must never leak f(x) before the player
    reveals it); revealed points are colored by role.
  - build_debrief_chart: the post-round reveal, echoing the professor's own
    slide legend (global minimum / local minima / function values) plus the
    player's own landing point. Not interactive - the round is already over.
"""

import plotly.graph_objects as go

COLOR_UNREVEALED = "#c3c2b7"   # baseline/axis muted tone - not yet evaluated
COLOR_REVEALED = "#898781"     # muted ink - revealed, not currently special
COLOR_CURRENT = "#2a78d6"      # categorical slot 1 - "you are here"
COLOR_CANDIDATE = "#eb6834"    # categorical slot 2 - actionable / clickable
COLOR_GOOD = "#0ca30c"         # status good - best-so-far / global optimum
COLOR_WARN = "#fab219"         # status warning - local-optimum trap
COLOR_CONTEXT = "#86b6ef"      # sequential step - debrief backdrop dots

SHELF_Y = 0  # unrevealed x's sit right on the x-axis line - literally on the axis
LIVE_Y_RANGE = [-0.6, 8.5]  # fixed bounds, independent of any round's actual
                            # data, so the axis never hints at unseen values


def _base_layout(fig, height):
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        showlegend=True,
        clickmode="event+select",
    )
    return fig


def build_live_chart(xmax, revealed, mode, current_x=None, improving_xs=None, best_x=None):
    """Every x in 0..xmax is plotted as a real, clickable point - unrevealed
    ones right on the axis line, revealed ones at their true height. app.py
    reads clicks back via st.plotly_chart(..., on_select="rerun")."""
    improving_xs = improving_xs or set()
    fig = go.Figure()

    all_x = list(range(xmax + 1))
    unrevealed = [x for x in all_x if x not in revealed]
    if unrevealed:
        if mode == "local" and current_x is None:
            click_hint = "click to start here"
        elif mode == "greedy":
            click_hint = "click to pick - final answer"
        else:
            click_hint = "click to reveal"
        fig.add_trace(go.Scatter(
            x=unrevealed, y=[SHELF_Y] * len(unrevealed), mode="markers",
            marker=dict(size=11, color=COLOR_UNREVEALED, symbol="circle-open", line=dict(width=1.5)),
            name="Not yet evaluated",
            hovertemplate=f"x=%{{x}}<br>{click_hint}<extra></extra>",
        ))

    buckets = {
        "current": {"x": [], "y": [], "color": COLOR_CURRENT, "symbol": "circle", "size": 17, "label": "Current position"},
        "best": {"x": [], "y": [], "color": COLOR_GOOD, "symbol": "star", "size": 18, "label": "Best so far"},
        "improving": {"x": [], "y": [], "color": COLOR_CANDIDATE, "symbol": "circle", "size": 16, "label": "You can move here"},
        "revealed": {"x": [], "y": [], "color": COLOR_REVEALED, "symbol": "circle", "size": 12, "label": "Revealed"},
    }
    for x, y in sorted(revealed.items()):
        if mode == "local" and x == current_x:
            key = "current"
        elif mode == "exhaustive" and x == best_x:
            key = "best"
        elif mode == "local" and x in improving_xs:
            key = "improving"
        else:
            key = "revealed"
        buckets[key]["x"].append(x)
        buckets[key]["y"].append(y)

    hint = {"improving": "click to move here"}
    for key, b in buckets.items():
        if not b["x"]:
            continue
        extra = f"<br>{hint[key]}" if key in hint else ""
        fig.add_trace(go.Scatter(
            x=b["x"], y=b["y"], mode="markers",
            marker=dict(size=b["size"], color=b["color"], symbol=b["symbol"], line=dict(width=1, color="white")),
            name=b["label"],
            hovertemplate="x=%{x}<br>f(x)=%{y:.2f}" + extra + "<extra></extra>",
        ))

    fig.update_xaxes(title="x", range=[-1, xmax + 1], dtick=1, zeroline=False, tickfont=dict(size=10))
    fig.update_yaxes(title="f(x)", range=LIVE_Y_RANGE, zeroline=False)
    return _base_layout(fig, 400)


def build_debrief_chart(ys, global_idx, local_idxs, player_x):
    n = len(ys)
    xs = list(range(n))

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=xs, y=ys, mode="markers",
        marker=dict(size=9, color=COLOR_CONTEXT, symbol="circle"),
        name="Function values",
        hovertemplate="x=%{x}<br>f(x)=%{y:.2f}<extra></extra>",
    ))

    if local_idxs:
        lx = sorted(local_idxs)
        fig.add_trace(go.Scatter(
            x=lx, y=[ys[i] for i in lx], mode="markers",
            marker=dict(size=14, color=COLOR_WARN, symbol="triangle-up", line=dict(width=1, color="white")),
            name="Local minimum",
        ))

    fig.add_trace(go.Scatter(
        x=[global_idx], y=[ys[global_idx]], mode="markers",
        marker=dict(size=16, color=COLOR_GOOD, symbol="square", line=dict(width=1, color="white")),
        name="Global minimum",
    ))

    fig.add_trace(go.Scatter(
        x=[player_x], y=[ys[player_x]], mode="markers",
        marker=dict(size=26, color="rgba(0,0,0,0)", symbol="circle-open", line=dict(width=3, color=COLOR_CURRENT)),
        name="Your result",
        hovertemplate="Your result<br>x=%{x}<br>f(x)=%{y:.2f}<extra></extra>",
    ))
    fig.add_annotation(
        x=player_x, y=ys[player_x], text="You", showarrow=True, arrowhead=2, ay=-32,
        font=dict(color=COLOR_CURRENT, size=12),
    )

    fig.update_xaxes(title="x", range=[-1, n], dtick=1, zeroline=False, tickfont=dict(size=10))
    fig.update_yaxes(title="f(x)", zeroline=False)
    return _base_layout(fig, 420)
