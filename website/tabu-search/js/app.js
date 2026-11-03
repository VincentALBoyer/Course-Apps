/* Tabu Search: The Grid Game — page controller. Port of
 * TabuSearch_GridGame_App/app.py: setup → construct (build an initial path)
 * → search (manual or auto neighborhoods, tenure, aspiration, deadlock,
 * auto-play) → finished report. */
(function () {
  "use strict";
  const { $, esc, fmt0 } = MG;
  const T = TS.logic;
  const AUTOPLAY_DELAY_MS = 600;

  const CONCEPTS = [
    ["Two swap moves: replace & shift", "A <strong>replace</strong> trades one cell currently in your path for one cell outside it, at a chosen position - the grid version of the slide's 'Replace' move. It's only <strong>feasible</strong> if the new cell keeps the path connected: adjacent (no diagonals) to whichever path neighbors sit on either side of that position. Any position can be replaced, including the very first cell (the <strong>head</strong>) or the very last one (the <strong>tail</strong>) - an endpoint only needs to stay connected to its single neighbor, not two.<br><br>A <strong>shift</strong> only applies at an extremity, matching the slide's 'Shift' move: instead of replacing the head or tail in place, drop it entirely and grow the path from the <strong>opposite</strong> end with a cell adjacent to <em>that</em> extremity. Both moves keep the path connected; most cells you could imagine picking are infeasible for either one - the grid's geometry does most of the filtering for you."],
    ["Neighborhood", "The <strong>neighborhood</strong> of your current path is every feasible swap you could make from it - one change away. Local search moves from neighborhood to neighborhood, one step at a time; a bigger neighborhood means more options per step, at the cost of more to evaluate."],
    ["Tabu list & tenure", "The <strong>tabu list</strong> remembers the cell removed by each of your last few moves and temporarily forbids bringing it back in. <strong>Tenure</strong> is how many future iterations that ban lasts. Tenure = 0 means no memory at all - nothing is ever forbidden."],
    ["Why tenure = 0 can cycle", "With no memory, the best available move right after escaping a local optimum can simply be <strong>reversing your last swap</strong> - undoing the very move that got you out, straight back into the trap. Tenure exists specifically to block that reversal for a while, forcing the search into genuinely new territory."],
    ["Escaping local optima on purpose", "At a <strong>local optimum</strong>, every feasible swap makes things worse. Local search would simply stop here. Tabu search doesn't: it accepts the <em>least-bad</em> move anyway (even a worsening one), then relies on the tabu list to stop it from immediately climbing back to the same spot - that's how it explores past a trap that pure hill-climbing can't."],
    ["Aspiration criterion", "A rigid tabu list can accidentally forbid a genuinely great move. The <strong>aspiration criterion</strong> is the escape clause: a tabu move is allowed anyway if it would produce a new <strong>best solution overall</strong> - the one exception worth breaking the rule for."],
    ["Deadlock", "If tenure is set too high relative to the neighborhood size, <em>every</em> feasible move can end up tabu at once, with nothing good enough to trigger aspiration either - a <strong>deadlock</strong> with no admissible move left. It's a real failure mode, not just a corner case: tune tenure relative to how big your neighborhood actually is."],
    ["Why not just brute force it?", "The number of possible paths grows roughly exponentially with path length - a few thousand on Easy, but well into the millions on Hard (see the setup screen's estimate). Exhaustive search still guarantees the true optimum, but it stops being realistic long before Hard difficulty. Tabu search trades that guarantee for a search that stays fast at any size."],
  ];
  $("concepts").innerHTML = CONCEPTS.map(([t, b]) => `<details><summary>${esc(t)}</summary><p>${b}</p></details>`).join("");

  // ── state ────────────────────────────────────────────────────────────
  const S = {
    phase: "setup", gameId: 0, gameCode: "", difficulty: "easy", size: 6, L: 5, grid: [], startTime: null, endTime: null,
    buildPath: [], redo: [],
    currentPath: [], previousPath: null, initialPath: [], initialSum: 0, bestPath: [], bestSum: 0,
    iteration: 0, tenure: 0, tabu: new Map(), tabuSource: new Map(), neighborMode: "manual",
    candidates: [], selectedOutPos: null, selectedCandIdx: null, history: [], visited: new Set(),
    autoplaying: false, notice: null,
  };

  const fmtCell = (cell) => `(${cell[0] + 1},${cell[1] + 1})`;
  const val = (cell) => S.grid[cell[0]][cell[1]];
  const pathStr = (path) => path.map(val).join(" → ") || "—";

  function startGame(diffKey, code) {
    const d = T.DIFFICULTIES[diffKey];
    const { code: c, seed } = T.resolveCode(code);
    Object.assign(S, {
      gameId: S.gameId + 1, gameCode: c, difficulty: diffKey, size: d.grid_size, L: d.path_length,
      grid: T.generateGrid(d.grid_size, new MG.PyRandom(seed)), phase: "construct",
      buildPath: [], redo: [], startTime: Date.now(), endTime: null, notice: null,
    });
  }

  function confirmInitial() {
    const path = S.buildPath.slice();
    const total = T.pathSum(S.grid, path);
    Object.assign(S, {
      currentPath: path, previousPath: null, initialPath: path, initialSum: total, bestPath: path, bestSum: total,
      iteration: 0, tenure: 0, tabu: new Map(), tabuSource: new Map(), neighborMode: "manual",
      candidates: [], selectedOutPos: null, selectedCandIdx: null,
      history: [{ iteration: 0, sum: total, best: total, delta: 0, tenure: 0, tabu: false, aspiration: false, repeat: false }],
      visited: new Set([T.pathKey(path)]), phase: "search", notice: null,
    });
  }

  const alreadyFound = (pos, cell, type) => S.candidates.some((c) => c.pos === pos && T.same(c.in_cell, cell) && c.move_type === type);

  /** Move types that would add a genuinely new candidate for `cell`. */
  function newValidMoves(cell) {
    const pos = S.selectedOutPos;
    if (pos === null) return [];
    const moves = [];
    if (T.swapIsFeasible(S.currentPath, pos, cell) && !alreadyFound(pos, cell, "replace")) moves.push("replace");
    if (T.shiftIsFeasible(S.currentPath, pos, cell) && !alreadyFound(pos, cell, "shift")) moves.push("shift");
    return moves;
  }

  const reverses = (cand) => S.previousPath !== null && T.pathKey(cand.new_path) === T.pathKey(S.previousPath);

  function handleSearchClick(cell) {
    const idx = S.currentPath.findIndex((p) => T.same(p, cell));
    if (idx >= 0) {
      S.selectedOutPos = S.selectedOutPos === idx ? null : idx;
      S.selectedCandIdx = null;
      return;
    }
    const pos = S.selectedOutPos;
    if (pos === null) return;
    const moves = newValidMoves(cell);
    if (!moves.length) return;
    for (const type of moves) {
      const cand = T.scoreCandidate(S.grid, S.currentPath, pos, cell, S.tabu, S.bestSum, type);
      cand.reverses_last = reverses(cand);
      S.candidates.push(cand);
    }
    S.selectedOutPos = null;
  }

  function revealFullNeighborhood() {
    const cands = T.enumerateNeighborhood(S.grid, S.currentPath, S.tabu, S.bestSum);
    cands.forEach((c) => { c.reverses_last = reverses(c); });
    S.candidates = cands;
    S.selectedCandIdx = null;
  }

  function clearCandidates() {
    S.candidates = [];
    S.selectedOutPos = null;
    S.selectedCandIdx = null;
  }

  function acceptMove(cand) {
    S.tabu = T.advanceTabu(S.tabu, S.tenure, cand.out_cell);
    // tabuSource records which swap each tabu entry blocks the reversal of
    // (display only), pruned to whatever advanceTabu kept.
    const src = new Map();
    for (const [k, v] of S.tabuSource) if (S.tabu.has(k)) src.set(k, v);
    if (S.tabu.has(T.key(cand.out_cell))) src.set(T.key(cand.out_cell), cand.in_cell);
    S.tabuSource = src;
    S.previousPath = S.currentPath;
    S.currentPath = cand.new_path;
    S.iteration += 1;
    const pk = T.pathKey(S.currentPath);
    const wasRepeat = S.visited.has(pk);
    S.visited.add(pk);
    if (cand.new_sum > S.bestSum) {
      S.bestSum = cand.new_sum;
      S.bestPath = S.currentPath;
    }
    S.history.push({
      iteration: S.iteration, sum: cand.new_sum, best: S.bestSum, delta: cand.delta, tenure: S.tenure,
      tabu: cand.tabu, aspiration: cand.aspiration, repeat: wasRepeat,
    });
    S.candidates = [];
    S.selectedOutPos = null;
    S.selectedCandIdx = null;
  }

  async function autoPlay(n) {
    S.autoplaying = true;
    S.notice = null;
    clearCandidates();
    render();
    const status = $("ap-status");
    const board = $("ap-board");
    for (let k = 0; k < n; k++) {
      const cands = T.enumerateNeighborhood(S.grid, S.currentPath, S.tabu, S.bestSum);
      const best = T.pickBestAdmissible(cands);
      if (!best) {
        S.notice = ["error", `🧱 Deadlock at iteration ${S.iteration} — tenure=${S.tenure} blocks every feasible swap. Auto-play stopped early.`];
        break;
      }
      if (S.visited.has(T.pathKey(best.new_path))) {
        S.notice = ["warning", `🔁 Cycling detected at iteration ${S.iteration} — tenure=${S.tenure} isn't enough memory to avoid repeating a past solution. Auto-play stopped early.`];
        break;
      }
      acceptMove(best);
      renderSearchGridOnly();
      const label = best.move_type === "shift" ? "shift" : "replace";
      board.innerHTML = `<p><strong>Iteration ${S.iteration}</strong> — ${label}: out ${fmtCell(best.out_cell)} for in ${fmtCell(best.in_cell)} (Δ${MG.signed(best.delta)})</p>
        <p>Current sum: <strong>${best.new_sum}</strong> &nbsp; | &nbsp; Best so far: <strong>${S.bestSum}</strong></p>`;
      status.textContent = `🤖 Auto-play — iteration ${S.iteration} / ${n}`;
      await MG.sleep(AUTOPLAY_DELAY_MS);
    }
    S.autoplaying = false;
    render();
  }

  // ── grid rendering ───────────────────────────────────────────────────
  /** stateFn(cell) -> {kind: "static"|"button", cls, disabled} */
  function renderGrid(el, stateFn) {
    const size = S.size;
    el.style.gridTemplateColumns = `24px repeat(${size}, auto)`;
    const parts = [`<span></span>`];
    for (let c = 0; c < size; c++) parts.push(`<span class="hdr">${c + 1}</span>`);
    for (let r = 0; r < size; r++) {
      parts.push(`<span class="hdr row">${r + 1}</span>`);
      for (let c = 0; c < size; c++) {
        const st = stateFn([r, c]);
        const v = S.grid[r][c];
        if (st.kind === "static") parts.push(`<span class="cell ${st.cls || ""}">${v}</span>`);
        else parts.push(`<button type="button" class="cell ${st.cls || ""}" data-r="${r}" data-c="${c}"${st.disabled ? " disabled" : ""} aria-label="Row ${r + 1}, column ${c + 1}, value ${v}">${v}</button>`);
      }
    }
    el.innerHTML = parts.join("");
  }

  function renderConstruct() {
    const path = S.buildPath;
    const L = S.L;
    $("construct-title").textContent = `Step 1 — Build your initial solution (${path.length} / ${L} cells)`;
    const available = new Set(T.availableNextCells(S.size, path).map(T.key));
    renderGrid($("construct-grid"), (cell) => {
      if (T.inPath(path, cell)) return { kind: "static", cls: "path" };
      return { kind: "button", disabled: !(path.length < L && available.has(T.key(cell))) };
    });
    $("construct-path").innerHTML = `<strong>Path so far:</strong> ${esc(pathStr(path))} &nbsp; (sum = <strong>${T.pathSum(S.grid, path)}</strong>)`;
    $("dead-end").hidden = !(path.length && path.length < L && !available.size);
    $("undo").disabled = !path.length;
    $("redo").disabled = !S.redo.length;
    $("clear").disabled = !path.length;
    $("confirm").disabled = path.length !== L;
  }

  function searchCellState(cell) {
    if (S.selectedCandIdx !== null) {
      const cand = S.candidates[S.selectedCandIdx];
      if (T.same(cell, cand.out_cell)) return { kind: "static", cls: "out" };
      if (T.same(cell, cand.in_cell)) return { kind: "static", cls: "in" };
      if (T.inPath(cand.new_path, cell)) return { kind: "static", cls: "path" };
      return { kind: "button", disabled: true };
    }
    if (S.neighborMode === "manual" && !S.autoplaying) {
      const idx = S.currentPath.findIndex((p) => T.same(p, cell));
      if (idx >= 0) return { kind: "button", cls: "path" + (idx === S.selectedOutPos ? " picked" : ""), disabled: false };
      const lit = S.selectedOutPos !== null && newValidMoves(cell).length > 0;
      return { kind: "button", cls: lit ? "target" : "", disabled: !lit };
    }
    if (T.inPath(S.currentPath, cell)) return { kind: "static", cls: "path" };
    return { kind: "button", disabled: true };
  }

  const renderSearchGridOnly = () => {
    renderGrid($("search-grid"), searchCellState);
    $("search-path").innerHTML = `<strong>Current path:</strong> ${esc(pathStr(S.currentPath))} &nbsp; (sum = <strong>${T.pathSum(S.grid, S.currentPath)}</strong>)`;
    $("m-sum").textContent = String(T.pathSum(S.grid, S.currentPath));
    $("m-best").textContent = String(S.bestSum);
    $("m-tabu").textContent = String(S.tabu.size);
    $("search-title").textContent = `Step 2 — Local Search (iteration ${S.iteration})`;
    $("side-best").textContent = String(S.bestSum);
    renderTabuList();
  };

  function renderTabuList() {
    if (!S.tabu.size) {
      $("tabu-list").innerHTML = `<p class="caption">🚫 Tabu list: empty — no recent swap is currently forbidden from being reversed.</p>`;
      return;
    }
    const entries = [...S.tabu].map(([k, rem]) => [k.split(",").map(Number), rem])
      .sort((a, b) => (b[1] - a[1]) || (a[0][0] - b[0][0]) || (a[0][1] - b[0][1]));
    const lines = entries.map(([out, rem]) => {
      const inCell = S.tabuSource.get(T.key(out));
      const desc = inCell ? `swap out ${fmtCell(out)} → in ${fmtCell(inCell)}` : `a move that removed ${fmtCell(out)}`;
      return `<li><strong>${desc}</strong>: bringing ${fmtCell(out)} back is forbidden for ${rem} more move(s)</li>`;
    });
    $("tabu-list").innerHTML = `<p style="margin:0">🚫 <strong>Tabu list</strong> (recent swaps that can't be reversed yet):</p><ul class="tabu-lines">${lines.join("")}</ul>`;
  }

  function renderSearch() {
    renderSearchGridOnly();
    $("tenure").value = String(S.tenure);
    $("tenure-out").textContent = String(S.tenure);
    document.querySelector(`input[name="neighbor-mode"][value="${S.neighborMode}"]`).checked = true;

    const last = S.history[S.history.length - 1];
    const notices = [];
    if (S.notice) notices.push(`<div class="alert ${S.notice[0]}">${esc(S.notice[1])}</div>`);
    if (last && last.repeat && S.iteration > 0) notices.push(`<div class="alert warning">🔁 You've returned to a solution you've already visited — a sign of cycling. Try raising the tabu tenure.</div>`);
    $("search-notice").innerHTML = notices.join("");

    const lock = S.autoplaying;
    $("tenure").disabled = lock;
    document.querySelectorAll('input[name="neighbor-mode"]').forEach((i) => { i.disabled = lock; });
    $("ap-start").disabled = lock;
    $("ap-live").hidden = !lock;

    // hint above the grid
    let hint = "";
    if (S.selectedCandIdx !== null) {
      const cand = S.candidates[S.selectedCandIdx];
      hint = `<p><strong>Selected:</strong> ${esc(pathStr(cand.new_path))} &nbsp; (sum = <strong>${cand.new_sum}</strong>, Δ${MG.signed(cand.delta)}) — 🟧 leaving, 🟩 arriving</p>
        <p class="caption">Confirm with ▶ Next round, or click the row again (or another row) to change the selection.</p>`;
    } else if (S.neighborMode === "manual") {
      if (S.selectedOutPos === null) {
        hint = `<p class="caption">Click a cell <strong>in your path</strong> to select it for swapping (click it again to deselect) — valid replacement cells will light up.</p>`;
      } else {
        const out = S.currentPath[S.selectedOutPos];
        hint = `<p class="caption">Selected ${fmtCell(out)}=${val(out)} — click a highlighted cell to swap it in, or click it again to deselect.</p>`;
      }
    }
    $("search-hint").innerHTML = lock ? "" : hint;
    $("reveal").hidden = lock || S.selectedCandIdx !== null || S.neighborMode !== "auto";
    renderCandidates();
  }

  function renderCandidates() {
    const el = $("candidates");
    if (S.autoplaying) { el.innerHTML = ""; return; }
    const total = T.enumerateNeighborhood(S.grid, S.currentPath, S.tabu, S.bestSum).length;
    const cands = S.candidates;
    const out = [`<div class="list-title"><strong>Candidate neighbors</strong> — ${cands.length} / ${total} found</div>`];
    if (!cands.length) {
      out.push(`<div class="alert info">No candidates yet — generate at least one swap to see it here.</div>`);
      el.innerHTML = out.join("");
      return;
    }
    out.push(`<p class="caption">Click a row to select that swap on the grid — including a worse one, on purpose, to escape a local optimum. Then confirm with ▶ Next round.</p>`);
    let admissible = 0;
    const rows = cands.map((c, i) => {
      const outV = val(c.out_cell);
      const inV = val(c.in_cell);
      let status = c.tabu && !c.aspiration ? "🚫 TABU" : c.tabu ? "🌟 aspiration" : "✅";
      if (c.reverses_last) status += " ↩️";
      const move = c.move_type === "shift"
        ? `↔️ shift: drop ${c.pos === 0 ? "head" : "tail"} ${fmtCell(c.out_cell)}=${outV} → grow ${c.pos === 0 ? "tail" : "head"} with ${fmtCell(c.in_cell)}=${inV}`
        : `pos ${c.pos + 1}: out ${fmtCell(c.out_cell)}=${outV} → in ${fmtCell(c.in_cell)}=${inV}`;
      const sel = S.selectedCandIdx === i;
      let act = `<span class="caption">blocked</span>`;
      if (c.admissible) {
        admissible++;
        act = `<button class="btn small${sel ? " primary" : ""}" data-act="select" data-i="${i}">${sel ? "✓ Shown" : "Select"}</button>`;
      }
      return `<div class="cand${sel ? " selected" : ""}"><strong>#${i + 1}</strong><span class="move">${move}</span><span class="res">sum <strong>${c.new_sum}</strong> (Δ${MG.signed(c.delta)}) · ${status}</span><span class="act">${act}</span></div>`;
    });
    out.push(`<div class="cands">${rows.join("")}</div>`);
    if (!admissible) {
      out.push(`<div class="alert warning">⚠️ Every candidate here is blocked by the tabu list — a deadlock. Lower the tenure, or clear the tabu list to escape (a deliberate rule-break, for demonstration).</div>
        <button class="btn" data-act="clear-tabu">🧹 Clear tabu list &amp; continue</button>`);
    } else {
      out.push(`<div class="row"><button class="btn primary" data-act="next"${S.selectedCandIdx === null ? " disabled" : ""}>▶ Next round</button>
        <button class="btn" data-act="clear-cands">🗑 Clear candidate list</button></div>`);
    }
    el.innerHTML = out.join("");
  }

  function renderFinished() {
    const imp = S.bestSum - S.initialSum;
    const metric = (l, v, d) => `<div><div class="metric-label">${esc(l)}</div><div class="metric-value">${esc(v)}</div>${d ? `<div class="metric-delta">↑ ${esc(d)}</div>` : ""}</div>`;
    $("fin-metrics").innerHTML = [
      metric("Initial sum", String(S.initialSum)),
      metric("Best sum found", String(S.bestSum), imp ? String(imp) : ""),
      metric("Iterations run", String(S.iteration)),
      metric("Total time", fmt0((S.endTime - S.startTime) / 1000) + "s"),
    ].join("");
    const nAsp = S.history.filter((h) => h.aspiration).length;
    const nRep = S.history.filter((h) => h.repeat).length;
    $("fin-caption").textContent = `Aspiration overrides used: ${nAsp} · Repeated solutions visited: ${nRep} · Difficulty: ${T.DIFFICULTIES[S.difficulty].label} · Game code: ${S.gameCode}`;
    renderChart();
    MG.renderTable($("history-table"), [
      { key: "iteration", label: "Iteration" }, { key: "sum", label: "Sum" }, { key: "best", label: "Best" },
      { key: "delta", label: "Δ", fmt: MG.signed }, { key: "tenure", label: "Tenure" },
      { key: "tabu", label: "Was tabu", fmt: MG.yesNo }, { key: "aspiration", label: "Aspiration used", fmt: MG.yesNo },
      { key: "repeat", label: "Repeated solution", fmt: MG.yesNo },
    ], S.history);
    $("fin-best").innerHTML = `<strong>Best path found:</strong> ${esc(pathStr(S.bestPath))}`;
  }

  function renderChart() {
    const h = S.history;
    const its = h.map((r) => r.iteration);
    MG.plot($("progress-chart"), [
      { type: "scatter", mode: "lines", x: its, y: its.map(() => S.initialSum), line: { color: "#c3c2b7", dash: "dash", width: 1.5 }, name: `Initial solution (${S.initialSum})`, hoverinfo: "skip" },
      { type: "scatter", mode: "lines+markers", x: its, y: h.map((r) => r.sum), name: "Current solution", line: { color: "#eb6834", width: 2 }, marker: { size: 7, color: "#eb6834" }, hovertemplate: "Iteration %{x}<br>Current sum: %{y}<extra></extra>" },
      { type: "scatter", mode: "lines+markers", x: its, y: h.map((r) => r.best), name: "Best found", line: { color: "#2a78d6", width: 3 }, marker: { size: 9, color: "#2a78d6" }, hovertemplate: "Iteration %{x}<br>Best sum: %{y}<extra></extra>" },
    ], {
      height: 300, margin: { l: 50, r: 10, t: 10, b: 45 },
      legend: { orientation: "h", yanchor: "bottom", y: 1.02, x: 0 },
      xaxis: { title: { text: "Iteration" }, dtick: 1, zeroline: false, tickfont: { size: 10 } },
      yaxis: { title: { text: "Path sum" }, zeroline: false },
    }, { displayModeBar: false });
  }

  function updateElapsed() {
    if (S.phase === "search" && S.startTime) $("m-elapsed").textContent = fmt0((Date.now() - S.startTime) / 1000) + "s";
  }
  setInterval(updateElapsed, 1000);

  function render() {
    for (const p of ["setup", "construct", "search", "finished"]) $("phase-" + p).hidden = S.phase !== p;
    $("status-panel").hidden = S.phase === "setup";
    $("side-code").textContent = S.gameCode;
    $("side-diff").textContent = T.DIFFICULTIES[S.difficulty].label;
    $("side-best-wrap").hidden = S.phase !== "search";
    $("side-best").textContent = String(S.bestSum);
    $("finish").hidden = S.phase !== "search";
    $("finish").disabled = $("side-new").disabled = S.autoplaying;
    if (S.phase === "construct") renderConstruct();
    else if (S.phase === "search") { renderSearch(); updateElapsed(); }
    else if (S.phase === "finished") renderFinished();
  }

  // ── wiring ───────────────────────────────────────────────────────────
  function syncDifficulty() {
    const d = T.DIFFICULTIES[document.querySelector('input[name="difficulty"]:checked').value];
    const est = T.estimateMaxPaths(d.grid_size, d.path_length);
    const note = est < 10000 ? "Small enough you could imagine checking a lot of them by hand." : "Far too many to check by hand — this is why we need a smart search strategy.";
    $("difficulty-caption").innerHTML = `${esc(d.blurb)} — up to roughly <strong>${est.toLocaleString("en-US")}</strong> possible paths of this length (rough upper bound). ${note}`;
  }
  document.querySelectorAll('input[name="difficulty"]').forEach((i) => i.addEventListener("change", syncDifficulty));
  syncDifficulty();

  $("start").addEventListener("click", () => {
    startGame(document.querySelector('input[name="difficulty"]:checked').value, $("code").value);
    render();
    window.scrollTo({ top: 0 });
  });
  $("code").addEventListener("keydown", (e) => { if (e.key === "Enter") $("start").click(); });

  $("construct-grid").addEventListener("click", (e) => {
    const b = e.target.closest("button.cell");
    if (!b || b.disabled) return;
    S.buildPath.push([Number(b.dataset.r), Number(b.dataset.c)]);
    S.redo = [];
    render();
  });
  $("undo").addEventListener("click", () => { if (S.buildPath.length) S.redo.push(S.buildPath.pop()); render(); });
  $("redo").addEventListener("click", () => { if (S.redo.length) S.buildPath.push(S.redo.pop()); render(); });
  $("clear").addEventListener("click", () => { S.buildPath = []; S.redo = []; render(); });
  $("confirm").addEventListener("click", () => { confirmInitial(); render(); });

  $("search-grid").addEventListener("click", (e) => {
    const b = e.target.closest("button.cell");
    if (!b || b.disabled || S.autoplaying || S.neighborMode !== "manual" || S.selectedCandIdx !== null) return;
    S.notice = null;
    handleSearchClick([Number(b.dataset.r), Number(b.dataset.c)]);
    render();
  });
  $("reveal").addEventListener("click", () => { S.notice = null; revealFullNeighborhood(); render(); });
  $("candidates").addEventListener("click", (e) => {
    const el = e.target.closest("[data-act]");
    if (!el) return;
    const act = el.dataset.act;
    S.notice = null;
    if (act === "select") {
      const i = Number(el.dataset.i);
      S.selectedCandIdx = S.selectedCandIdx === i ? null : i;
      S.selectedOutPos = null;
    } else if (act === "next") {
      if (S.selectedCandIdx !== null) acceptMove(S.candidates[S.selectedCandIdx]);
    } else if (act === "clear-cands") clearCandidates();
    else if (act === "clear-tabu") { S.tabu = new Map(); S.tabuSource = new Map(); }
    render();
  });
  $("tenure").addEventListener("input", (e) => { S.tenure = Number(e.target.value); $("tenure-out").textContent = e.target.value; });
  document.querySelectorAll('input[name="neighbor-mode"]').forEach((i) => i.addEventListener("change", (e) => { S.neighborMode = e.target.value; render(); }));
  $("ap-start").addEventListener("click", () => {
    const n = Math.max(1, Math.min(T.MAX_AUTOPLAY_ITERATIONS, Math.trunc(Number($("ap-n").value)) || 1));
    $("ap-n").value = String(n);
    autoPlay(n);
  });

  $("finish").addEventListener("click", () => { S.phase = "finished"; S.endTime = Date.now(); render(); });
  $("side-new").addEventListener("click", () => { S.phase = "setup"; render(); });
  $("replay").addEventListener("click", () => { S.phase = "construct"; S.buildPath = []; S.redo = []; render(); });
  $("new-game").addEventListener("click", () => { S.phase = "setup"; render(); });

  MG.theme.onChange(() => { if (S.phase === "finished") renderChart(); });
  window.addEventListener("beforeunload", (e) => { if (S.phase === "construct" || S.phase === "search") e.preventDefault(); });

  render();
})();
