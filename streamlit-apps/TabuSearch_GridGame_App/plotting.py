"""Plotly chart builder for the Tabu Search Grid Game minigame.

One chart: path sum over iterations - current solution vs. best solution
found so far, against a dashed reference line at the initial solution's
sum. Colors reuse the fixed categorical order already established in this
repo's other minigames (GA_WordGame_App/plotting.py): blue for the
headline metric, orange for the secondary one, muted gray for reference
lines.
"""

import plotly.graph_objects as go

COLOR_BEST = "#2a78d6"      # categorical slot 1 - headline metric
COLOR_CURRENT = "#eb6834"   # categorical slot 2 - secondary metric
COLOR_INITIAL = "#c3c2b7"   # muted reference line - not a data series


def build_progress_chart(history: list, initial_sum: int):
    iterations = [h["iteration"] for h in history]
    current = [h["sum"] for h in history]
    best = [h["best"] for h in history]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=iterations, y=[initial_sum] * len(iterations), mode="lines",
        line=dict(color=COLOR_INITIAL, dash="dash", width=1.5),
        name=f"Initial solution ({initial_sum})", hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=iterations, y=current, mode="lines+markers", name="Current solution",
        line=dict(color=COLOR_CURRENT, width=2), marker=dict(size=7, color=COLOR_CURRENT),
        hovertemplate="Iteration %{x}<br>Current sum: %{y}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=iterations, y=best, mode="lines+markers", name="Best found",
        line=dict(color=COLOR_BEST, width=3), marker=dict(size=9, color=COLOR_BEST),
        hovertemplate="Iteration %{x}<br>Best sum: %{y}<extra></extra>",
    ))

    fig.update_xaxes(title="Iteration", dtick=1, zeroline=False, tickfont=dict(size=10))
    fig.update_yaxes(title="Path sum", zeroline=False)
    fig.update_layout(
        height=300,
        margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        showlegend=True,
    )
    return fig
