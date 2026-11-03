/* Page controller — port of Greedy_BinPacking_App/app.py.
 *
 * Three modes sharing one instance format:
 * - Game: the drag-and-drop minigame (5 rounds, live scoring).
 * - Challenge: generate offline instances (seed + difficulty + count) as an
 *   Excel file to solve with your own code.
 * - Scoring: upload a completed instances file, get graded (0 profit for any
 *   infeasible instance), and inspect one submitted layout at a time.
 *
 * Everything runs in the visitor's browser; nothing is sent anywhere.
 */
(function () {
  "use strict";
  const { game: G, excel: X, plotting: P, fmt0 } = BP;
  const N_ROUNDS = 5;
  const XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";

  const $ = (id) => document.getElementById(id);

  // ── helpers ──────────────────────────────────────────────────────────
  function toast(text) {
    const t = document.createElement("div");
    t.className = "toast";
    t.textContent = text;
    $("toast-stack").appendChild(t);
    setTimeout(() => { t.classList.add("leaving"); setTimeout(() => t.remove(), 350); }, 4000);
  }

  function download(data, filename, mime) {
    const url = URL.createObjectURL(new Blob([data], { type: mime }));
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  /** columns: [{key, label, fmt?, text?}] */
  function renderTable(table, columns, rows) {
    const thead = document.createElement("thead");
    const hr = document.createElement("tr");
    for (const c of columns) {
      const th = document.createElement("th");
      th.textContent = c.label;
      if (c.text) th.className = "text";
      hr.appendChild(th);
    }
    thead.appendChild(hr);
    const tbody = document.createElement("tbody");
    for (const r of rows) {
      const tr = document.createElement("tr");
      for (const c of columns) {
        const td = document.createElement("td");
        td.textContent = c.fmt ? c.fmt(r[c.key]) : String(r[c.key]);
        if (c.text) td.className = "text";
        tr.appendChild(td);
      }
      tbody.appendChild(tr);
    }
    table.replaceChildren(thead, tbody);
  }

  const yesNo = (v) => (v ? "✓" : "✗");
  const dec1 = (v) => v.toFixed(1);

  function plot(el, fig) {
    Plotly.react(el, fig.data, fig.layout, { responsive: true, displaylogo: false });
  }

  // ── mode switching ───────────────────────────────────────────────────
  const tabs = document.querySelectorAll(".modes button");
  function setMode(mode) {
    tabs.forEach((b) => b.setAttribute("aria-selected", String(b.dataset.mode === mode)));
    for (const m of ["game", "challenge", "scoring"]) $("mode-" + m).hidden = m !== mode;
    // Plotly sizes charts from their container; resize once it's visible.
    document.querySelectorAll(`#mode-${mode} .js-plotly-plot`).forEach((c) => Plotly.Plots.resize(c));
    try { history.replaceState(null, "", "#" + mode); } catch (e) { /* file:// or sandboxed */ }
  }
  tabs.forEach((b) => b.addEventListener("click", () => setMode(b.dataset.mode)));

  // ── Game mode ────────────────────────────────────────────────────────
  let game;
  const board = BP.createBoard($("board"), handleDrop);

  function initGame() {
    game = {
      phase: "intro",
      round_state: null,
      round_results: [],
      completed_instances: [], // for end-of-game export
      completed_placements: {}, // {round_idx: [placed]}
      results_xlsx: null, // built once on the final report
    };
  }

  function startRound(roundIdx) {
    const rs = G.generateRound(roundIdx, new BP.PyRandom(null));
    rs.start_time = Date.now();
    game.round_state = rs;
    $("confirm-infeasible").checked = false;
  }

  function finishRound() {
    const rs = game.round_state;
    rs.items = []; // anything not placed is skipped
    const elapsed = (Date.now() - rs.start_time) / 1000;
    const feasible = G.isFeasible(rs);
    const utilization = G.computeUtilization(rs);
    const profit = feasible ? G.computeProfit(rs) : 0;
    const potential = rs.all_items.reduce((s, it) => s + it.profit, 0);
    game.round_results.push({
      round: rs.round_idx, feasible, profit, potential_profit: potential, utilization,
      time_sec: elapsed, items_placed: rs.placed.length, items_total: rs.all_items.length,
    });
    game.completed_instances.push({ id: rs.round_idx, bin_w: rs.bin_w, bin_h: rs.bin_h, items: rs.all_items });
    game.completed_placements[rs.round_idx] = rs.placed.slice();

    toast(feasible
      ? `Round ${rs.round_idx} complete — ${profit}/${potential} profit captured.`
      : `⚠️ Round ${rs.round_idx} complete — scored 0 (layout was infeasible).`);

    if (rs.round_idx < N_ROUNDS) {
      startRound(rs.round_idx + 1);
      game.phase = "playing";
    } else {
      game.phase = "final";
    }
  }

  function handleDrop(drop) {
    const rs = game.round_state;
    if (!rs || game.phase !== "playing") return;
    if (drop.remove) {
      G.removePlacedItem(rs, drop.item_id);
    } else if (drop.source === "placed") {
      G.movePlacedItem(rs, drop.item_id, drop.x, drop.y, drop.rotated);
    } else {
      const item = rs.items.find((it) => it.id === drop.item_id);
      if (item) G.placeItem(rs, item, drop.x, drop.y, drop.rotated);
    }
    renderGame();
  }

  function renderPlaying() {
    const rs = game.round_state;
    $("round-title").textContent = `Round ${rs.round_idx} of ${N_ROUNDS}`;
    $("m-profit").textContent = String(G.computeProfit(rs));
    $("m-util").textContent = fmt0(G.computeUtilization(rs)) + "%";
    updateElapsed();

    board.render({
      bin_w: rs.bin_w, bin_h: rs.bin_h,
      items: rs.items.map((it) => ({ id: it.id, w: it.w, h: it.h, profit: it.profit, color: it.color })),
      placed: rs.placed.map((p) => ({
        id: p.item.id, x: p.x, y: p.y, w: G.placedW(p), h: G.placedH(p),
        rotated: p.rotated, color: p.item.color, profit: p.item.profit,
      })),
    });

    const feasible = G.isFeasible(rs);
    // Like a Streamlit checkbox that stops being rendered, the confirmation
    // resets whenever it's hidden (layout feasible again).
    if (feasible) $("confirm-infeasible").checked = false;
    $("confirm-wrap").hidden = feasible;
    $("game-next").textContent = rs.round_idx === N_ROUNDS ? "See final report" : "Next round";
    $("game-next").disabled = !feasible && !$("confirm-infeasible").checked;
  }

  function updateElapsed() {
    const rs = game.round_state;
    if (game.phase === "playing" && rs) $("m-elapsed").textContent = fmt0((Date.now() - rs.start_time) / 1000) + "s";
  }
  setInterval(updateElapsed, 1000);

  function finalStats() {
    const rows = game.round_results;
    const totalScore = rows.reduce((s, r) => s + r.profit, 0);
    const totalTime = rows.reduce((s, r) => s + r.time_sec, 0);
    const avgUtil = rows.reduce((s, r) => s + r.utilization, 0) / rows.length;
    return { rows, totalScore, totalTime, avgUtil };
  }

  function renderFinal() {
    const { rows, totalScore, totalTime, avgUtil } = finalStats();
    $("f-score").textContent = String(totalScore);
    $("f-time").textContent = fmt0(totalTime) + "s";
    $("f-util").textContent = fmt0(avgUtil) + "%";
    renderTable($("final-table"), [
      { key: "round", label: "Round" },
      { key: "feasible", label: "Feasible", fmt: yesNo },
      { key: "profit", label: "Your profit" },
      { key: "potential_profit", label: "Potential profit" },
      { key: "utilization", label: "Utilization (%)", fmt: dec1 },
      { key: "time_sec", label: "Time (s)", fmt: dec1 },
      { key: "items_placed", label: "Items placed" },
      { key: "items_total", label: "Items offered" },
    ], rows);
    plot($("final-chart"), {
      data: [{ type: "bar", x: rows.map((r) => r.round), y: rows.map((r) => r.profit), name: "Your profit", marker: { color: "#d9452b" } }],
      layout: {
        xaxis: { title: { text: "Round" }, dtick: 1 }, yaxis: { title: { text: "Profit" } },
        height: 350, margin: { l: 60, r: 10, t: 30, b: 50 },
        paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
        font: { color: getComputedStyle(document.body).color },
      },
    });
    if (!game.results_xlsx) {
      // Results can't change once the game is over: build the workbook once.
      game.results_xlsx = X.instancesWorkbookBytes(
        game.completed_instances, "game-mode", "1-5", N_ROUNDS, game.completed_placements,
      );
    }
  }

  function renderGame() {
    $("game-intro").hidden = game.phase !== "intro";
    $("game-playing").hidden = game.phase !== "playing";
    $("game-final").hidden = game.phase !== "final";
    if (game.phase === "playing") renderPlaying();
    if (game.phase === "final") renderFinal();
  }

  $("game-start").addEventListener("click", () => {
    game.phase = "playing";
    startRound(1);
    renderGame();
  });
  $("confirm-infeasible").addEventListener("change", () => {
    $("game-next").disabled = !$("confirm-infeasible").checked;
  });
  $("game-next").addEventListener("click", () => {
    finishRound();
    renderGame();
    window.scrollTo({ top: 0 });
  });
  $("dl-results").addEventListener("click", async () => download(await game.results_xlsx, "game_results.xlsx", XLSX_MIME));
  $("play-again").addEventListener("click", () => { initGame(); renderGame(); });

  // Leaving mid-game loses progress (as in the Streamlit app) — warn first.
  window.addEventListener("beforeunload", (e) => {
    if (game.phase === "playing") e.preventDefault();
  });

  // ── Challenge mode ───────────────────────────────────────────────────
  let challengeFile = null;
  $("c-diff").addEventListener("input", (e) => { $("c-diff-out").textContent = e.target.value; });

  function readInt(input, min, max, fallback) {
    const raw = String(input.value).trim();
    let v;
    try { v = /^\d+$/.test(raw) ? BigInt(raw) : BigInt(Math.trunc(Number(raw))); } catch (e) { v = BigInt(fallback); }
    if (v < BigInt(min)) v = BigInt(min);
    if (max !== null && v > BigInt(max)) v = BigInt(max);
    input.value = v.toString();
    return v;
  }

  $("c-generate").addEventListener("click", async () => {
    const btn = $("c-generate");
    btn.disabled = true;
    btn.textContent = "Generating…";
    await new Promise((r) => setTimeout(r, 20)); // let the label repaint
    try {
      const seed = readInt($("c-seed"), 0, null, 42);
      const diff = Number($("c-diff").value);
      const n = Number(readInt($("c-n"), 1, 50, 10));
      const instances = G.generateInstances(seed, diff, n);
      const seedOut = seed <= BigInt(Number.MAX_SAFE_INTEGER) ? Number(seed) : seed.toString();
      challengeFile = {
        seed: seed.toString(), diff, n,
        n_generated: instances.length,
        total_items: instances.reduce((s, i) => s + i.items.length, 0),
        xlsx: await X.instancesWorkbookBytes(instances, seedOut, diff, n),
      };
      $("c-summary").textContent =
        `Generated ${challengeFile.n_generated} instance(s) — seed ${challengeFile.seed}, ` +
        `difficulty ${diff}, ${challengeFile.total_items} items total.`;
      $("c-result").hidden = false;
    } finally {
      btn.disabled = false;
      btn.textContent = "Generate instances";
    }
  });
  $("c-download").addEventListener("click", () => {
    const f = challengeFile;
    download(f.xlsx, `instances_seed${f.seed}_d${f.diff}_n${f.n}.xlsx`, XLSX_MIME);
  });

  // ── Scoring mode ─────────────────────────────────────────────────────
  let scoring = null;
  $("s-file").addEventListener("change", (e) => { $("s-score").disabled = !e.target.files.length; });

  $("s-score").addEventListener("click", async () => {
    const file = $("s-file").files[0];
    if (!file) return;
    $("s-error").hidden = true;
    try {
      const { rows, integrity } = await X.parseSubmissionWorkbook(await file.arrayBuffer());
      scoring = { ...X.scoreSubmission(rows), integrity };
      renderScoring();
    } catch (err) {
      scoring = null;
      $("s-results").hidden = true;
      $("s-error").textContent = `Could not score this submission: ${err.message}`;
      $("s-error").hidden = false;
    }
  });

  function renderScoring() {
    const { results, summary, reconstructed, integrity } = scoring;
    const box = $("s-integrity");
    if (integrity.checked && !integrity.ok) {
      box.className = "alert error";
      box.textContent = `⚠️ Integrity check failed: ${integrity.message}`;
    } else if (integrity.checked) {
      box.className = "alert success";
      box.textContent = `✓ Integrity check passed: ${integrity.message}`;
    } else {
      box.className = "alert info";
      box.textContent = integrity.message;
    }
    $("s-total").textContent = String(summary.total_score);
    $("s-potential").textContent = String(summary.total_potential);
    $("s-feasible").textContent = `${summary.n_feasible}/${summary.n_instances}`;
    $("s-util").textContent = fmt0(summary.avg_utilization) + "%";
    renderTable($("s-table"), [
      { key: "instance_id", label: "Instance" },
      { key: "feasible", label: "Feasible", fmt: yesNo },
      { key: "error", label: "Issue", text: true },
      { key: "profit", label: "Profit" },
      { key: "potential_profit", label: "Potential profit" },
      { key: "utilization", label: "Utilization (%)", fmt: dec1 },
      { key: "items_placed", label: "Items placed" },
      { key: "items_total", label: "Items offered" },
    ], results);

    const sel = $("s-select");
    sel.replaceChildren(...[...reconstructed.keys()].sort((a, b) => a - b).map((id) => new Option(`Instance ${id}`, id)));
    $("s-results").hidden = false;
    renderSelectedInstance();
  }

  function scoringReportText() {
    const { results, summary, integrity } = scoring;
    const lines = [
      "Greedy Bin Packing — Scoring Report",
      `Integrity check: ${integrity.ok ? "PASSED" : "FAILED"} — ${integrity.message}`,
      `Total score: ${summary.total_score} / ${summary.total_potential}`,
      `Feasible instances: ${summary.n_feasible}/${summary.n_instances}`,
      `Average utilization: ${fmt0(summary.avg_utilization)}%`,
      "",
      "Per-instance:",
    ];
    for (const r of results) {
      const note = r.feasible ? "" : ` [INFEASIBLE — ${r.error}, scored 0]`;
      lines.push(
        `  Instance ${r.instance_id}: ${r.profit}/${r.potential_profit} profit${note}, ` +
          `${fmt0(r.utilization)}% utilization, ${r.items_placed}/${r.items_total} items placed`,
      );
    }
    return lines.join("\n");
  }

  function renderSelectedInstance() {
    const id = Number($("s-select").value);
    const d = scoring.reconstructed.get(id);
    if (!d) return;
    $("s-infeasible").hidden = d.feasible;
    plot($("s-plot"), P.buildInstanceFigure(d.bin_w, d.bin_h, d.items_by_id, d.placed, d.feasible));
  }
  $("s-select").addEventListener("change", renderSelectedInstance);
  $("s-dl-report").addEventListener("click", () => download(scoringReportText(), "scoring_report.txt", "text/plain"));

  // ── boot ─────────────────────────────────────────────────────────────
  initGame();
  renderGame();
  const initial = location.hash.replace("#", "");
  setMode(["game", "challenge", "scoring"].includes(initial) ? initial : "game");
})();
