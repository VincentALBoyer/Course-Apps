/* GA Word Game — page controller. Port of GA_WordGame_App/app.py: same
 * phases (setup → breeding ⇄ selection → finished), the same mutation dice
 * and stagnation rule, and messages.
 *
 * Two views while playing: ✋ Manual (the default, every operator by hand)
 * and 🤖 Auto. Auto mode runs generations with the operators chosen in the
 * sidebar settings pane, one sub-step at a time (Play, or Next step), on a
 * fixed board that updates in place. Finished runs of the same word are
 * kept so their curves can be compared. */
(function () {
  "use strict";
  const { $, esc, fmt0 } = MG;
  const G = GA.logic;

  const STAGNATION_THRESHOLD = 3; // generations without a new best before mutation gets aggressive
  const SPEED_MS = { slow: 1800, normal: 1000, fast: 400, instant: 120 }; // per sub-step (per generation for instant)
  const SPEED_LABELS = { slow: "Slow", normal: "Normal", fast: "Fast", instant: "Instant (no steps)" };
  const MAX_RUNS = 8; // one categorical color per run, never cycled
  const MAX_PLAY_GENERATIONS = 100;

  // Reference categorical palette (dataviz skill), light / dark steps.
  const RUN_COLORS = {
    light: ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"],
    dark: ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#0ca30c", "#9085e9", "#e66767"],
  };

  const PARENT_HELP = {
    random: "Every member has the same chance - fitness is ignored. No selection pressure: a baseline to compare against.",
    roulette: "Each member gets a slice of the wheel proportional to its fitness, then the wheel is spun. Fitter members are picked more often, but weaker ones still have a chance (fitness 0 gets almost no slice).",
    tournament: "Draw k members at random; the fittest of them wins. A bigger k means stronger pressure toward the best; k = 2 is gentle.",
  };
  const SURVIVOR_HELP = {
    best: "Parents and offspring compete together and the N fittest survive (offspring win ties). The best word is never lost, but diversity can collapse quickly.",
    offspring: "All N offspring replace the parents (generational GA). Nothing is protected, so the best word can be lost.",
    elitism: "The k best parents survive automatically (the elite); the other N - k places go to the best offspring.",
  };

  const CONCEPTS = [
    ["Gene, Chromosome & Fitness", "A <strong>gene</strong> is one letter; a <strong>chromosome</strong> is a full candidate word. <strong>Fitness</strong> scores how close a candidate is to the hidden word - the population only learns from that single number each round, never the letters themselves."],
    ["Scoring: Exact vs. Partial Credit", "<strong>Exact match</strong> only rewards letters in the exact right spot, so a word with every letter right but shifted by one position scores 0 - a harsh, deceptive fitness landscape. <strong>Partial credit</strong> also rewards wrong letters that are merely close alphabetically, giving the GA a smoother slope to climb instead of scattered cliffs. This is a real lesson in GA design: how you score a solution shapes how easily evolution can find it."],
    ["Selection: Choosing Parents", "Selection decides which individuals get to reproduce. <strong>Roulette wheel</strong>: the chance of being picked is proportional to fitness. <strong>Tournament</strong>: draw k members at random and keep the fittest - only the ranking matters, not how big the fitness gaps are. <strong>Random</strong>: no pressure at all. Always picking the two fittest narrows the gene pool fast; occasionally breeding a weaker individual keeps letters in play that might matter later."],
    ["Crossover", "Single-point crossover cuts both parents at the same position and swaps tails, so each child blends letters from both parents. Where you cut controls how much of each parent survives into the children."],
    ["Mutation", "Mutation randomly replaces a gene (letter) in a child. It's the GA's only source of brand-new genetic material - without it, the population can only ever recombine letters already present in the initial population. A rate of 1/L means about one mutated letter per child; higher rates explore further from the parents but also destroy more of what crossover just built."],
    ["Survivor Selection & Elitism", "After breeding, you choose who survives into the next generation. <strong>Best of all</strong> keeps the fittest of parents + offspring: progress is locked in but diversity can be lost. <strong>Offspring only</strong> replaces every parent: more exploration, but the best word can disappear. <strong>Elitism (k)</strong> is in between: the k best parents always survive."],
    ["Why does population size matter?", "A larger population explores more of the search space per generation (more diversity) but costs more fitness evaluations per round - the same quality-vs-cost trade-off you saw with search strategies."],
  ];
  $("concepts").innerHTML = CONCEPTS.map(([t, b]) => `<details><summary>${esc(t)}</summary><p>${b}</p></details>`).join("");

  // ── state ────────────────────────────────────────────────────────────
  const S = {
    phase: "setup", gameId: 0, hidden: "", L: 6, popSize: 6, mode: "exact", code: "", rng: null,
    population: [], roundIdx: 0, offspring: [], history: [], totalEvals: 0,
    found: false, winningWord: null, foundGen: null, stoppedManually: false,
    startTime: null, endTime: null, bestWord: null, bestFit: null, bestImprovedGen: 0,
    runs: [], runNo: 0, runsKey: null,
  };
  // Per-pair UI choices, keyed like the Streamlit widget keys so they reset
  // per game / generation / pair (and come back after "Undo last pair").
  const UI = { view: "manual", order: new Map(), cut: new Map(), mut: new Map(), sel: new Map(), playN: 5 };
  // Auto-mode operator settings (kept across games). pMut is a percentage;
  // null means the default 1/L for the current word.
  const AUTO = { parent: "roulette", tourK: 2, survivor: "best", eliteK: 1, pMut: null, speed: "normal" };
  // Auto-mode runner: the generation in progress, its remaining sub-steps,
  // and what the board currently shows.
  const AR = { gen: null, steps: [], i: 0, playing: false, timer: null, done: 0, target: 5, board: null, stage: null, sub: "", explain: "" };

  const score = (w) => G.computeFitness(w, S.hidden, S.mode);
  const fmtScore = (v) => (S.mode === "partial" ? v.toFixed(2) : String(MG.pyRound(v)));
  const MANUAL = "Manual";
  const mName = (i) => `M${i + 1}`;

  const clampInt = (v, lo, hi, dflt) => {
    const n = Math.trunc(Number(v));
    return Number.isFinite(n) ? Math.max(lo, Math.min(hi, n)) : dflt;
  };
  const maxK = () => S.popSize - 1;
  const mutPct = () => (AUTO.pMut === null ? Math.round(100 / S.L) : AUTO.pMut);

  /** Short name of auto settings, used in the history and run comparison. */
  function autoLabel(c = AUTO) {
    const p = G.PARENT_METHODS[c.parent] + (c.parent === "tournament" ? ` k=${c.tourK}` : "");
    const s = G.SURVIVOR_RULES[c.survivor] + (c.survivor === "elitism" ? ` k=${c.eliteK}` : "");
    return `${p} · ${s} · mutation ${c.pct}%`;
  }

  function updateBest(word) {
    const f = score(word);
    if (S.bestFit === null || f > S.bestFit) {
      S.bestWord = word;
      S.bestFit = f;
      S.bestImprovedGen = S.roundIdx;
    }
  }

  /** "Manual (3 gen) → Roulette … (12 gen)" from the history's `by` column. */
  function runLabel(history) {
    const segs = [];
    for (const r of history.slice(1)) {
      const last = segs[segs.length - 1];
      if (last && last.by === r.by) last.n++;
      else segs.push({ by: r.by, n: 1 });
    }
    return segs.length ? segs.map((s) => `${s.by} (${s.n} gen)`).join(" → ") : "Found in the starting population";
  }

  function recordRun() {
    if (S.runs.length >= MAX_RUNS) S.runs.shift();
    const used = new Set(S.runs.map((r) => r.slot));
    let slot = 0;
    while (used.has(slot)) slot++; // a run keeps its color for as long as it's listed
    S.runNo += 1;
    S.runs.push({
      no: S.runNo, slot, label: runLabel(S.history), history: S.history.slice(), found: S.found,
      gens: S.found ? S.foundGen : S.roundIdx, bestFit: S.bestFit, evals: S.totalEvals,
    });
  }

  function finish() {
    arReset();
    S.phase = "finished";
    S.endTime = Date.now();
    recordRun();
  }

  function startGame(word, popSize, code, mode) {
    arReset();
    const runsKey = `${word}|${mode}`;
    if (runsKey !== S.runsKey) Object.assign(S, { runs: [], runNo: 0, runsKey }); // only compare runs of the same word & scoring
    const rng = G.makeRng(code);
    const L = G.chars(word).length;
    const population = G.randomPopulation(popSize, L, rng);
    population.sort((a, b) => G.computeFitness(b, word, mode) - G.computeFitness(a, word, mode));
    const stats = G.populationStats(population, word, mode);
    Object.assign(S, {
      gameId: S.gameId + 1, hidden: word, L, popSize, mode, code, rng, population,
      roundIdx: 0, offspring: [], history: [{ generation: 0, best: stats.best, avg: stats.avg, by: "Start" }],
      totalEvals: popSize, found: false, winningWord: null, foundGen: null, stoppedManually: false,
      startTime: Date.now(), endTime: null, phase: "breeding", bestWord: null, bestFit: null, bestImprovedGen: 0,
    });
    AUTO.tourK = clampInt(AUTO.tourK, 2, maxK(), 2);
    AUTO.eliteK = clampInt(AUTO.eliteK, 1, maxK(), 1);
    population.forEach(updateBest);
    const winner = population.find((w) => score(w) === L);
    if (winner) {
      Object.assign(S, { found: true, winningWord: winner, foundGen: 0 });
      finish();
    }
  }

  const isStagnant = () => S.roundIdx - S.bestImprovedGen >= STAGNATION_THRESHOLD;
  const pairKey = () => `${S.gameId}_${S.roundIdx}_${Math.floor(S.offspring.length / 2)}`;

  // ── manual play ──────────────────────────────────────────────────────
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
      // Same basis as every other row: the popSize best of population + offspring
      // (what elitist survivor selection would keep), not just the partial pool.
      const fits = S.population.map(score).concat(S.offspring.map((o) => o.fitness))
        .sort((x, y) => y - x).slice(0, S.popSize);
      S.history.push({ generation: gen, best: Math.max(...fits), avg: MG.pySum(fits) / fits.length, by: MANUAL });
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
    const keep = G.selectSurvivors(S.population.map(score), S.offspring.map((o) => o.fitness), "best", 0, S.popSize);
    S.population.forEach((_, i) => UI.sel.set(selKey("p", i), keep.p.has(i)));
    S.offspring.forEach((_, i) => UI.sel.set(selKey("o", i), keep.o.has(i)));
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
    S.history.push({ generation: gen, best: Math.max(...fits), avg: MG.pySum(fits) / fits.length, by: MANUAL });
    S.population = words.slice().sort((a, b) => score(b) - score(a));
    S.roundIdx = gen;
    S.offspring = [];
    S.phase = "breeding";
  }

  // ── auto mode runner ─────────────────────────────────────────────────
  // A generation is computed up front (G.autoRunGeneration), then revealed
  // as sub-steps: for each pair pick A, pick B, make the children; then
  // survivor selection; then the new population.
  const STAGES = ["Parent selection", "Crossover & mutation", "Survivor selection", "New population"];

  function freshBoard(words, fits) {
    return { words: words.slice(), fits: fits.slice(), roles: words.map(() => []), kids: Array(S.popSize).fill(null), keepP: null, keepO: null, hl: { p: new Set(), o: new Set() } };
  }

  function arIntro() {
    AR.board = freshBoard(S.population, S.population.map(score));
    AR.stage = null;
    AR.sub = "";
    AR.explain = `<div class="ex-title">How auto mode works</div>
      <p>Each generation runs in four steps: <strong>1</strong> choose parents pair by pair, <strong>2</strong> crossover & mutation,
      <strong>3</strong> survivor selection, <strong>4</strong> the survivors become the new population.</p>
      <p class="caption">Press <strong>⏭ Next step</strong> to advance one step at a time (good for explaining), or <strong>▶ Play</strong> to run
      at the chosen speed. The operators are set in the <strong>Auto mode settings</strong> pane.</p>`;
  }

  function arReset() {
    clearTimeout(AR.timer);
    Object.assign(AR, { gen: null, steps: [], i: 0, playing: false, timer: null, done: 0, board: null });
  }

  function arStartGen() {
    const genNo = S.roundIdx + 1;
    const pct = mutPct();
    const p = pct / 100;
    const cfg = { parent: AUTO.parent, tourK: AUTO.tourK, survivor: AUTO.survivor, eliteK: AUTO.eliteK, pct };
    const parents = S.population.slice();
    const r = G.autoRunGeneration(parents, S.hidden, S.popSize, S.mode, S.rng, { ...cfg, pMut: p });
    AR.gen = { r, parents, genNo, p, cfg, label: autoLabel(cfg) };
    AR.board = freshBoard(parents, r.fits);
    AR.steps = [];
    r.pairs.forEach((_, k) => AR.steps.push({ t: "pick", k }, { t: "kids", k }));
    AR.steps.push({ t: "survivors" }, { t: "next" });
    AR.i = 0;
  }

  const kidLabel = (i) => `C${i + 1}`;
  const listNames = (xs) => (xs.length ? xs.join(", ") : "none");

  function arApply(st) {
    const g = AR.gen;
    const r = g.r;
    const B = AR.board;
    const c = g.cfg;
    B.hl = { p: new Set(), o: new Set() };
    const nPairs = r.pairs.length;

    if (st.t === "pick") {
      // Both parents of the pair in one frame: A first, then B (drawn without A).
      const pr = r.pairs[st.k];
      B.roles[pr.a.index].push(`A${st.k + 1}`);
      B.roles[pr.b.index].push(`B${st.k + 1}`);
      B.hl.p.add(pr.a.index).add(pr.b.index);
      AR.stage = 0;
      AR.sub = `Pair ${st.k + 1} of ${nPairs}`;
      const method = G.PARENT_METHODS[c.parent] + (c.parent === "tournament" ? ` (k = ${c.tourK})` : "");
      AR.explain = `<div class="ex-title">Pair ${st.k + 1}: choosing Parents A and B - ${esc(method)}</div>
        <p class="caption">${esc(PARENT_HELP[c.parent])}</p>
        ${pickHtml(pr.a, "Parent A", r.fits)}${pickHtml(pr.b, "Parent B", r.fits, pr.a.index)}`;
    } else if (st.t === "kids") {
      const pr = r.pairs[st.k];
      const pa = g.parents[pr.a.index];
      const pb = g.parents[pr.b.index];
      const kids = [0, 1].map((j) => 2 * st.k + j);
      for (const i of kids) {
        const o = r.offspring[i];
        B.kids[i] = { ...o, cut: pr.cut };
        B.hl.o.add(i);
        updateBest(o.word);
        S.totalEvals += 1;
      }
      B.hl.p.add(pr.a.index).add(pr.b.index);
      AR.stage = 1;
      AR.sub = `Pair ${st.k + 1} of ${nPairs}`;
      const mutNote = kids.map((i) => {
        const pos = [...r.offspring[i].mutated].sort((x, y) => x - y).map((x) => x + 1);
        return `${kidLabel(i)}: ${pos.length ? "letter " + pos.join(", ") : "none"}`;
      }).join(" · ");
      const line = (lab, word, kid) => `<div class="ex-x"><span>${lab}</span>${tiles(word, { cut: pr.cut, size: 24 })}<span class="ex-arrow">→ <strong>${kidLabel(kid)}</strong></span>${tiles(r.offspring[kid].word, { cut: pr.cut, mutated: r.offspring[kid].mutated, size: 24 })}<span class="fit">${fmtScore(r.offspring[kid].fitness)}/${S.L}</span></div>`;
      const winner = kids.find((i) => r.offspring[i].fitness === S.L);
      AR.explain = `<div class="ex-title">Pair ${st.k + 1}: crossover after letter ${pr.cut}, then mutation (${Math.round(g.p * 100)}% per letter)</div>
        ${line(`A · ${mName(pr.a.index)}`, pa, kids[0])}${line(`B · ${mName(pr.b.index)}`, pb, kids[1])}
        <p class="caption">${kidLabel(kids[0])} = A's first ${pr.cut} letters + B's rest; ${kidLabel(kids[1])} = the opposite. Mutated (orange): ${mutNote}.</p>
        ${winner !== undefined ? `<div class="alert success">🎉 ${kidLabel(winner)} is the hidden word! Next step shows the results.</div>` : ""}`;
      if (winner !== undefined) AR.steps = AR.steps.slice(0, AR.i).concat([{ t: "found" }]);
    } else if (st.t === "survivors") {
      B.keepP = r.keep.p;
      B.keepO = r.keep.o;
      AR.stage = 2;
      AR.sub = "";
      const kept = [...g.parents.keys()].filter((i) => r.keep.p.has(i)).map(mName).concat([...r.offspring.keys()].filter((i) => r.keep.o.has(i)).map(kidLabel));
      const gone = [...g.parents.keys()].filter((i) => !r.keep.p.has(i)).map(mName).concat([...r.offspring.keys()].filter((i) => !r.keep.o.has(i)).map(kidLabel));
      const rule = G.SURVIVOR_RULES[c.survivor] + (c.survivor === "elitism" ? ` (k = ${c.eliteK})` : "");
      AR.explain = `<div class="ex-title">Survivor selection - ${esc(rule)}</div>
        <p class="caption">${esc(SURVIVOR_HELP[c.survivor])}</p>
        <p>✓ Survive (${kept.length}): <strong>${listNames(kept)}</strong></p><p>✗ Removed: ${listNames(gone)}</p>`;
    } else if (st.t === "next" || st.t === "found") {
      const fits = r.population.map(score);
      S.history.push({ generation: g.genNo, best: Math.max(...fits), avg: MG.pySum(fits) / fits.length, by: g.label });
      S.population = r.population;
      S.roundIdx = g.genNo;
      S.offspring = [];
      AR.gen = null;
      AR.done += 1;
      if (st.t === "found") {
        const win = r.offspring.find((o) => o.fitness === S.L);
        Object.assign(S, { found: true, winningWord: win.word, foundGen: g.genNo });
        finish();
        render();
        window.scrollTo({ top: 0 });
        MG.balloons();
        return;
      }
      AR.board = freshBoard(S.population, fits);
      AR.stage = 3;
      AR.sub = "";
      AR.explain = `<div class="ex-title">Generation ${g.genNo} complete</div>
        <p>The survivors, sorted by fitness, are the population of generation ${g.genNo + 1}:
        best fitness <strong>${fmtScore(Math.max(...fits))}/${S.L}</strong>, average <strong>${(MG.pySum(fits) / fits.length).toFixed(2)}</strong>.</p>
        <p class="caption">The chart below adds one point per generation.</p>`;
      arChart();
    }
  }

  /** Advance one sub-step (starting a new generation when needed). */
  function arStep() {
    if (S.phase !== "breeding") return;
    if (!AR.gen) arStartGen();
    arApply(AR.steps[AR.i++]);
  }

  function arTick() {
    AR.timer = null;
    if (!AR.playing || S.phase !== "breeding") return;
    if (!AR.gen && AR.done >= AR.target) {
      AR.playing = false;
      arPaint();
      return;
    }
    if (AUTO.speed === "instant") {
      arStep();
      while (AR.gen && S.phase === "breeding") arStep();
    } else arStep();
    if (S.phase !== "breeding") return;
    arPaint();
    AR.timer = setTimeout(arTick, SPEED_MS[AUTO.speed] || SPEED_MS.normal);
  }

  function arPlay() {
    AR.playing = true;
    AR.done = 0;
    AR.target = UI.playN;
    arTick();
  }

  function arPause() {
    AR.playing = false;
    clearTimeout(AR.timer);
    AR.timer = null;
  }

  /** One parent pick, drawn so students can see why that member won. */
  function pickHtml(pick, who, fits, excluded) {
    const res = `<span class="pick-res">→ <strong>${mName(pick.index)}</strong></span>`;
    const head = `<span class="pick-who">${who}</span>`;
    const note = excluded !== undefined ? ` (${mName(excluded)} left out - already Parent A)` : "";
    if (pick.method === "roulette") {
      const segs = pick.shares.map(({ i, p }) =>
        `<span class="seg${i === pick.index ? " on" : ""}" style="flex-grow:${p}" title="${mName(i)}: ${(p * 100).toFixed(0)}%">${p >= 0.09 ? mName(i) : ""}</span>`).join("");
      const shares = pick.shares.map(({ i, p }) => `${mName(i)} ${(p * 100).toFixed(0)}%`).join(" · ");
      return `<div class="pick">${head}<div class="wheel" role="img" aria-label="Roulette wheel, stopped on ${mName(pick.index)}">${segs}<span class="spin" style="left:${(pick.spin * 100).toFixed(1)}%"></span></div>${res}</div>
        <p class="caption pick-note">Slices: ${shares}${note}</p>`;
    }
    if (pick.method === "tournament") {
      const cs = pick.contestants.map((c) => `<span class="contestant${c === pick.index ? " on" : ""}">${mName(c)} <small>${fmtScore(fits[c])}</small></span>`).join("");
      return `<div class="pick">${head}<span>🥊 ${cs}</span>${res}</div>
        <p class="caption pick-note">${pick.contestants.length} contestants drawn at random; the fittest wins${note}.</p>`;
    }
    return `<div class="pick">${head}<span class="caption">🎲 Uniform draw among ${pick.pool.map(mName).join(", ")}</span>${res}</div>`;
  }

  // ── rendering helpers ────────────────────────────────────────────────
  function tiles(word, { cut = null, mutated = new Set(), size = 30, ghost = false } = {}) {
    const parts = [];
    Array.from(word).forEach((ch, i) => {
      parts.push(`<span class="tile${mutated.has(i) ? " mut" : ""}${ghost ? " ghost" : ""}">${esc(ch)}</span>`);
      if (cut !== null && i === cut - 1) parts.push(`<span class="tile-cut"></span>`);
    });
    return `<span class="tiles" style="--tile:${size}px">${parts.join("")}</span>`;
  }

  const fitText = (f) => `Fitness <strong>${fmtScore(f)}/${S.L}</strong>`;
  const memberRow = (label, word, f, opts) => `<div class="member"><span>${label}</span>${tiles(word, opts)}<span class="fit">${fitText(f)}</span></div>`;

  function viewTabs() {
    const autoLocked = S.phase === "selection" || S.offspring.length > 0;
    const manualLocked = !!AR.gen || AR.playing;
    const tab = (v, label, locked, why) => `<button type="button" role="tab" data-act="view" data-v="${v}" aria-selected="${UI.view === v}"${locked && UI.view !== v ? ` disabled title="${why}"` : ""}>${label}</button>`;
    return `<div class="modes view-tabs" role="tablist" aria-label="Play mode">
      ${tab("manual", "✋ Manual", manualLocked, "Pause and finish this generation (⏭ Next step) first")}${tab("auto", "🤖 Auto mode", autoLocked, "Finish (or undo) this generation's breeding first")}</div>`;
  }

  function renderBreeding(body) {
    const L = S.L;
    const pk = pairKey();
    const selected = UI.order.get(pk) || [];

    const left = [`<div class="list-title">Current Population</div><p class="caption">Click a member's M# to select it as a parent (first click = Parent A).</p>`];
    S.population.forEach((w, i) => {
      const role = selected[0] === i ? "A" : selected[1] === i ? "B" : "";
      left.push(`<div class="member"><button class="mbtn${role ? " on" : ""}" data-act="parent" data-i="${i}" aria-pressed="${!!role}">M${i + 1}${role ? ` · ${role}` : ""}</button>${tiles(w, { size: 26 })}<span class="fit">${fitText(score(w))}</span></div>`);
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

    body.innerHTML = viewTabs() + `<div class="ga-cols"><div>${left.join("")}</div><div>${right.join("")}</div></div>`;
    if (selected.length >= 2) renderWorkspace();
  }

  /** The part of the workspace that depends on the cut slider. */
  function renderWorkspace() {
    const L = S.L;
    const pk = pairKey();
    const [a, b] = UI.order.get(pk) || []; // click order: first click = Parent A
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
    body.innerHTML = viewTabs() + `
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

  // ── auto view ────────────────────────────────────────────────────────
  /** Built once per render; arPaint() then only updates the parts that change. */
  function renderAuto(body) {
    if (!AR.board) arIntro();
    const speedOpts = Object.entries(SPEED_LABELS).map(([v, l]) => `<option value="${v}"${v === AUTO.speed ? " selected" : ""}>${esc(l)}</option>`).join("");
    body.innerHTML = viewTabs() + `
      <div class="ar-controls">
        <button class="btn primary" id="ar-play" data-act="ar-play"></button>
        <button class="btn" id="ar-next" data-act="ar-next">⏭ Next step</button>
        <label class="ar-inline">Speed <select id="ar-speed">${speedOpts}</select></label>
        <label class="ar-inline">▶ Play runs <input type="number" id="ar-n" min="1" max="${MAX_PLAY_GENERATIONS}" step="1" value="${UI.playN}" /> generations</label>
      </div>
      <div class="ar-stepper" id="ar-stepper" aria-live="polite"></div>
      <div class="ar-explain" id="ar-explain"></div>
      <div id="ar-board"></div>
      <p class="caption ar-legend"><span class="role">A1</span> <span class="role">B1</span> picked as Parent A / B of pair 1 ·
        <span class="tile mut legend-tile">X</span> mutated letter · grey bar = crossover cut · ✓ survives, ✗ removed</p>
      <div class="list-title">Best and average fitness per generation</div>
      <div id="ar-chart" class="chart"></div>`;
    arPaint();
    arChart();
  }

  function boardHtml() {
    const B = AR.board;
    const L = S.L;
    const mark = (kept) => (kept === null ? "" : kept ? "✓" : "✗");
    const prow = (i) => {
      const kept = B.keepP ? B.keepP.has(i) : null;
      const roles = B.roles[i].map((x) => `<span class="role">${x}</span>`).join("");
      return `<div class="ar-row${B.hl.p.has(i) ? " hl" : ""}${kept === false ? " out" : ""}"><span class="ar-lab">${mName(i)}</span>${tiles(B.words[i], { size: 22 })}<span class="ar-fit">${fmtScore(B.fits[i])}</span><span class="ar-roles">${roles}</span><span class="ar-mark">${mark(kept)}</span></div>`;
    };
    const orow = (i) => {
      const o = B.kids[i];
      if (!o) return `<div class="ar-row empty"><span class="ar-lab">${kidLabel(i)}</span>${tiles(" ".repeat(L), { size: 22, ghost: true })}<span class="ar-fit">–</span><span class="ar-roles"></span><span class="ar-mark"></span></div>`;
      const kept = B.keepO ? B.keepO.has(i) : null;
      return `<div class="ar-row${B.hl.o.has(i) ? " hl" : ""}${kept === false ? " out" : ""}${o.fitness === L ? " win" : ""}"><span class="ar-lab">${kidLabel(i)}</span>${tiles(o.word, { size: 22, mutated: o.mutated, cut: o.cut })}<span class="ar-fit">${fmtScore(o.fitness)}</span><span class="ar-roles"></span><span class="ar-mark">${mark(kept)}</span></div>`;
    };
    const gen = AR.gen ? AR.gen.genNo : S.roundIdx + 1;
    return `<div class="ar-board" style="--L:${L}">
      <div><div class="list-title">Parents · generation ${gen} <span class="caption">(fitness / ${L})</span></div>${B.words.map((_, i) => prow(i)).join("")}</div>
      <div><div class="list-title">Offspring</div>${B.kids.map((_, i) => orow(i)).join("")}</div>
    </div>`;
  }

  function arPaint() {
    if (!$("ar-board")) return;
    const play = $("ar-play");
    play.textContent = AR.playing ? "⏸ Pause" : "▶ Play";
    const gen = AR.gen ? AR.gen.genNo : S.roundIdx + 1;
    const chips = STAGES.map((s, i) => `<span class="chip${AR.stage === i ? " on" : ""}">${i + 1} ${s}</span>`).join("");
    $("ar-stepper").innerHTML = `<span class="ar-gen">Generation ${gen}</span>${chips}${AR.sub ? `<span class="ar-sub">${esc(AR.sub)}</span>` : ""}`;
    $("ar-explain").innerHTML = AR.explain;
    $("ar-board").innerHTML = boardHtml();
    // things outside the stage that depend on the runner
    $("gen-title").textContent = `Generation ${gen} — Auto mode`;
    $("side-best").textContent = `${fmtScore(S.bestFit)} / ${S.L}`;
    $("side-action").disabled = AR.playing;
    const manualTab = document.querySelector('[data-act="view"][data-v="manual"]');
    if (manualTab) {
      manualTab.disabled = !!AR.gen || AR.playing;
      manualTab.title = manualTab.disabled ? "Pause and finish this generation (⏭ Next step) first" : "";
    }
  }

  function arChart() {
    const el = $("ar-chart");
    if (!el) return;
    const h = S.history;
    const gens = h.map((r) => r.generation);
    const L = S.L;
    MG.plot(el, [
      { type: "scatter", mode: "lines", x: gens, y: h.map((r) => r.avg), name: "Average", line: { color: "#eb6834", width: 2 }, hovertemplate: "Generation %{x}<br>Average: %{y:.2f}<extra></extra>" },
      { type: "scatter", mode: "lines+markers", x: gens, y: h.map((r) => r.best), name: "Best", line: { color: "#2a78d6", width: 2 }, marker: { size: 8, color: "#2a78d6" }, hovertemplate: `Generation %{x}<br>Best: %{y${S.mode === "partial" ? ":.2f" : ""}}<extra></extra>` },
    ], {
      height: 220, margin: { l: 40, r: 10, t: 10, b: 35 },
      legend: { orientation: "h", yanchor: "bottom", y: 1.02, x: 0 },
      xaxis: { zeroline: false, tickfont: { size: 10 }, range: [-0.3, Math.max(5, gens[gens.length - 1]) + 0.3], tickformat: "d", title: { text: "Generation" } },
      yaxis: { range: [-0.3, L + 0.6], dtick: 1, zeroline: false },
    }, { displayModeBar: false });
  }

  function renderAutoSettings() {
    const panel = $("auto-panel");
    const show = UI.view === "auto" && S.phase === "breeding";
    panel.hidden = !show;
    document.querySelector("main").classList.toggle("auto-view", show);
    if (!show) return;
    const pct = mutPct();
    const opts = (o, cur) => Object.entries(o).map(([v, l]) => `<option value="${v}"${v === cur ? " selected" : ""}>${esc(l)}</option>`).join("");
    const kField = (id, val, lo, label) => `<label class="field ap-k"><span>${label}</span>
      <input type="number" id="${id}" min="${lo}" max="${maxK()}" step="1" value="${val}" /></label>`;
    panel.innerHTML = `<h3>🤖 Auto mode settings</h3>
      <label class="field"><span>Parent selection</span><select id="ap-parent">${opts(G.PARENT_METHODS, AUTO.parent)}</select></label>
      ${AUTO.parent === "tournament" ? kField("ap-tourk", AUTO.tourK, 2, `Tournament size k (2-${maxK()})`) : ""}
      <label class="field"><span>Survivor selection</span><select id="ap-surv">${opts(G.SURVIVOR_RULES, AUTO.survivor)}</select></label>
      ${AUTO.survivor === "elitism" ? kField("ap-elitek", AUTO.eliteK, 1, `Elite size k (1-${maxK()})`) : ""}
      <label class="field"><span>Mutation per letter <output id="ap-mut-out">${pct}%${AUTO.pMut === null ? " (1/L)" : ""}</output></span>
        <input type="range" id="ap-mut" min="0" max="50" step="1" value="${pct}" /></label>
      <p class="caption">1/L = ${Math.round(100 / S.L)}% ≈ one mutated letter per child. Changes apply from the next generation.</p>`;
  }

  function rerenderSettingsKeepFocus(id) {
    renderAutoSettings();
    const el = $(id);
    if (el) el.focus();
  }

  // ── finished ─────────────────────────────────────────────────────────
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
      { key: "by", label: "Played by", text: true },
    ], S.history);
    renderCompare();
  }

  function renderChart() {
    const h = S.history;
    const gens = h.map((r) => r.generation);
    const L = S.L;
    MG.plot($("fitness-chart"), [
      { type: "scatter", mode: "lines", x: gens, y: gens.map(() => L), line: { color: "#c3c2b7", dash: "dash", width: 1.5 }, name: `Target (${L})`, hoverinfo: "skip" },
      { type: "scatter", mode: "lines+markers", x: gens, y: h.map((r) => r.avg), name: "Average fitness", line: { color: "#eb6834", width: 2 }, marker: { size: 7, color: "#eb6834" }, hovertemplate: "Generation %{x}<br>Average fitness: %{y:.2f}<extra></extra>" },
      { type: "scatter", mode: "lines+markers", x: gens, y: h.map((r) => r.best), name: "Best fitness", line: { color: "#2a78d6", width: 3 }, marker: { size: 9, color: "#2a78d6" }, hovertemplate: `Generation %{x}<br>Best fitness: %{y${S.mode === "partial" ? ":.2f" : ""}}<extra></extra>` },
    ], {
      height: 300, margin: { l: 50, r: 10, t: 10, b: 45 },
      legend: { orientation: "h", yanchor: "bottom", y: 1.02, x: 0 },
      xaxis: { title: { text: "Generation" }, zeroline: false, tickfont: { size: 10 } },
      yaxis: { title: { text: S.mode === "partial" ? "Fitness (partial credit)" : "Fitness (letters correct)" }, range: [-0.3, L + 0.6], dtick: 1, zeroline: false },
    }, { displayModeBar: false });
  }

  /** Best-fitness curves of every finished run of this word, one color per run. */
  function renderCompare() {
    const runs = S.runs;
    const many = runs.length >= 2;
    $("compare-hint").hidden = many;
    $("compare-body").hidden = !many;
    if (!many) return;
    const L = S.L;
    const colors = RUN_COLORS[MG.theme.current() === "dark" ? "dark" : "light"];
    const fmtBest = S.mode === "partial" ? ":.2f" : "";
    const maxGen = Math.max(1, ...runs.map((r) => r.history[r.history.length - 1].generation));
    MG.plot($("compare-chart"), [
      { type: "scatter", mode: "lines", x: [0, maxGen], y: [L, L], line: { color: "#c3c2b7", dash: "dash", width: 1.5 }, name: `Target (${L})`, hoverinfo: "skip" },
      ...runs.map((r) => ({
        type: "scatter", mode: "lines+markers", name: `Run ${r.no}`,
        x: r.history.map((h) => h.generation), y: r.history.map((h) => h.best),
        line: { color: colors[r.slot], width: 2 }, marker: { size: 8, color: colors[r.slot] },
        hovertemplate: `Run ${r.no}<br>Generation %{x}<br>Best fitness: %{y${fmtBest}}<extra></extra>`,
      })),
    ], {
      height: 320, margin: { l: 50, r: 10, t: 10, b: 45 },
      legend: { orientation: "h", yanchor: "bottom", y: 1.02, x: 0 },
      xaxis: { title: { text: "Generation" }, zeroline: false, tickfont: { size: 10 } },
      yaxis: { title: { text: "Best fitness" }, range: [-0.3, L + 0.6], dtick: 1, zeroline: false },
    }, { displayModeBar: false });
    const rows = runs.map((r) => `<tr>
      <td class="text"><span class="swatch" style="background:${colors[r.slot]}"></span>Run ${r.no}</td>
      <td class="text wrap">${esc(r.label)}</td>
      <td>${r.found ? "✓ found" : "✗ stopped"}</td>
      <td>${r.gens}</td><td>${fmtScore(r.bestFit)} / ${L}</td><td>${r.evals}</td></tr>`).join("");
    $("compare-table").innerHTML = `<thead><tr><th class="text">Run</th><th class="text">How it was played</th><th>Result</th><th>Generations</th><th>Best fitness</th><th>Evaluations</th></tr></thead><tbody>${rows}</tbody>`;
  }

  function updateElapsed() {
    if ((S.phase === "breeding" || S.phase === "selection") && S.startTime) $("m-elapsed").textContent = fmt0((Date.now() - S.startTime) / 1000) + "s";
  }
  setInterval(updateElapsed, 1000);

  function render() {
    const playing = S.phase === "breeding" || S.phase === "selection";
    if (S.phase === "selection") UI.view = "manual";
    $("phase-setup").hidden = S.phase !== "setup";
    $("phase-play").hidden = !playing;
    $("phase-finished").hidden = S.phase !== "finished";

    $("status-panel").hidden = S.phase === "setup";
    if (S.phase !== "setup") {
      $("side-best").textContent = `${fmtScore(S.bestFit)} / ${S.L}`;
      $("side-action").textContent = playing ? "⏹ Stop Game" : "↺ New Game";
      $("side-action").disabled = AR.playing;
    }
    renderAutoSettings();

    if (playing) {
      const label = S.phase === "breeding" ? "Breeding offspring" : "Selecting survivors";
      $("gen-title").textContent = `Generation ${S.roundIdx + 1} — ${label}`;
      $("gen-scoring").textContent = `Scoring: ${G.SCORING_LABELS[S.mode]}`;
      $("m-pop").textContent = String(S.popSize);
      $("m-target").textContent = String(S.L);
      updateElapsed();
      const body = $("play-body");
      if (S.phase === "breeding" && UI.view === "auto") renderAuto(body);
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
    UI.view = "manual"; // a new game always starts fully manual
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
    if (!el || el.disabled) return;
    const act = el.dataset.act;
    const pk = pairKey();
    if (act === "view") {
      UI.view = el.dataset.v;
      if (UI.view === "auto") arIntro();
      render();
      return;
    }
    if (act === "ar-play") {
      if (AR.playing) { arPause(); arPaint(); } else arPlay();
      return;
    }
    if (act === "ar-next") {
      arPause();
      arStep();
      if (S.phase === "breeding") arPaint();
      return;
    }
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
      const [a, b] = UI.order.get(pk) || [];
      const cut = UI.cut.has(pk) ? UI.cut.get(pk) : Math.floor(S.L / 2);
      commitPair(a, b, cut, UI.mut.get(`${pk}_${a}_${b}_1`) || [], UI.mut.get(`${pk}_${a}_${b}_2`) || []);
      if (S.found) MG.balloons();
    } else if (act === "auto-select") { autoSelectBest(); }
    else if (act === "clear-select") { clearSelection(); }
    else if (act === "confirm") { confirmSelection(chosenWords()); }
    else if (act === "keep") return; // handled by the change listener
    else return;
    render();
  });
  body.addEventListener("input", (e) => {
    const t = e.target;
    if (t.id === "cut") {
      UI.cut.set(pairKey(), Number(t.value));
      $("cut-out").textContent = t.value;
      renderWorkspace();
    } else if (t.id === "ar-n") {
      UI.playN = clampInt(t.value, 1, MAX_PLAY_GENERATIONS, UI.playN);
      if (AR.playing) AR.target = UI.playN;
    }
  });
  body.addEventListener("change", (e) => {
    const t = e.target;
    if (t.dataset.act === "keep") {
      UI.sel.set(t.dataset.key, t.checked);
      renderSelectionStatus();
    } else if (t.id === "ar-speed") {
      AUTO.speed = t.value;
    } else if (t.id === "ar-n") {
      t.value = UI.playN;
    }
  });

  const panel = $("auto-panel");
  panel.addEventListener("input", (e) => {
    if (e.target.id === "ap-mut") {
      AUTO.pMut = Number(e.target.value);
      $("ap-mut-out").textContent = `${AUTO.pMut}%`;
    }
  });
  panel.addEventListener("change", (e) => {
    const t = e.target;
    if (t.id === "ap-parent") { AUTO.parent = t.value; rerenderSettingsKeepFocus("ap-parent"); }
    else if (t.id === "ap-surv") { AUTO.survivor = t.value; rerenderSettingsKeepFocus("ap-surv"); }
    else if (t.id === "ap-tourk") { AUTO.tourK = clampInt(t.value, 2, maxK(), AUTO.tourK); t.value = AUTO.tourK; }
    else if (t.id === "ap-elitek") { AUTO.eliteK = clampInt(t.value, 1, maxK(), AUTO.eliteK); t.value = AUTO.eliteK; }
  });

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
    startGame(S.hidden, S.popSize, S.code, S.mode); // same class code → same start population
    if (S.found) MG.balloons();
    render();
    window.scrollTo({ top: 0 });
  });
  $("new-game").addEventListener("click", () => { S.phase = "setup"; render(); });
  $("clear-runs").addEventListener("click", () => {
    S.runs = S.runs.slice(-1);
    renderCompare();
  });

  MG.theme.onChange(() => {
    if (S.phase === "finished") { renderChart(); renderCompare(); }
    else if (UI.view === "auto") arChart();
  });
  window.addEventListener("beforeunload", (e) => { if (S.phase === "breeding" || S.phase === "selection") e.preventDefault(); });

  render();
})();
