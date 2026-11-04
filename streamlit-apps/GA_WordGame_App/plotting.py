"""Plotly chart builder for the GA Word Game minigame.

One chart: fitness-over-generations, the classic GA convergence plot -
best and average fitness of the population at each generation, against a
dashed target line at the hidden word's length (a perfect match).

Colors reuse the fixed categorical order already established in this repo's
other minigame (ExhaustiveVsLocalSearch_App/plotting.py): blue for the
primary series, orange for the secondary one, muted gray for reference lines.
"""

import plotly.graph_objects as go

COLOR_BEST = "#2a78d6"     # categorical slot 1 - primary metric
COLOR_AVG = "#eb6834"      # categorical slot 2 - secondary metric
COLOR_TARGET = "#c3c2b7"   # muted reference line - not a data series


def build_fitness_chart(history: list, target_fitness: int, y_label: str = "Fitness (letters correct)"):
    generations = [h["generation"] for h in history]
    best = [h["best"] for h in history]
    avg = [h["avg"] for h in history]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=generations, y=[target_fitness] * len(generations), mode="lines",
        line=dict(color=COLOR_TARGET, dash="dash", width=1.5),
        name=f"Target ({target_fitness})", hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=generations, y=avg, mode="lines+markers", name="Average fitness",
        line=dict(color=COLOR_AVG, width=2), marker=dict(size=7, color=COLOR_AVG),
        hovertemplate="Generation %{x}<br>Average fitness: %{y:.2f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=generations, y=best, mode="lines+markers", name="Best fitness",
        line=dict(color=COLOR_BEST, width=3), marker=dict(size=9, color=COLOR_BEST),
        hovertemplate="Generation %{x}<br>Best fitness: %{y}<extra></extra>",
    ))

    fig.update_xaxes(title="Generation", dtick=1, zeroline=False, tickfont=dict(size=10))
    fig.update_yaxes(title=y_label, range=[-0.3, target_fitness + 0.6], dtick=1, zeroline=False)
    fig.update_layout(
        height=300,
        margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        showlegend=True,
    )
    return fig
