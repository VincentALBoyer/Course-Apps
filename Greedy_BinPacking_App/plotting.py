"""Static (read-only) Plotly rendering of a bin layout — used by Scoring
mode to visualize one selected submitted solution at a time.

Challenge/Scoring instances can range from a handful of items up to several
hundred at high difficulty, so labeling and sizing scale down automatically
once there are too many items to label legibly."""

import plotly.graph_objects as go

from game_logic import profit_color

# Above this many placed items, per-item "#id" labels would just overlap
# into noise, so they're dropped and color is left to carry the info.
LABEL_ITEM_THRESHOLD = 80
MAX_UNPLACED_LISTED = 30


def build_instance_figure(bin_w: int, bin_h: int, items_by_id: dict, placed: list, feasible: bool) -> go.Figure:
    profits = [p for _, _, p in items_by_id.values()]
    vmin, vmax = (min(profits), max(profits)) if profits else (0, 1)
    placed_ids = {p["item_id"] for p in placed}
    show_labels = len(placed) <= LABEL_ITEM_THRESHOLD

    # Shapes and annotations are collected as plain dicts and handed to
    # Plotly in a single update_layout call. Calling fig.add_shape /
    # fig.add_annotation once per item re-validates the whole growing list
    # every time (quadratic), which took ~9s of server CPU for a ~400-item
    # instance and stalled every other session sharing the process.
    shapes = [dict(
        type="rect", x0=0, y0=0, x1=bin_w, y1=bin_h,
        line=dict(color="black", width=2), fillcolor="rgba(0,0,0,0)",
    )]
    annotations = []

    # Grid lines only inside the bin, not across the whole plot area — drawn
    # as shapes (clipped to [0,bin_w]x[0,bin_h]) rather than via the axes'
    # native showgrid, which would span the full padded axis range.
    grid_step_x = max(1, bin_w // 30)
    grid_step_y = max(1, bin_h // 30)
    for gx in range(0, bin_w + 1, grid_step_x):
        shapes.append(dict(type="line", x0=gx, y0=0, x1=gx, y1=bin_h, line=dict(color="#eee", width=1), layer="below"))
    for gy in range(0, bin_h + 1, grid_step_y):
        shapes.append(dict(type="line", x0=0, y0=gy, x1=bin_w, y1=gy, line=dict(color="#eee", width=1), layer="below"))

    border_color = "#333" if feasible else "#d32f2f"
    border_width = 2 if not feasible else (1 if show_labels else 0.5)
    for p in placed:
        _, _, profit = items_by_id.get(p["item_id"], (0, 0, p["profit"]))
        color = profit_color(profit, vmin, vmax)
        # The game places items with y=0 at the TOP of the bin (CSS/screen
        # convention, growing downward), but Plotly's y-axis defaults to
        # y=0 at the bottom. Flip here so the plot matches what was seen
        # in-game instead of rendering it upside down.
        y0 = bin_h - p["y"] - p["h"]
        y1 = bin_h - p["y"]
        shapes.append(dict(
            type="rect", x0=p["x"], y0=y0, x1=p["x"] + p["w"], y1=y1,
            line=dict(color=border_color, width=border_width), fillcolor=color,
        ))
        if show_labels:
            annotations.append(dict(
                x=p["x"] + p["w"] / 2, y=(y0 + y1) / 2,
                text=f"#{p['item_id']}", showarrow=False, font=dict(color="white", size=11),
            ))

    unplaced = sorted(iid for iid in items_by_id if iid not in placed_ids)
    if unplaced:
        shown = ", ".join("#" + str(i) for i in unplaced[:MAX_UNPLACED_LISTED])
        more = f" … and {len(unplaced) - MAX_UNPLACED_LISTED} more" if len(unplaced) > MAX_UNPLACED_LISTED else ""
        annotations.append(dict(
            x=0, y=bin_h, xanchor="left", yanchor="bottom", showarrow=False,
            text=f"Not placed ({len(unplaced)}): {shown}{more}",
            font=dict(size=11, color="#666"),
        ))

    fig = go.Figure()
    fig.update_layout(shapes=shapes, annotations=annotations)

    pad = max(bin_w, bin_h) * 0.05
    fig.update_xaxes(range=[-pad, bin_w + pad], showgrid=False, zeroline=False, showticklabels=True, dtick=grid_step_x)
    fig.update_yaxes(
        range=[-pad, bin_h + pad], showgrid=False, zeroline=False,
        showticklabels=True, dtick=grid_step_y, scaleanchor="x", scaleratio=1,
    )
    height = int(min(800, max(420, bin_h * 14)))
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=30, b=10))
    return fig
