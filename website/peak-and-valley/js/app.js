/* Peak and Valley — page controller. Port of
 * ExhaustiveVsLocalSearch_App/app.py: same phases (intro → playing →
 * debrief → … → final), strategies, scoring and messages. Clicking the
 * chart is handled in the browser, so there is no server round-trip. */
(function () {
  "use strict";
  const { $, esc, fmt0 } = MG;
  const L = PV.logic;
  const P = PV.plotting;

  const TOTAL_ROUNDS = L.ROUND_XMAX.length;
  const MAX_POSSIBLE_SCORE = 1000 * TOTAL_ROUNDS;
  const EXHAUSTIVE_FIXED_SCORE = MG.pyRound(1000 * L.QUALITY_WEIGHT);
  const STRATEGY_LABELS = { exhaustive: "Exhaustive", local: "Local Search", greedy: "Greedy" };
  const STRATEGY_CAPTIONS = {
    exhaustive: "Exhaustive: click every point one by one — guaranteed to find the best, costs the most evaluations.",
    local: "Local Search: pick a start, step to a strictly better neighbor each time — stops at the first local optimum.",
    greedy: "Greedy: click one point and that's your final answer — no exploration, no comparison, no take-backs.",
  };

  const CONCEPTS = [
    ["Global vs. local optimum",
      "A <strong>global optimum</strong> is the best solution over the <em>entire</em> search space. A <strong>local optimum</strong> is only the best <em>within its neighborhood</em> — every neighbor is equal or worse, but somewhere else in the space could still be better. Local search and Greedy can only ever guarantee a local optimum, never a global one."],
    ["Exhaustive search",
      "Evaluates <em>every</em> candidate solution, so it's the only strategy here that guarantees the global optimum. The catch is cost: the number of candidates often grows exponentially with problem size (e.g. 2ⁿ subsets for an n-item knapsack) — fine for small problems, impossible for real ones."],
    ["Greedy / constructive search",
      "Builds a solution in one shot using a fast rule of thumb — in this game, literally picking one point and accepting it, no comparison at all. It's the cheapest possible strategy (one evaluation) but has no way to check or correct its choice, so solution quality is pure luck."],
    ["Local search & neighborhoods",
      "Start from one solution, look at its <strong>neighborhood</strong> (nearby candidate solutions), and move to a better neighbor if one exists — repeat until none do. That stopping point is a local optimum. A wider neighborhood sees more of the landscape per step (more likely to find an improving move) but costs more evaluations per step."],
    ["Restarts (multi-start search)",
      "A classic fix for getting trapped in a bad local optimum: rerun local search from a different starting point and keep the best result across all attempts. It trades extra evaluations (lower efficiency) for a better shot at the global optimum."],
    ["Why search strategies matter",
      "Most real optimization problems have far too many candidate solutions to check exhaustively — a 20-item knapsack already has over a million subsets, and a 200-location p-median problem has more configurations than atoms are easy to count. Smart search strategies trade a guarantee of optimality for a solution that's good enough, fast enough."],
  ];
  $("concepts").innerHTML = CONCEPTS.map(([t, b]) => `<details><summary>${esc(t)}</summary><p>${b}</p></details>`).join("");
  $("exhaustive-fixed").textContent = String(EXHAUSTIVE_FIXED_SCORE);

  // ── state ────────────────────────────────────────────────────────────
  const S = {
    phase: "intro", gameCode: "", rounds: null, roundIdx: 0, roundResults: [],
    mode: null, neighborhoodN: 1, maxRestarts: 0,
    revealed: new Map(), roundStart: null, gameStart: null,
    lsCurrentX: null, lsStarted: false, lsRestartsUsed: 0, lsBestX: null, lsBestY: null,
  };

  function startGame(code, mode, neighborhoodN, maxRestarts) {
    const { code: c, seed } = L.resolveCode(code);
    Object.assign(S, {
      gameCode: c, rounds: L.generateAllRounds(seed), roundIdx: 0, roundResults: [],
      gameStart: Date.now(), neighborhoodN, maxRestarts,
    });
    beginRound(mode);
    S.phase = "playing";
  }

  function beginRound(mode) {
    Object.assign(S, {
      mode, revealed: new Map(), roundStart: Date.now(),
      lsCurrentX: null, lsStarted: false, lsRestartsUsed: 0, lsBestX: null, lsBestY: null,
    });
  }

  function finishRound(foundX, foundY) {
    const ys = S.rounds[S.roundIdx];
    const evaluations = S.revealed.size;
    const result = L.scoreRound(foundY, ys, evaluations);
    Object.assign(result, {
      round: S.roundIdx + 1, mode: S.mode, n_points: ys.length, evaluations,
      found_x: foundX, found_y: foundY,
      restarts_used: S.mode === "local" ? S.lsRestartsUsed : 0,
      time: (Date.now() - S.roundStart) / 1000,
    });
    S.roundResults.push(result);
    S.phase = "debrief";
  }

  function nextRoundOrFinish() {
    if (S.roundIdx < TOTAL_ROUNDS - 1) {
      S.roundIdx += 1;
      beginRound(S.mode);
      S.phase = "playing";
    } else {
      S.phase = "final";
    }
  }

  const ysNow = () => S.rounds[S.roundIdx];
  const xmaxNow = () => L.ROUND_XMAX[S.roundIdx];
  const minRevealed = () => Math.min(...S.revealed.values());
  function argminRevealed() {
    let best = null;
    for (const [x, y] of S.revealed) if (best === null || y < S.revealed.get(best)) best = x; // first in insertion order
    return best;
  }

  function revealExhaustive(x) {
    const ys = ysNow();
    S.revealed.set(x, ys[x]);
    if (S.revealed.size === ys.length) {
      const bx = argminRevealed();
      finishRound(bx, S.revealed.get(bx));
    }
  }

  function revealAround(x) {
    const ys = ysNow();
    if (!S.revealed.has(x)) S.revealed.set(x, ys[x]);
    for (const nb of L.neighborXs(x, S.neighborhoodN, ys.length - 1)) if (!S.revealed.has(nb)) S.revealed.set(nb, ys[nb]);
    S.lsCurrentX = x;
  }

  function startLocalSearch(x) {
    revealAround(x);
    S.lsStarted = true;
  }

  function restartLocalSearch() {
    S.lsRestartsUsed += 1;
    S.lsStarted = false;
    S.lsCurrentX = null;
  }

  function pickGreedy(x) {
    const ys = ysNow();
    S.revealed.set(x, ys[x]);
    finishRound(x, ys[x]);
  }

  function improvingNow() {
    const cur = S.revealed.get(S.lsCurrentX);
    return new Set(L.neighborXs(S.lsCurrentX, S.neighborhoodN, xmaxNow()).filter((x) => L.isImproving(S.revealed.get(x), cur)));
  }

  /** At a local optimum: remember the best attempt so far. */
  function recordIfStuck() {
    if (!S.lsStarted || improvingNow().size) return;
    const cy = S.revealed.get(S.lsCurrentX);
    if (S.lsBestY === null || cy < S.lsBestY) { S.lsBestX = S.lsCurrentX; S.lsBestY = cy; }
  }

  // ── chart clicks ─────────────────────────────────────────────────────
  function onChartClick(x) {
    if (S.phase !== "playing") return;
    const xmax = xmaxNow();
    if (!(Number.isInteger(x) && x >= 0 && x <= xmax)) return;
    if (S.mode === "exhaustive") {
      if (S.revealed.has(x)) return;
      revealExhaustive(x);
    } else if (S.mode === "greedy") {
      pickGreedy(x);
    } else if (!S.lsStarted) {
      startLocalSearch(x);
      recordIfStuck();
    } else {
      const improving = improvingNow();
      if (!improving.size) return; // stuck: the round is decided by the buttons below
      if (!improving.has(x)) {
        MG.toast("⚠️ That point isn't a strictly better neighbor — pick a highlighted point instead.");
        return;
      }
      revealAround(x);
      recordIfStuck();
    }
    render();
  }

  // ── rendering ────────────────────────────────────────────────────────
  const metric = (label, value) => `<div><div class="metric-label">${esc(label)}</div><div class="metric-value">${esc(value)}</div></div>`;
  const f2 = (v) => v.toFixed(2);

  function renderPlaying() {
    const idx = S.roundIdx;
    const xmax = xmaxNow();
    const n = xmax + 1;
    $("round-title").textContent = `Round ${idx + 1} / ${TOTAL_ROUNDS} — x from 0 to ${xmax} (${n} points)`;
    $("m-strategy").textContent = STRATEGY_LABELS[S.mode];
    $("m-score").textContent = String(S.roundResults.reduce((s, r) => s + r.score, 0));
    updateClock();
    $("progress-bar").style.width = (idx / TOTAL_ROUNDS) * 100 + "%";

    const panel = [];
    let fig;
    if (S.mode === "exhaustive") {
      const bestX = S.revealed.size ? argminRevealed() : null;
      fig = P.liveChart(xmax, S.revealed, "exhaustive", { bestX });
      panel.push(`<div class="metrics">${metric("Evaluations", `${S.revealed.size} / ${n}`)}${metric("Best so far", S.revealed.size ? f2(minRevealed()) : "—")}</div>`);
      panel.push(`<p class="caption">Click any unrevealed point on the chart to evaluate f(x) there — every point must be checked.</p>`);
    } else if (S.mode === "greedy") {
      fig = P.liveChart(xmax, S.revealed, "greedy");
      panel.push(`<p class="caption">Click any point on the chart — that's your final answer, no comparison, no take-backs.</p>`);
    } else if (!S.lsStarted) {
      fig = P.liveChart(xmax, S.revealed, "local");
      panel.push(S.lsRestartsUsed > 0
        ? `<p class="caption">Restart ${S.lsRestartsUsed}/${S.maxRestarts}: click anywhere on the chart to choose a new starting point. Previously revealed points are still shown.</p>`
        : `<p class="caption">Click anywhere on the chart to choose your starting point.</p>`);
    } else {
      const cx = S.lsCurrentX;
      const cy = S.revealed.get(cx);
      const improving = improvingNow();
      fig = P.liveChart(xmax, S.revealed, "local", { currentX: cx, improvingXs: improving });
      const ms = [metric("Current position", `x = ${cx}`), metric("Current value", f2(cy)), metric("Evaluations", `${S.revealed.size} / ${n}`)];
      if (S.maxRestarts > 0) {
        ms.push(metric("Restarts used", `${S.lsRestartsUsed} / ${S.maxRestarts}`));
        ms.push(metric("Best so far", S.lsBestY !== null ? f2(Math.min(S.lsBestY, cy)) : f2(cy)));
      }
      panel.push(`<div class="metrics">${ms.join("")}</div>`);
      if (!improving.size) {
        const bx = S.lsBestX;
        const by = S.lsBestY;
        const left = S.maxRestarts - S.lsRestartsUsed;
        if (left > 0) {
          panel.push(`<div class="alert warning">🪤 Attempt ${S.lsRestartsUsed + 1} reached a local optimum at x=${cx} (f=${f2(cy)}). Best result so far: f=${f2(by)} at x=${bx}. ${left} restart(s) left.</div>`);
          panel.push(`<div class="row"><button class="btn" data-act="restart-ls">🔄 Restart from a new point</button><button class="btn primary" data-act="accept-best">🏁 Accept best result (f=${f2(by)})</button></div>`);
        } else {
          panel.push(bx === cx
            ? `<div class="alert success">🏁 Local optimum reached at x=${cx} (f=${f2(cy)}) — neither neighbor is better. Round complete!</div>`
            : `<div class="alert success">🏁 Local optimum reached at x=${cx} (f=${f2(cy)}). Your best across all attempts was f=${f2(by)} at x=${bx} — that's what counts. Round complete!</div>`);
          panel.push(`<button class="btn primary" data-act="accept-best">See round results ▶</button>`);
        }
      } else {
        panel.push(`<p class="caption">Click the highlighted neighbor on the chart to move there.</p>`);
      }
    }
    $("play-panel").innerHTML = panel.join("");
    MG.plot($("live-chart"), fig.data, fig.layout, { displayModeBar: false });
  }

  // Chart clicks are resolved here rather than with plotly_click, which
  // only fires for a point already under a hover — never the case for a
  // finger tap (and Plotly cancels the tap's synthetic "click"). A pointer
  // release counts if it lands within TAP_RADIUS_PX of a point's marker
  // (unrevealed points sit on the y=0 shelf) and wasn't a drag/scroll.
  const TAP_RADIUS_PX = 30;
  // The release is caught on window: on press Plotly lays a drag "cover"
  // over the whole page, so the pointerup never reaches the chart itself.
  let down = null;
  $("live-chart").addEventListener("pointerdown", (e) => { down = { x: e.clientX, y: e.clientY }; }, true);
  window.addEventListener("pointercancel", () => { down = null; }, true);
  window.addEventListener("pointerup", (e) => {
    if (!down || Math.hypot(e.clientX - down.x, e.clientY - down.y) > 10) { down = null; return; }
    down = null;
    if (e.button > 0) return; // left mouse button, touch or pen only
    const gd = $("live-chart");
    const fl = gd._fullLayout;
    if (!fl || S.phase !== "playing") return;
    const box = gd.getBoundingClientRect();
    const xa = fl.xaxis;
    const ya = fl.yaxis;
    const px = e.clientX - box.left - xa._offset;
    const py = e.clientY - box.top - ya._offset;
    const x = Math.round(xa.p2l(px));
    if (x < 0 || x > xmaxNow()) return;
    const y = S.revealed.has(x) ? S.revealed.get(x) : 0;
    if (Math.hypot(xa.l2p(x) - px, ya.l2p(y) - py) <= TAP_RADIUS_PX) onChartClick(x);
  }, true);

  function renderDebrief() {
    const idx = S.roundIdx;
    const ys = ysNow();
    const r = S.roundResults[S.roundResults.length - 1];
    const g = L.argmin(ys);
    const locals = L.localMinimaIndices(ys).filter((i) => i !== g);
    const px = r.found_x;
    $("debrief-title").textContent = `Round ${idx + 1} results — ${STRATEGY_LABELS[r.mode]}`;
    const alert = $("debrief-alert");
    if (px === g) {
      alert.className = "alert success";
      alert.innerHTML = "🎉 You found the <strong>global optimum</strong>!";
    } else if (r.mode === "greedy") {
      alert.className = "alert warning";
      alert.textContent = `🎲 Your greedy pick landed at x=${px} — not the best. The global minimum was at x=${g}.`;
    } else {
      alert.className = "alert warning";
      alert.innerHTML = `🪤 You landed on a <strong>local optimum</strong> at x=${px}. The global minimum was at x=${g}.`;
    }
    const fig = P.debriefChart(ys, g, locals, px);
    MG.plot($("debrief-chart"), fig.data, fig.layout, { displayModeBar: false });

    const ms = [
      metric("Evaluations used", `${r.evaluations} / ${r.n_points}`),
      metric("Quality", fmt0(r.quality * 100) + "%"),
      metric("Efficiency", fmt0(r.efficiency * 100) + "%"),
      metric("Round score", String(r.score)),
    ];
    if (r.mode === "local" && S.maxRestarts > 0) ms.push(metric("Restarts used", `${r.restarts_used} / ${S.maxRestarts}`));
    $("debrief-metrics").innerHTML = ms.join("");
    $("debrief-time").textContent = `Round time: ${r.time.toFixed(1)}s`;
    $("next-round").textContent = idx < TOTAL_ROUNDS - 1 ? "Next Round ▶" : "See Final Results 🏁";
  }

  function renderFinal() {
    const total = S.roundResults.reduce((s, r) => s + r.score, 0);
    const time = S.roundResults.reduce((s, r) => s + r.time, 0);
    $("f-score").textContent = `${total} / ${MAX_POSSIBLE_SCORE}`;
    $("f-time").textContent = `${time.toFixed(1)}s`;
    $("f-code").textContent = S.gameCode;
    const pct = (v) => MG.pyRound(v * 100) + "%";
    const cols = [
      { key: "round", label: "Round" },
      { key: "mode", label: "Strategy", text: true, fmt: (m) => STRATEGY_LABELS[m] },
      { key: "n_points", label: "Points" },
      { key: "evaluations", label: "Evaluations" },
      { key: "quality", label: "Quality", fmt: pct },
      { key: "efficiency", label: "Efficiency", fmt: pct },
      { key: "score", label: "Score" },
      { key: "time", label: "Time (s)", fmt: (t) => t.toFixed(1) },
    ];
    if (S.mode === "local" && S.maxRestarts > 0) cols.push({ key: "restarts_used", label: "Restarts" });
    MG.renderTable($("final-table"), cols, S.roundResults);
  }

  function updateClock() {
    if (S.phase === "playing" && S.gameStart) $("m-time").textContent = fmt0((Date.now() - S.gameStart) / 1000) + "s";
  }
  setInterval(updateClock, 1000);

  function render() {
    for (const p of ["intro", "playing", "debrief", "final"]) $("phase-" + p).hidden = S.phase !== p;
    $("status-panel").hidden = S.phase === "intro";
    $("side-code").textContent = S.gameCode;
    if (S.phase === "playing") renderPlaying();
    else if (S.phase === "debrief") renderDebrief();
    else if (S.phase === "final") renderFinal();
  }

  // ── wiring ───────────────────────────────────────────────────────────
  const chosen = (name) => document.querySelector(`input[name="${name}"]:checked`).value;
  function syncIntro() {
    const mode = chosen("strategy");
    $("strategy-caption").textContent = STRATEGY_CAPTIONS[mode];
    $("advanced").hidden = mode !== "local";
    $("restarts-out").textContent = $("restarts").value;
  }
  document.querySelectorAll('input[name="strategy"]').forEach((i) => i.addEventListener("change", syncIntro));
  $("restarts").addEventListener("input", syncIntro);

  $("start").addEventListener("click", () => {
    const mode = chosen("strategy");
    const nb = mode === "local" ? Number(chosen("neighborhood")) : 1;
    const restarts = mode === "local" ? Number($("restarts").value) : 0;
    startGame($("code").value, mode, nb, restarts);
    render();
    window.scrollTo({ top: 0 });
  });

  $("play-panel").addEventListener("click", (e) => {
    const act = e.target.closest("[data-act]")?.dataset.act;
    if (act === "restart-ls") restartLocalSearch();
    else if (act === "accept-best") finishRound(S.lsBestX, S.lsBestY);
    else return;
    render();
  });

  $("next-round").addEventListener("click", () => { nextRoundOrFinish(); render(); window.scrollTo({ top: 0 }); });
  $("replay-same").addEventListener("click", () => { startGame(S.gameCode, S.mode, S.neighborhoodN, S.maxRestarts); render(); });
  $("replay-new").addEventListener("click", () => { startGame("", S.mode, S.neighborhoodN, S.maxRestarts); render(); });
  $("restart").addEventListener("click", () => { S.phase = "intro"; render(); });

  MG.theme.onChange(() => { if (S.phase === "playing" || S.phase === "debrief") render(); });
  window.addEventListener("beforeunload", (e) => { if (S.phase === "playing" || S.phase === "debrief") e.preventDefault(); });

  syncIntro();
  render();
})();
