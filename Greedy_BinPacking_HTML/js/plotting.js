/* Static (read-only) Plotly rendering of a bin layout — used by Scoring mode
 * to visualize one submitted solution. Port of
 * Greedy_BinPacking_App/plotting.py: same shapes, labels and axes.
 *
 * Instances can have several hundred items at high difficulty, so per-item
 * labels are dropped above LABEL_ITEM_THRESHOLD and color carries the info.
 * Requires the Plotly global.
 */
(function () {
  "use strict";
  const BP = (globalThis.BP = globalThis.BP || {});

  const LABEL_ITEM_THRESHOLD = 80;
  const MAX_UNPLACED_LISTED = 30;
  const UNPLACED_PER_LINE = 10;

  /** Returns {data, layout} for Plotly.react. itemsById: Map id -> [w, h, profit].
   *  colors: page theme colors for axis text ({text, muted}). */
  function buildInstanceFigure(binW, binH, itemsById, placed, feasible, colors = { text: "#444", muted: "#666" }) {
    const profits = [...itemsById.values()].map((v) => v[2]);
    const [vmin, vmax] = profits.length ? [Math.min(...profits), Math.max(...profits)] : [0, 1];
    const placedIds = new Set(placed.map((p) => p.item_id));
    const showLabels = placed.length <= LABEL_ITEM_THRESHOLD;

    // The bin itself is always white with a light grid (like the game
    // board), so its black outline and grid read the same in both themes.
    const shapes = [
      { type: "rect", x0: 0, y0: 0, x1: binW, y1: binH, line: { width: 0 }, fillcolor: "#fff", layer: "below" },
      {
        type: "rect", x0: 0, y0: 0, x1: binW, y1: binH,
        line: { color: "black", width: 2 }, fillcolor: "rgba(0,0,0,0)",
      },
    ];
    const annotations = [];

    // Grid lines only inside the bin, not across the padded plot area.
    const gridX = Math.max(1, Math.floor(binW / 30));
    const gridY = Math.max(1, Math.floor(binH / 30));
    const grid = { color: "#eee", width: 1 };
    for (let gx = 0; gx <= binW; gx += gridX) shapes.push({ type: "line", x0: gx, y0: 0, x1: gx, y1: binH, line: grid, layer: "below" });
    for (let gy = 0; gy <= binH; gy += gridY) shapes.push({ type: "line", x0: 0, y0: gy, x1: binW, y1: gy, line: grid, layer: "below" });

    const borderColor = feasible ? "#333" : "#d32f2f";
    const borderWidth = !feasible ? 2 : showLabels ? 1 : 0.5;
    for (const p of placed) {
      const profit = (itemsById.get(p.item_id) || [0, 0, p.profit])[2];
      // The game puts y=0 at the TOP of the bin (screen convention); Plotly's
      // y axis grows upward, so flip to match what was seen in-game.
      const y0 = binH - p.y - p.h;
      const y1 = binH - p.y;
      shapes.push({
        type: "rect", x0: p.x, y0, x1: p.x + p.w, y1,
        line: { color: borderColor, width: borderWidth }, fillcolor: BP.game.profitColor(profit, vmin, vmax),
      });
      if (showLabels) {
        annotations.push({
          x: p.x + p.w / 2, y: (y0 + y1) / 2, text: `#${p.item_id}`,
          showarrow: false, font: { color: "white", size: 11 },
        });
      }
    }

    // The "Not placed" list sits above the bin, wrapped so it never runs off
    // the side of the chart; the top margin grows to fit the extra lines.
    let notPlacedLines = 0;
    const unplaced = [...itemsById.keys()].filter((id) => !placedIds.has(id)).sort((a, b) => a - b);
    if (unplaced.length) {
      const shown = unplaced.slice(0, MAX_UNPLACED_LISTED).map((i) => "#" + i);
      const lines = [];
      for (let i = 0; i < shown.length; i += UNPLACED_PER_LINE) lines.push(shown.slice(i, i + UNPLACED_PER_LINE).join(", "));
      lines[0] = `Not placed (${unplaced.length}): ` + lines[0];
      if (unplaced.length > MAX_UNPLACED_LISTED) lines[lines.length - 1] += ` … and ${unplaced.length - MAX_UNPLACED_LISTED} more`;
      notPlacedLines = lines.length;
      annotations.push({
        x: 0, y: binH, xanchor: "left", yanchor: "bottom", align: "left", showarrow: false,
        text: lines.join("<br>"), font: { size: 11, color: colors.muted },
      });
    }

    const pad = Math.max(binW, binH) * 0.05;
    // Ticks are left to Plotly: one per grid cell (the Streamlit version's
    // dtick) piles up into unreadable labels on the bigger bins.
    // constrain: "domain" keeps the axes hugging the bin at a 1:1 ratio.
    return {
      data: [],
      layout: {
        shapes, annotations,
        xaxis: { range: [-pad, binW + pad], showgrid: false, zeroline: false, showticklabels: true, constrain: "domain" },
        yaxis: {
          range: [-pad, binH + pad], showgrid: false, zeroline: false, showticklabels: true,
          scaleanchor: "x", scaleratio: 1, constrain: "domain",
        },
        height: Math.trunc(Math.min(800, Math.max(420, binH * 14))) + 14 * Math.max(0, notPlacedLines - 1),
        margin: { l: 40, r: 10, t: 30 + 14 * Math.max(0, notPlacedLines - 1), b: 30 },
        paper_bgcolor: "rgba(0,0,0,0)",
        plot_bgcolor: "rgba(0,0,0,0)",
        font: { color: colors.text },
      },
    };
  }

  BP.plotting = { buildInstanceFigure };
})();
