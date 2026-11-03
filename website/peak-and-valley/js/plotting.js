/* Plotly charts for Peak and Valley — port of
 * ExhaustiveVsLocalSearch_App/plotting.py.
 *   - liveChart: the in-round board, clicked directly to play. Unrevealed
 *     x's sit on a "shelf" on the x-axis (their height must never leak f(x)
 *     before it's revealed); revealed points are colored by role.
 *   - debriefChart: the post-round reveal (global minimum / local minima /
 *     function values / your result), mirroring the slide's legend.
 * Both return {data, layout} for MG.plot.
 */
(function () {
  "use strict";
  const PV = (globalThis.PV = globalThis.PV || {});

  const COLOR_UNREVEALED = "#c3c2b7";
  const COLOR_REVEALED = "#898781";
  const COLOR_CURRENT = "#2a78d6";
  const COLOR_CANDIDATE = "#eb6834";
  const COLOR_GOOD = "#0ca30c";
  const COLOR_WARN = "#fab219";
  const COLOR_CONTEXT = "#86b6ef";

  const SHELF_Y = 0;
  // Fixed bounds, independent of the round's data, so the axis never hints
  // at values that haven't been revealed yet.
  const LIVE_Y_RANGE = [-0.6, 8.5];

  function baseLayout(height) {
    return {
      height,
      margin: { l: 50, r: 10, t: 10, b: 45 },
      legend: { orientation: "h", yanchor: "bottom", y: 1.02, x: 0 },
      showlegend: true,
      hovermode: "closest",
      dragmode: false, // the board is clicked, never zoomed or panned
    };
  }

  /** mode: "exhaustive" | "local" | "greedy". revealed: Map x -> f(x). */
  function liveChart(xmax, revealed, mode, { currentX = null, improvingXs = new Set(), bestX = null } = {}) {
    const data = [];
    const unrevealed = [];
    for (let x = 0; x <= xmax; x++) if (!revealed.has(x)) unrevealed.push(x);
    if (unrevealed.length) {
      const hint = mode === "local" && currentX === null ? "click to start here"
        : mode === "greedy" ? "click to pick - final answer" : "click to reveal";
      data.push({
        type: "scatter", mode: "markers", x: unrevealed, y: unrevealed.map(() => SHELF_Y),
        marker: { size: 11, color: COLOR_UNREVEALED, symbol: "circle-open", line: { width: 1.5 } },
        name: "Not yet evaluated", hovertemplate: `x=%{x}<br>${hint}<extra></extra>`,
      });
    }

    const buckets = {
      current: { x: [], y: [], color: COLOR_CURRENT, symbol: "circle", size: 17, label: "Current position" },
      best: { x: [], y: [], color: COLOR_GOOD, symbol: "star", size: 18, label: "Best so far" },
      improving: { x: [], y: [], color: COLOR_CANDIDATE, symbol: "circle", size: 16, label: "You can move here" },
      revealed: { x: [], y: [], color: COLOR_REVEALED, symbol: "circle", size: 12, label: "Revealed" },
    };
    for (const x of [...revealed.keys()].sort((a, b) => a - b)) {
      let key = "revealed";
      if (mode === "local" && x === currentX) key = "current";
      else if (mode === "exhaustive" && x === bestX) key = "best";
      else if (mode === "local" && improvingXs.has(x)) key = "improving";
      buckets[key].x.push(x);
      buckets[key].y.push(revealed.get(x));
    }
    for (const [key, b] of Object.entries(buckets)) {
      if (!b.x.length) continue;
      const extra = key === "improving" ? "<br>click to move here" : "";
      data.push({
        type: "scatter", mode: "markers", x: b.x, y: b.y,
        marker: { size: b.size, color: b.color, symbol: b.symbol, line: { width: 1, color: "white" } },
        name: b.label, hovertemplate: "x=%{x}<br>f(x)=%{y:.2f}" + extra + "<extra></extra>",
      });
    }

    const layout = baseLayout(400);
    layout.xaxis = { title: { text: "x" }, range: [-1, xmax + 1], dtick: 1, zeroline: false, tickfont: { size: 10 }, fixedrange: true };
    layout.yaxis = { title: { text: "f(x)" }, range: LIVE_Y_RANGE, zeroline: false, fixedrange: true };
    return { data, layout };
  }

  function debriefChart(ys, globalIdx, localIdxs, playerX) {
    const n = ys.length;
    const xs = [...Array(n).keys()];
    const data = [{
      type: "scatter", mode: "markers", x: xs, y: ys,
      marker: { size: 9, color: COLOR_CONTEXT, symbol: "circle" },
      name: "Function values", hovertemplate: "x=%{x}<br>f(x)=%{y:.2f}<extra></extra>",
    }];
    if (localIdxs.length) {
      data.push({
        type: "scatter", mode: "markers", x: localIdxs, y: localIdxs.map((i) => ys[i]),
        marker: { size: 14, color: COLOR_WARN, symbol: "triangle-up", line: { width: 1, color: "white" } },
        name: "Local minimum",
      });
    }
    data.push({
      type: "scatter", mode: "markers", x: [globalIdx], y: [ys[globalIdx]],
      marker: { size: 16, color: COLOR_GOOD, symbol: "square", line: { width: 1, color: "white" } },
      name: "Global minimum",
    });
    data.push({
      type: "scatter", mode: "markers", x: [playerX], y: [ys[playerX]],
      // For "-open" symbols Plotly strokes with marker.color, so the ring
      // color goes there (the Streamlit original set it transparent, which
      // left the ring invisible).
      marker: { size: 26, color: COLOR_CURRENT, symbol: "circle-open", line: { width: 3 } },
      name: "Your result", hovertemplate: "Your result<br>x=%{x}<br>f(x)=%{y:.2f}<extra></extra>",
    });
    const layout = baseLayout(420);
    layout.annotations = [{
      x: playerX, y: ys[playerX], text: "You", showarrow: true, arrowhead: 2, ay: -32,
      arrowcolor: COLOR_CURRENT, font: { color: COLOR_CURRENT, size: 12 },
    }];
    layout.xaxis = { title: { text: "x" }, range: [-1, n], dtick: 1, zeroline: false, tickfont: { size: 10 }, fixedrange: true };
    layout.yaxis = { title: { text: "f(x)" }, zeroline: false, fixedrange: true };
    return { data, layout };
  }

  PV.plotting = { liveChart, debriefChart };
})();
