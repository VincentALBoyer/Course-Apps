/* Tabu Search: The Grid Game — page controller. Port of
 * TabuSearch_GridGame_App/app.py: setup → construct (build an initial path)
 * → search (manual or auto neighborhoods, tenure, aspiration, deadlock,
 * auto-play) → finished report.
 *
 * Differences from the Streamlit original (see logic.js): the neighborhood
 * is every swap that keeps the path connected (replace, shift or re-route),
 * and a tenure change always takes effect on the very next confirmed move. */
(function () {
  "use strict";
  const { $, esc, fmt0 } = MG;
  const T = TS.logic;
  const AUTOPLAY_DELAY_MS = 600;

  const CONCEPTS = [
    ["Swap moves: replace, shift & re-route", "Every move takes <strong>one cell out</strong> of your path and puts <strong>one cell in</strong>. It's <strong>feasible</strong> whenever the new set of cells can still be walked as one connected path (up, down, left, right, no revisits).<br><br>The game labels each move by what happens to the path: a <strong>replace</strong> puts the new cell in the old one's place; a <strong>shift</strong> drops the head or tail and grows the path from the <strong>opposite</strong> end; a <strong>re-route</strong> is any other swap, where the path has to be re-ordered to stay connected (for example a new cell that links the tail back to the head)."],
    ["Neighborhood", "The <strong>neighborhood</strong> of your current path is every feasible swap you could make from it, one change away. Local search moves from neighborhood to neighborhood, one step at a time; a bigger neighborhood means more options per step, at the cost of more to evaluate."],
    ["Tabu list & tenure", "The <strong>tabu list</strong> remembers the cell removed by each of your last few moves and temporarily forbids bringing it back in. <strong>Tenure</strong> is how many future moves that ban lasts. Tenure = 0 means no memory at all: nothing is ever forbidden. A new tenure applies from your next move on, so you can watch the list build up round by round."],
    ["Why tenure = 0 can cycle", "With no memory, the best available move right after escaping a local optimum can simply be <strong>reversing your last swap</strong>, undoing the very move that got you out, straight back into the trap. Tenure exists specifically to block that reversal for a while, forcing the search into genuinely new territory."],
    ["Escaping local optima on purpose", "At a <strong>local optimum</strong>, every feasible swap makes things worse. Local search would simply stop here. Tabu search doesn't: it accepts the <em>least-bad</em> move anyway (even a worsening one), then relies on the tabu list to stop it from immediately climbing back to the same spot. That's how it explores past a trap that pure hill-climbing can't."],
    ["Aspiration criterion", "A rigid tabu list can accidentally forbid a genuinely great move. The <strong>aspiration criterion</strong> is the escape clause: a tabu move is allowed anyway if it would produce a new <strong>best solution overall</strong>."],
    ["Deadlock", "If tenure is set too high relative to the neighborhood size, <em>every</em> feasible move can end up tabu at once, with nothing good enough to trigger aspiration either: a <strong>deadlock</strong> with no admissible move left. Tune tenure relative to how big your neighborhood actually is."],
    ["Why not just brute force it?", "The number of possible paths grows roughly exponentially with path length: a few thousand on Easy, but millions on Hard. Exhaustive search still guarantees the true optimum, but it stops being realistic long before Hard. Tabu search trades that guarantee for a search that stays fast at any size."],
  ];
  $("concepts").innerHTML = CONCEPTS.map(([t, b]) => `<details><summary>${esc(t)}</summary><p>${b}</p></details>`).join("");

  // ── state ────────────────────────────────────────────────────────────
  const S = {
    phase: "setup", gameId: 0, gameCode: "", difficulty: "easy", size: 6, L: 5, grid: [], startTime: null, endTime: null,
    buildPath: [], redo: [],
    currentPath: [], previousPath: null, initialPath: [], initialSum: 0, bestPath: [], bestSum: 0,
    iteration: 0, tenure: 0,
    // Tabu list: cell key -> {rem: moves it stays forbidden, inCell: what replaced it}.
    tabu: new Map(),
    neighborMode: "manual",
    candidates: [], selectedOutPos: null, selectedCandIdx: null, history: [], visited: new Set(),
    autoplaying: false, notice: null,
  };

  const fmtCell = (cell) => `(${cell[0] + 1},${cell[1] + 1})`;
  const val = (cell) => S.grid[cell[0]][cell[1]];
  const pathStr = (path) => path.map(val).join(" → ") || "—";
  /** Cells forbidden right now, with the moves each still has to wait. */
  const tabuNow = () => T.tabuRemaining(S.tabu);

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
      iteration: 0, tenure: 0, tabu: new Map(), neighborMode: "manual",
      candidates: [], selectedOutPos: null, selectedCandIdx: null,
      history: [{ iteration: 0, sum: total, best: total, delta: 0, tenure: 0, tabu: false, aspiration: false, repeat: false }],
      visited: new Set([T.pathKey(path)]), phase: "search", notice: null,
    });
  }

  const alreadyFound = (pos, cell) => S.candidates.some((c) => c.pos === pos && T.same(c.in_cell, cell));

  /** The new move `cell` would add for the selected path cell, or null. */
  function newValidMove(cell) {
    const pos = S.selectedOutPos;
    if (pos === null || alreadyFound(pos, cell)) return null;
    return T.moveFor(S.currentPath, pos, cell);
  }

  const reverses = (cand) => S.previousPath !== null && T.pathKey(cand.new_path) === T.pathKey(S.previousPath);

  function handleSearchClick(cell) {
    const idx = S.currentPath.findIndex((p) => T.same(p, cell));
    if (idx >= 0) {
      S.selectedOutPos = S.selectedOutPos === idx ? null : idx;
      S.selectedCandIdx = null;
      return;
    }
    const move = newValidMove(cell);
    if (!move) return;
    const cand = T.scoreCandidate(S.grid, S.currentPath, S.selectedOutPos, cell, tabuNow(), S.bestSum, move);
    cand.reverses_last = reverses(cand);
    S.candidates.push(cand);
    // Keep the path cell selected: the cell just added is no longer lit
    // (already a candidate), the other replacements stay clickable.
  }

  function revealFullNeighborhood() {
    const cands = T.enumerateNeighborhood(S.grid, S.currentPath, tabuNow(), S.bestSum);
    cands.forEach((c) => { c.reverses_last = reverses(c); });
    S.candidates = cands;
    S.selectedCandIdx = null;
  }

  function clearCandidates() {
    S.candidates = [];
    S.selectedOutPos = null;
    S.selectedCandIdx = null;
  }

  /** Tabu list changed (cleared): refresh the listed candidates' status. */
  function rescoreCandidates() {
    const tabu = tabuNow();
    S.candidates.forEach((c) => T.rescore(c, tabu, S.bestSum));
    if (S.selectedCandIdx !== null && !S.candidates[S.selectedCandIdx].admissible) S.selectedCandIdx = null;
  }

  function acceptMove(cand) {
    // Uses the tenure in force right now, so a slider change applies to
    // this very move and the list grows one entry per round.
    S.tabu = T.advanceTabu(S.tabu, S.tenure, cand.out_cell, cand.in_cell);
    S.iteration += 1;
    S.previousPath = S.currentPath;
    S.currentPath = cand.new_path;
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

  const moveLabel = (c) => (c.move_type === "shift" ? "shift" : c.move_type === "reroute" ? "re-route" : "replace");

  async function autoPlay(n) {
    S.autoplaying = true;
    S.notice = null;
    clearCandidates();
    render();
    const status = $("ap-status");
    const board = $("ap-board");
    for (let k = 0; k < n; k++) {
      const cands = T.enumerateNeighborhood(S.grid, S.currentPath, tabuNow(), S.bestSum);
      const best = T.pickBestAdmissible(cands);
      if (!best) {
        S.notice = ["error", `🧱 Deadlock at iteration ${S.iteration}: tenure=${S.tenure} blocks every feasible swap. Auto-play stopped early.`];
        break;
      }
      if (S.visited.has(T.pathKey(best.new_path))) {
        S.notice = ["warning", `🔁 Cycling detected at iteration ${S.iteration}: tenure=${S.tenure} isn't enough memory to avoid repeating a past solution. Auto-play stopped early.`];
        break;
      }
      acceptMove(best);
      renderSearchGridOnly();
      board.innerHTML = `<p><strong>Iteration ${S.iteration}</strong>: ${moveLabel(best)}, out ${fmtCell(best.out_cell)} for in ${fmtCell(best.in_cell)} (Δ${MG.signed(best.delta)}) · current sum <strong>${best.new_sum}</strong> · best <strong>${S.bestSum}</strong></p>`;
      status.textContent = `🤖 Auto-play: iteration ${S.iteration} / ${n}`;
      await MG.sleep(AUTOPLAY_DELAY_MS);
    }
    S.autoplaying = false;
    render();
  }

  // ── grid rendering ───────────────────────────────────────────────────
  /** Cell size that fits the grid in the window (and its column), so the
   * whole board is visible on a laptop at any difficulty. */
  function fitCells(el) {
    const scroller = el.parentElement;
    const top = scroller.getBoundingClientRect().top + window.scrollY;
    const gap = 3;
    const byHeight = Math.floor((window.innerHeight - top - 64) / (S.size + 0.5)) - gap;
    const byWidth = Math.floor((scroller.clientWidth - 28) / S.size) - gap;
    const cell = Math.max(24, Math.min(46, byHeight, byWidth));
    el.style.setProperty("--cell", cell + "px");
  }

  /** stateFn(cell) -> {kind: "static"|"button", cls, disabled} */
  function renderGrid(el, stateFn) {
    const size = S.size;
    el.style.gridTemplateColumns = `20px repeat(${size}, auto)`;
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
    fitCells(el);
  }

  function renderConstruct() {
    const path = S.buildPath;
    const L = S.L;
    $("construct-title").textContent = `Step 1 · Build your initial path (${path.length} / ${L} cells)`;
    $("construct-sum").textContent = String(T.pathSum(S.grid, path));
    const available = new Set(T.availableNextCells(S.size, path).map(T.key));
    $("construct-path").textContent = pathStr(path);
    $("dead-end").hidden = !(path.length && path.length < L && !available.size);
    $("undo").disabled = !path.length;
    $("redo").disabled = !S.redo.length;
    $("clear").disabled = !path.length;
    $("confirm").disabled = path.length !== L;
    renderGrid($("construct-grid"), (cell) => {
      if (T.inPath(path, cell)) return { kind: "static", cls: "path" };
      return { kind: "button", disabled: !(path.length < L && available.has(T.key(cell))) };
    });
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
      const lit = S.selectedOutPos !== null && newValidMove(cell) !== null;
      return { kind: "button", cls: lit ? "target" : "", disabled: !lit };
    }
    if (T.inPath(S.currentPath, cell)) return { kind: "static", cls: "path" };
    return { kind: "button", disabled: true };
  }

  const renderSearchGridOnly = () => {
    const tabu = tabuNow();
    $("search-path").innerHTML = `<strong>Current path:</strong> ${esc(pathStr(S.currentPath))}`;
    $("m-sum").textContent = String(T.pathSum(S.grid, S.currentPath));
    $("m-best").textContent = String(S.bestSum);
    $("m-tabu").textContent = String(tabu.size);
    $("search-title").textContent = `Step 2 · Tabu search (iteration ${S.iteration})`;
    renderTabuList(tabu);
    renderGrid($("search-grid"), searchCellState);
  };

  function renderTabuList(tabu) {
    if (!tabu.size) {
      $("tabu-list").innerHTML = `<p class="ts-panel-title">🚫 Tabu list</p><p class="caption" style="margin:0">Empty: no removed cell is currently forbidden from coming back.${S.tenure ? ` Your next move will be remembered for ${S.tenure} move${S.tenure > 1 ? "s" : ""}.` : " Tenure is 0, so nothing is remembered."}</p>`;
      return;
    }
    const entries = [...tabu].map(([k, rem]) => [k.split(",").map(Number), rem])
      .sort((a, b) => (b[1] - a[1]) || (a[0][0] - b[0][0]) || (a[0][1] - b[0][1]));
    const lines = entries.map(([out, rem]) => {
      const inCell = S.tabu.get(T.key(out))?.inCell;
      const desc = inCell ? `out ${fmtCell(out)} → in ${fmtCell(inCell)}` : `removed ${fmtCell(out)}`;
      return `<li><strong>${desc}</strong>: ${fmtCell(out)} can't come back for ${rem} more move${rem > 1 ? "s" : ""}</li>`;
    });
    $("tabu-list").innerHTML = `<p class="ts-panel-title">🚫 Tabu list</p><ul class="tabu-lines">${lines.join("")}</ul>`;
  }

  function renderSearch() {
    renderSearchControls();
    renderSearchGridOnly();
    renderCandidates();
    fitCandidateList();
  }

  /** Cap the candidate list so it (and its buttons) end level with the
   * bottom of the grid; longer lists scroll inside that space. */
  function fitCandidateList() {
    const list = document.querySelector("#candidates .cands");
    if (!list) return;
    const gridBottom = $("search-grid").getBoundingClientRect().bottom;
    const actions = document.querySelector("#candidates .cand-actions, #candidates [data-act=clear-tabu]");
    const below = actions ? actions.getBoundingClientRect().height + 8 : 0;
    const room = gridBottom - list.getBoundingClientRect().top - below;
    list.style.maxHeight = Math.max(150, Math.floor(room)) + "px";
  }

  function renderSearchControls() {
    $("tenure").value = String(S.tenure);
    $("tenure-out").textContent = String(S.tenure);
    document.querySelector(`input[name="neighbor-mode"][value="${S.neighborMode}"]`).checked = true;

    const last = S.history[S.history.length - 1];
    const notices = [];
    if (S.notice) notices.push(`<div class="alert ${S.notice[0]}">${esc(S.notice[1])}</div>`);
    if (last && last.repeat && S.iteration > 0) notices.push(`<div class="alert warning">🔁 You've returned to a solution you've already visited, a sign of cycling. Try raising the tabu tenure.</div>`);
    $("search-notice").innerHTML = notices.join("");

    const lock = S.autoplaying;
    $("tenure").disabled = lock;
    document.querySelectorAll('input[name="neighbor-mode"]').forEach((i) => { i.disabled = lock; });
    $("ap-start").disabled = lock;
    $("ap-live").hidden = !lock;
    $("finish").disabled = lock;
    document.querySelectorAll(".js-new").forEach((b) => { b.disabled = lock; });

    let hint = "";
    if (S.selectedCandIdx !== null) {
      const cand = S.candidates[S.selectedCandIdx];
      hint = `<p class="caption"><strong>Selected:</strong> ${esc(pathStr(cand.new_path))} (sum <strong>${cand.new_sum}</strong>, Δ${MG.signed(cand.delta)}) · 🟧 leaving, 🟩 arriving. Confirm with ▶ Next round.</p>`;
    } else if (S.neighborMode === "manual") {
      if (S.selectedOutPos === null) {
        hint = `<p class="caption">Click a cell <strong>in your path</strong> to take it out (click again to deselect): every cell that could replace it lights up.</p>`;
      } else {
        const out = S.currentPath[S.selectedOutPos];
        hint = `<p class="caption">Taking out ${fmtCell(out)}=${val(out)}: click highlighted cells to add them as candidates, click another path cell to switch, or click ${fmtCell(out)} again to deselect.</p>`;
      }
    }
    $("search-hint").innerHTML = lock ? "" : hint;
    $("reveal").hidden = lock || S.selectedCandIdx !== null || S.neighborMode !== "auto";
  }

  function renderCandidates() {
    const el = $("candidates");
    if (S.autoplaying) { el.innerHTML = ""; return; }
    const total = T.enumerateNeighborhood(S.grid, S.currentPath, tabuNow(), S.bestSum).length;
    const cands = S.candidates;
    const out = [`<div class="list-title"><strong>Candidate neighbors</strong>: ${cands.length} / ${total} found</div>`];
    if (!cands.length) {
      out.push(`<div class="alert info">No candidates yet: generate at least one swap to see it here.</div>`);
      el.innerHTML = out.join("");
      return;
    }
    if (S.selectedCandIdx === null) out.push(`<p class="caption" style="margin:0 0 6px">Select a row to preview that swap on the grid (a worse one is fine, on purpose, to escape a local optimum), then confirm with ▶ Next round.</p>`);
    let admissible = 0;
    const rows = cands.map((c, i) => {
      const outV = val(c.out_cell);
      const inV = val(c.in_cell);
      let status = c.tabu && !c.aspiration ? "🚫 TABU" : c.tabu ? "🌟 aspiration" : "✅";
      if (c.reverses_last) status += " ↩️";
      const move = c.move_type === "shift"
        ? `↔️ shift: drop ${c.pos === 0 ? "head" : "tail"} ${fmtCell(c.out_cell)}=${outV}, grow ${c.pos === 0 ? "tail" : "head"} with ${fmtCell(c.in_cell)}=${inV}`
        : c.move_type === "reroute"
          ? `↪️ re-route: out ${fmtCell(c.out_cell)}=${outV}, in ${fmtCell(c.in_cell)}=${inV}`
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
      out.push(`<div class="alert warning">⚠️ Every candidate here is blocked by the tabu list: a deadlock. Lower the tenure, or clear the tabu list to escape (a deliberate rule-break, for demonstration).</div>
        <button class="btn" data-act="clear-tabu">🧹 Clear tabu list &amp; continue</button>`);
    } else {
      out.push(`<div class="cand-actions"><button class="btn" data-act="clear-cands">🗑 Clear list</button>
        <button class="btn primary" data-act="next"${S.selectedCandIdx === null ? " disabled" : ""}>▶ Next round</button></div>`);
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
    $("fin-caption").textContent = `Aspiration overrides used: ${nAsp} · Repeated solutions visited: ${nRep}`;
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
    // Game screens take the full width; the Concepts panel flows below.
    document.querySelector("main").classList.toggle("ts-wide", S.phase !== "setup");
    document.querySelectorAll(".js-code").forEach((el) => { el.textContent = S.gameCode; });
    document.querySelectorAll(".js-diff").forEach((el) => { el.textContent = `${S.size}×${S.size}`; });
    if (S.phase === "construct") renderConstruct();
    else if (S.phase === "search") { renderSearch(); updateElapsed(); }
    else if (S.phase === "finished") renderFinished();
  }

  // ── wiring ───────────────────────────────────────────────────────────
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
    else if (act === "clear-tabu") { S.tabu = new Map(); rescoreCandidates(); }
    render();
  });
  // A new tenure applies from the next confirmed move (acceptMove reads it);
  // the current tabu list is left as it is.
  $("tenure").addEventListener("input", (e) => {
    S.tenure = Number(e.target.value);
    render();
  });
  document.querySelectorAll('input[name="neighbor-mode"]').forEach((i) => i.addEventListener("change", (e) => { S.neighborMode = e.target.value; render(); }));
  $("ap-start").addEventListener("click", () => {
    const n = Math.max(1, Math.min(T.MAX_AUTOPLAY_ITERATIONS, Math.trunc(Number($("ap-n").value)) || 1));
    $("ap-n").value = String(n);
    autoPlay(n);
  });

  $("finish").addEventListener("click", () => { S.phase = "finished"; S.endTime = Date.now(); render(); window.scrollTo({ top: 0 }); });
  document.querySelectorAll(".js-new").forEach((b) => b.addEventListener("click", () => { S.phase = "setup"; render(); window.scrollTo({ top: 0 }); }));
  $("replay").addEventListener("click", () => { S.phase = "construct"; S.buildPath = []; S.redo = []; render(); });
  $("new-game").addEventListener("click", () => { S.phase = "setup"; render(); });

  let resizeTimer = null;
  window.addEventListener("resize", () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => { if (S.phase === "construct" || S.phase === "search") render(); }, 150);
  });
  MG.theme.onChange(() => { if (S.phase === "finished") renderChart(); });
  window.addEventListener("beforeunload", (e) => { if (S.phase === "construct" || S.phase === "search") e.preventDefault(); });

  render();
})();
