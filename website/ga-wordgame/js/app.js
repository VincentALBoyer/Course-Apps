/* GA Word Game — page controller. Port of GA_WordGame_App/app.py: same
 * phases (setup → breeding ⇄ selection → finished), the same mutation dice
 * and stagnation rule, auto-play, and messages. */
(function () {
  "use strict";
  const { $, esc, fmt0 } = MG;
  const G = GA.logic;

  const STAGNATION_THRESHOLD = 3; // generations without a new best before the dice gets aggressive
  const AUTOPLAY_DELAY_MS = 700;

  const CONCEPTS = [
    ["Gene, Chromosome & Fitness", "A <strong>gene</strong> is one letter; a <strong>chromosome</strong> is a full candidate word. <strong>Fitness</strong> scores how close a candidate is to the hidden word - the population only learns from that single number each round, never the letters themselves."],
    ["Scoring: Exact vs. Partial Credit", "<strong>Exact match</strong> only rewards letters in the exact right spot, so a word with every letter right but shifted by one position scores 0 - a harsh, deceptive fitness landscape. <strong>Partial credit</strong> also rewards wrong letters that are merely close alphabetically, giving the GA a smoother slope to climb instead of scattered cliffs. This is a real lesson in GA design: how you score a solution shapes how easily evolution can find it."],
    ["Selection: Choosing Parents", "Selection decides which individuals get to reproduce. Always picking the two fittest narrows the gene pool fast; occasionally breeding a weaker individual keeps letters in play that might matter later."],
    ["Crossover", "Single-point crossover cuts both parents at the same position and swaps tails, so each child blends letters from both parents. Where you cut controls how much of each parent survives into the children."],
    ["Mutation", "Mutation randomly replaces a gene (letter) in a child. It's the GA's only source of brand-new genetic material - without it, the population can only ever recombine letters already present in the initial population. Mutating more genes explores further from the parents, but also destroys more of what crossover just built."],
    ["Survivor Selection & Elitism", "After breeding, you choose who survives into the next generation. Keeping only the best (elitism) locks in progress fast but can lose diversity; keeping weaker individuals too preserves diversity at the cost of slower convergence."],
    ["Why does population size matter?", "A larger population explores more of the search space per generation (more diversity) but costs more fitness evaluations per round - the same quality-vs-cost trade-off you saw with search strategies."],
  ];
  $("concepts").innerHTML = CONCEPTS.map(([t, b]) => `<details><summary>${esc(t)}</summary><p>${b}</p></details>`).join("");

  // ── state ────────────────────────────────────────────────────────────
  const S = {
    phase: "setup", gameId: 0, hidden: "", L: 6, popSize: 6, mode: "exact", rng: null,
    population: [], roundIdx: 0, offspring: [], history: [], totalEvals: 0,
    found: false, winningWord: null, foundGen: null, stoppedManually: false,
    startTime: null, endTime: null, bestWord: null, bestFit: null, bestImprovedGen: 0,
    autoplaying: false,
  };
  // Per-pair UI choices, keyed like the Streamlit widget keys so they reset
  // per game / generation / pair (and come back after "Undo last pair").
  const UI = { order: new Map(), cut: new Map(), mut: new Map(), sel: new Map(), autoplayN: 5, autoplayOpen: false };

  const score = (w) => G.computeFitness(w, S.hidden, S.mode);
  const fmtScore = (v) => (S.mode === "partial" ? v.toFixed(2) : String(MG.pyRound(v)));

  function updateBest(word) {
    const f = score(word);
    if (S.bestFit === null || f > S.bestFit) {
      S.bestWord = word;
      S.bestFit = f;
      S.bestImprovedGen = S.roundIdx;
    }
  }

  function finish() {
    S.phase = "finished";
    S.endTime = Date.now();
  }

  function startGame(word, popSize, code, mode) {
    const rng = G.makeRng(code);
    const L = G.chars(word).length;
    const population = G.randomPopulation(popSize, L, rng);
    population.sort((a, b) => G.computeFitness(b, word, mode) - G.computeFitness(a, word, mode));
    const stats = G.populationStats(population, word, mode);
    Object.assign(S, {
      gameId: S.gameId + 1, hidden: word, L, popSize, mode, rng, population,
      roundIdx: 0, offspring: [], history: [{ generation: 0, best: stats.best, avg: stats.avg }],
      totalEvals: popSize, found: false, winningWord: null, foundGen: null, stoppedManually: false,
      startTime: Date.now(), endTime: null, phase: "breeding", bestWord: null, bestFit: null, bestImprovedGen: 0,
    });
    population.forEach(updateBest);
    const winner = population.find((w) => score(w) === L);
    if (winner) {
      Object.assign(S, { found: true, winningWord: winner, foundGen: 0 });
      finish();
    }
  }

  const isStagnant = () => S.roundIdx - S.bestImprovedGen >= STAGNATION_THRESHOLD;
  const pairKey = () => `${S.gameId}_${S.roundIdx}_${Math.floor(S.offspring.length / 2)}`;

  function toggleParent(i) {
    const k = pairKey();
    const order = (UI.order.get(k) || []).slice();
    const at = order.indexOf(i);
    if (at >= 0) order.splice(at, 1);
    else {
      order.push(i);
      if (order.length > 2) order.shift();
    }
    UI.order.set(k, order);
  }

  /** The 🎲 button: usually at most one gene (same overall odds as the
   *  classic 1/length-per-gene scheme); once progress stalls, 1–2 genes. */
  function randomizeMutation(key) {
    const rng = S.rng;
    const L = S.L;
    let positions;
    if (isStagnant()) {
      const n = L >= 2 && rng.random() < 0.5 ? 2 : 1;
      positions = rng.sample([...Array(L).keys()], n);
    } else {
      const pAny = 1 - (1 - 1.0 / L) ** L;
      positions = rng.random() < pAny ? [rng.randrange(L)] : [];
    }
    UI.mut.set(key, positions);
  }

  function commitPair(a, b, cut, m1, m2) {
    const rng = S.rng;
    let [c1, c2] = G.crossover(S.population[a], S.population[b], cut);
    for (const pos of [...m1].sort((x, y) => x - y)) c1 = G.mutate(c1, pos, rng);
    for (const pos of [...m2].sort((x, y) => x - y)) c2 = G.mutate(c2, pos, rng);
    for (const [word, mutated] of [[c1, new Set(m1)], [c2, new Set(m2)]]) {
      S.offspring.push({ word, fitness: score(word), mutated });
      updateBest(word);
    }
    S.totalEvals += 2;
    const gen = S.roundIdx + 1;
    const winner = S.offspring.find((o) => o.fitness === S.L);
    if (winner) {
      const fits = S.offspring.map((o) => o.fitness);
      S.history.push({ generation: gen, best: Math.max(...fits), avg: MG.pySum(fits) / fits.length });
      Object.assign(S, { found: true, winningWord: winner.word, foundGen: gen });
      finish();
    } else if (S.offspring.length >= S.popSize) {
      S.phase = "selection";
    }
  }

  function undoLastPair() {
    S.offspring = S.offspring.slice(0, -2);
    S.totalEvals -= 2;
  }

  const selKey = (src, i) => `${S.gameId}_${S.roundIdx}_${src}${i}`;

  function autoSelectBest() {
    const cands = S.population.map((w, i) => [selKey("p", i), score(w), 1])
      .concat(S.offspring.map((o, i) => [selKey("o", i), o.fitness, 0]));
    cands.sort((x, y) => (y[1] - x[1]) || (x[2] - y[2])); // offspring win ties at the cutoff
    const keep = new Set(cands.slice(0, S.popSize).map((c) => c[0]));
    for (const [k] of cands) UI.sel.set(k, keep.has(k));
  }

  function clearSelection() {
    S.population.forEach((_, i) => UI.sel.set(selKey("p", i), false));
    S.offspring.forEach((_, i) => UI.sel.set(selKey("o", i), false));
  }

  function chosenWords() {
    return S.population.filter((_, i) => UI.sel.get(selKey("p", i)))
      .concat(S.offspring.filter((_, i) => UI.sel.get(selKey("o", i))).map((o) => o.word));
  }

  function confirmSelection(words) {
    const gen = S.roundIdx + 1;
    const fits = words.map(score);
    S.history.push({ generation: gen, best: Math.max(...fits), avg: MG.pySum(fits) / fits.length });
    S.population = words.slice().sort((a, b) => score(b) - score(a));
    S.roundIdx = gen;
    S.offspring = [];
    S.phase = "breeding";
  }

  // ── auto-play ────────────────────────────────────────────────────────
  async function autoPlay(n) {
    S.autoplaying = true;
    render();
    const status = $("ap-status");
    const board = $("ap-board");
    const L = S.L;
    const say = (kind, text) => { status.className = "alert " + kind; status.textContent = text; };
    for (let k = 0; k < n; k++) {
      if (S.found) break;
      const gen = S.roundIdx + 1;
      say("info", `🤖 Auto-play — generation ${gen}: breeding...`);
      const result = G.autoRunGeneration(S.population, S.hidden, S.popSize, S.mode, S.rng);
      S.totalEvals += result.offspring.length;
      result.offspring.forEach((o) => updateBest(o.word));
      board.innerHTML = `<div class="list-title">New offspring</div>` + result.offspring.map((o, i) =>
        memberRow(`<strong>C${i + 1}</strong>`, o.word, o.fitness, { mutated: o.mutated, size: 24 })).join("");
      await MG.sleep(AUTOPLAY_DELAY_MS);

      const winner = result.offspring.find((o) => o.fitness === L);
      const fits = result.population.map(score);
      S.history.push({ generation: gen, best: Math.max(...fits), avg: MG.pySum(fits) / fits.length });
      S.population = result.population;
      S.roundIdx = gen;
      S.offspring = [];
      if (winner) {
        Object.assign(S, { found: true, winningWord: winner.word, foundGen: gen });
        say("success", `🤖 Found it in generation ${gen}!`);
        await MG.sleep(AUTOPLAY_DELAY_MS);
        finish();
        break;
      }
      say("success", `🤖 Generation ${gen} complete — best fitness ${fmtScore(Math.max(...fits))}/${L}`);
      board.innerHTML = `<div class="list-title">Population after generation ${gen}</div>` + result.population.map((w, i) =>
        memberRow(`<strong>M${i + 1}</strong>`, w, score(w), { size: 24 })).join("");
      await MG.sleep(AUTOPLAY_DELAY_MS);
    }
    S.autoplaying = false;
    render();
  }

  // ── rendering helpers ────────────────────────────────────────────────
  function tiles(word, { cut = null, mutated = new Set(), size = 30 } = {}) {
    const parts = [];
    Array.from(word).forEach((ch, i) => {
      parts.push(`<span class="tile${mutated.has(i) ? " mut" : ""}">${esc(ch)}</span>`);
      if (cut !== null && i === cut - 1) parts.push(`<span class="tile-cut"></span>`);
    });
    return `<span class="tiles" style="--tile:${size}px">${parts.join("")}</span>`;
  }

  const fitText = (f) => `Fitness <strong>${fmtScore(f)}/${S.L}</strong>`;
  const memberRow = (label, word, f, opts) => `<div class="member"><span>${label}</span>${tiles(word, opts)}<span class="fit">${fitText(f)}</span></div>`;

  function renderBreeding(body) {
    const L = S.L;
    const pk = pairKey();
    const selected = UI.order.get(pk) || [];
    const out = [];
    if (!S.offspring.length) {
      out.push(`<details class="expander" id="ap-details"${UI.autoplayOpen ? " open" : ""}>
        <summary>🤖 Auto-Play (watch the GA run itself)</summary>
        <div class="row">
          <label class="field" style="margin:8px 0"><span>Generations to auto-play</span>
            <input type="number" id="ap-n" min="1" max="${G.MAX_AUTOPLAY_GENERATIONS}" step="1" value="${UI.autoplayN}" /></label>
          <button class="btn" data-act="autoplay">▶ Start</button>
        </div>
        <p class="caption">Automatically breeds and selects survivors, generation after generation, so you can watch the GA converge on its own. Stops early the moment the hidden word is found.</p>
      </details>`);
    }

    const left = [`<div class="list-title">Current Population</div><p class="caption">Click a member's M# to select it as a parent.</p>`];
    S.population.forEach((w, i) => {
      left.push(`<div class="member"><button class="mbtn${selected.includes(i) ? " on" : ""}" data-act="parent" data-i="${i}" aria-pressed="${selected.includes(i)}">M${i + 1}</button>${tiles(w, { size: 26 })}<span class="fit">${fitText(score(w))}</span></div>`);
    });
    left.push(`<p class="caption">Offspring created: ${S.offspring.length} / ${S.popSize}</p><div class="progress"><div style="width:${(S.offspring.length / S.popSize) * 100}%"></div></div>`);
    if (S.offspring.length) {
      left.push(`<div class="list-title">Offspring pool so far</div>`);
      S.offspring.forEach((o, i) => left.push(memberRow(`<strong>C${i + 1}</strong>`, o.word, o.fitness, { mutated: o.mutated, size: 26 })));
      left.push(`<button class="btn" data-act="undo">↺ Undo last pair</button>`);
    }

    const right = [`<div class="list-title">Breeding Workspace</div>`];
    if (selected.length < 2) {
      right.push(`<div class="alert info">← Click 2 members in the population list to select them as parents.</div>`);
    } else {
      const cut = UI.cut.has(pk) ? UI.cut.get(pk) : Math.floor(L / 2);
      right.push(`<div class="workspace">
        <label class="field" style="max-width:none"><span>Crossover cut position <output id="cut-out">${cut}</output></span>
          <input type="range" id="cut" min="1" max="${L - 1}" step="1" value="${cut}" /></label>
        <p class="caption">Child 1 takes letters 1..cut from Parent A then the rest from Parent B. Child 2 gets the opposite split.</p>
        <div id="ws-dyn"></div>
      </div>`);
    }

    out.push(`<div class="ga-cols"><div>${left.join("")}</div><div>${right.join("")}</div></div>`);
    body.innerHTML = out.join("");
    if (selected.length >= 2) renderWorkspace();
  }

  /** The part of the workspace that depends on the cut slider. */
  function renderWorkspace() {
    const L = S.L;
    const pk = pairKey();
    const [a, b] = (UI.order.get(pk) || []).slice().sort((x, y) => x - y);
    const cut = UI.cut.has(pk) ? UI.cut.get(pk) : Math.floor(L / 2);
    const [c1, c2] = G.crossover(S.population[a], S.population[b], cut);
    const stagnant = isStagnant();
    const diceHelp = stagnant
      ? "Progress has stalled, so this rolls 1-2 mutated genes instead of the usual 0-1."
      : "Randomly mutates at most one gene (~1/N chance of any mutation at all).";
    const child = (n, word) => {
      const key = `${pk}_${a}_${b}_${n}`;
      const picked = new Set(UI.mut.get(key) || []);
      const pills = Array.from(word).map((ch, i) =>
        `<button class="pill${picked.has(i) ? " on" : ""}" data-act="pill" data-key="${key}" data-i="${i}" aria-pressed="${picked.has(i)}">${esc(ch)}</button>`).join("");
      return `<div>
        <div class="child-head"><span>Child ${n} &nbsp; fitness <strong>${fmtScore(score(word))}/${L}</strong></span>
          <button class="btn small dice" data-act="dice" data-key="${key}" title="${esc(diceHelp)}" aria-label="Roll mutation dice for child ${n}">🎲</button></div>
        <div class="pills-label">Click letters to mutate (optional, any number)</div>
        <div class="pills">${pills}</div>
      </div>`;
    };
    $("ws-dyn").innerHTML = `
      <p class="caption">Crossing M${a + 1} × M${b + 1} at cut position ${cut}</p>
      <div class="parent-line">A ${tiles(S.population[a], { cut, size: 22 })}</div>
      <div class="parent-line">B ${tiles(S.population[b], { cut, size: 22 })}</div>
      ${stagnant ? `<p class="caption">🌡️ No new best fitness in ${STAGNATION_THRESHOLD}+ generations — the 🎲 dice is mutating more aggressively to help you escape the plateau.</p>` : ""}
      <div class="children">${child(1, c1)}${child(2, c2)}</div>
      <p class="caption">Fitness shown is before mutation - clicked (or 🎲 randomized) letters are replaced with a random new one once added.</p>
      <button class="btn primary" data-act="commit">✅ Add to offspring pool</button>`;
  }

  function renderSelection(body) {
    const row = (src, i, word, f) => {
      const k = selKey(src, i);
      return `<label class="member sel"><input type="checkbox" data-act="keep" data-key="${k}"${UI.sel.get(k) ? " checked" : ""} aria-label="Keep ${src === "p" ? "M" : "C"}${i + 1}" />
        <span><strong>${src === "p" ? "M" : "C"}${i + 1}</strong> &nbsp; ${tiles(word, { size: 22 })}</span><span class="fit"><strong>${fmtScore(f)}/${S.L}</strong></span></label>`;
    };
    body.innerHTML = `
      <div class="alert info">Offspring pool complete! Select exactly <strong>${S.popSize}</strong> individuals to carry into the next generation.</div>
      <div class="ga-cols even">
        <div><div class="list-title">Current Population</div>${S.population.map((w, i) => row("p", i, w, score(w))).join("")}</div>
        <div><div class="list-title">Offspring</div>${S.offspring.map((o, i) => row("o", i, o.word, o.fitness)).join("")}</div>
      </div>
      <div id="sel-status"></div>
      <div class="row">
        <button class="btn" data-act="auto-select">⭐ Auto-select best ${S.popSize}</button>
        <button class="btn" data-act="clear-select">✖ Clear selection</button>
        <button class="btn primary" data-act="confirm" id="confirm-sel">✅ Confirm & start next round</button>
      </div>`;
    renderSelectionStatus();
  }

  function renderSelectionStatus() {
    const n = chosenWords().length;
    $("sel-status").innerHTML = `<div class="alert ${n === S.popSize ? "success" : "warning"}">Selected: ${n} / ${S.popSize}</div>`;
    $("confirm-sel").disabled = n !== S.popSize;
  }

  function renderFinished() {
    const L = S.L;
    const alert = $("fin-alert");
    if (S.found) {
      alert.innerHTML = `<div class="alert success">🎉 Found the hidden word <strong>${esc(S.hidden)}</strong> in generation ${S.foundGen}!</div>`;
    } else {
      alert.innerHTML = `<div class="alert info">Game stopped. The hidden word was <strong>${esc(S.hidden)}</strong>.</div>
        <p>Best candidate found: ${tiles(S.bestWord, { size: 28 })} &nbsp; fitness <strong>${fmtScore(S.bestFit)}/${L}</strong></p>`;
    }
    const gens = S.found ? S.foundGen : S.roundIdx;
    const metric = (l, v) => `<div><div class="metric-label">${esc(l)}</div><div class="metric-value">${esc(v)}</div></div>`;
    $("fin-metrics").innerHTML = [
      metric("Generations played", String(gens)),
      metric("Best fitness reached", `${fmtScore(S.bestFit)} / ${L}`),
      metric("Individuals evaluated", String(S.totalEvals)),
      metric("Total time", fmt0((S.endTime - S.startTime) / 1000) + "s"),
    ].join("");
    $("fin-scoring").textContent = `Scoring method: ${G.SCORING_LABELS[S.mode]}`;
    renderChart();
    const partial = S.mode === "partial";
    MG.renderTable($("history-table"), [
      { key: "generation", label: "Generation" },
      { key: "best", label: "Best fitness", fmt: (v) => (partial ? v.toFixed(2) : String(MG.pyRound(v))) },
      { key: "avg", label: "Average fitness", fmt: (v) => v.toFixed(2) },
    ], S.history);
  }

  function renderChart() {
    const h = S.history;
    const gens = h.map((r) => r.generation);
    const L = S.L;
    MG.plot($("fitness-chart"), [
      { type: "scatter", mode: "lines", x: gens, y: gens.map(() => L), line: { color: "#c3c2b7", dash: "dash", width: 1.5 }, name: `Target (${L})`, hoverinfo: "skip" },
      { type: "scatter", mode: "lines+markers", x: gens, y: h.map((r) => r.avg), name: "Average fitness", line: { color: "#eb6834", width: 2 }, marker: { size: 7, color: "#eb6834" }, hovertemplate: "Generation %{x}<br>Average fitness: %{y:.2f}<extra></extra>" },
      { type: "scatter", mode: "lines+markers", x: gens, y: h.map((r) => r.best), name: "Best fitness", line: { color: "#2a78d6", width: 3 }, marker: { size: 9, color: "#2a78d6" }, hovertemplate: "Generation %{x}<br>Best fitness: %{y}<extra></extra>" },
    ], {
      height: 300, margin: { l: 50, r: 10, t: 10, b: 45 },
      legend: { orientation: "h", yanchor: "bottom", y: 1.02, x: 0 },
      xaxis: { title: { text: "Generation" }, dtick: 1, zeroline: false, tickfont: { size: 10 } },
      yaxis: { title: { text: S.mode === "partial" ? "Fitness (partial credit)" : "Fitness (letters correct)" }, range: [-0.3, L + 0.6], dtick: 1, zeroline: false },
    }, { displayModeBar: false });
  }

  function updateElapsed() {
    if ((S.phase === "breeding" || S.phase === "selection") && S.startTime) $("m-elapsed").textContent = fmt0((Date.now() - S.startTime) / 1000) + "s";
  }
  setInterval(updateElapsed, 1000);

  function render() {
    const playing = S.phase === "breeding" || S.phase === "selection";
    $("phase-setup").hidden = S.phase !== "setup";
    $("phase-play").hidden = !playing;
    $("phase-finished").hidden = S.phase !== "finished";

    $("status-panel").hidden = S.phase === "setup";
    if (S.phase !== "setup") {
      $("side-best").textContent = `${fmtScore(S.bestFit)} / ${S.L}`;
      $("side-action").textContent = playing ? "⏹ Stop Game" : "↺ New Game";
      $("side-action").disabled = S.autoplaying;
    }

    if (playing) {
      const label = S.phase === "breeding" ? "Breeding offspring" : "Selecting survivors";
      $("gen-title").textContent = `Generation ${S.roundIdx + 1} — ${label}`;
      $("gen-scoring").textContent = `Scoring: ${G.SCORING_LABELS[S.mode]}`;
      $("m-pop").textContent = String(S.popSize);
      $("m-target").textContent = String(S.L);
      updateElapsed();
      const body = $("play-body");
      if (S.autoplaying) body.innerHTML = `<div id="ap-status" class="alert info"></div><div id="ap-board" class="autoplay-board"></div>`;
      else if (S.phase === "breeding") renderBreeding(body);
      else renderSelection(body);
    } else if (S.phase === "finished") {
      renderFinished();
    }
  }

  // ── wiring ───────────────────────────────────────────────────────────
  const chosen = (name) => document.querySelector(`input[name="${name}"]:checked`).value;

  function onStart() {
    const word = G.cleanHiddenWord($("hidden-word").value);
    const n = G.chars(word).length;
    if (n < G.MIN_WORD_LEN || n > G.MAX_WORD_LEN) {
      $("setup-error").textContent = `Enter a hidden word between ${G.MIN_WORD_LEN} and ${G.MAX_WORD_LEN} letters (letters only).`;
      $("setup-error").hidden = false;
      return;
    }
    $("setup-error").hidden = true;
    startGame(word, Number(chosen("pop")), $("code").value, chosen("scoring"));
    if (S.found) MG.balloons();
    render();
    window.scrollTo({ top: 0 });
  }
  $("start").addEventListener("click", onStart);
  for (const id of ["hidden-word", "code"]) $(id).addEventListener("keydown", (e) => { if (e.key === "Enter") onStart(); });

  const body = $("play-body");
  body.addEventListener("click", (e) => {
    const el = e.target.closest("[data-act]");
    if (!el || S.autoplaying) return;
    const act = el.dataset.act;
    const pk = pairKey();
    if (act === "parent") toggleParent(Number(el.dataset.i));
    else if (act === "undo") undoLastPair();
    else if (act === "pill") {
      const set = new Set(UI.mut.get(el.dataset.key) || []);
      const i = Number(el.dataset.i);
      if (set.has(i)) set.delete(i); else set.add(i);
      UI.mut.set(el.dataset.key, [...set]);
      renderWorkspace();
      return;
    } else if (act === "dice") {
      randomizeMutation(el.dataset.key);
      renderWorkspace();
      return;
    } else if (act === "commit") {
      const [a, b] = (UI.order.get(pk) || []).slice().sort((x, y) => x - y);
      const cut = UI.cut.has(pk) ? UI.cut.get(pk) : Math.floor(S.L / 2);
      commitPair(a, b, cut, UI.mut.get(`${pk}_${a}_${b}_1`) || [], UI.mut.get(`${pk}_${a}_${b}_2`) || []);
      if (S.found) MG.balloons();
    } else if (act === "autoplay") {
      const n = Math.max(1, Math.min(G.MAX_AUTOPLAY_GENERATIONS, Math.trunc(Number($("ap-n").value)) || 1));
      UI.autoplayN = n;
      autoPlay(n).then(() => { if (S.found) MG.balloons(); });
      return;
    } else if (act === "auto-select") { autoSelectBest(); }
    else if (act === "clear-select") { clearSelection(); }
    else if (act === "confirm") { confirmSelection(chosenWords()); }
    else if (act === "keep") return; // handled by the change listener
    else return;
    render();
  });
  body.addEventListener("input", (e) => {
    if (e.target.id === "cut") {
      UI.cut.set(pairKey(), Number(e.target.value));
      $("cut-out").textContent = e.target.value;
      renderWorkspace();
    } else if (e.target.id === "ap-n") {
      UI.autoplayN = Number(e.target.value) || UI.autoplayN;
    }
  });
  body.addEventListener("change", (e) => {
    if (e.target.dataset.act === "keep") {
      UI.sel.set(e.target.dataset.key, e.target.checked);
      renderSelectionStatus();
    }
  });
  body.addEventListener("toggle", (e) => { if (e.target.id === "ap-details") UI.autoplayOpen = e.target.open; }, true);

  $("side-action").addEventListener("click", () => {
    if (S.phase === "breeding" || S.phase === "selection") {
      S.stoppedManually = true;
      finish();
    } else {
      S.phase = "setup";
    }
    render();
  });
  $("play-again").addEventListener("click", () => {
    startGame(S.hidden, S.popSize, "", S.mode);
    if (S.found) MG.balloons();
    render();
  });
  $("new-game").addEventListener("click", () => { S.phase = "setup"; render(); });

  MG.theme.onChange(() => { if (S.phase === "finished") renderChart(); });
  window.addEventListener("beforeunload", (e) => { if (S.phase === "breeding" || S.phase === "selection") e.preventDefault(); });

  render();
})();
