/* Ant Colony: The Pheromone Trail — page controller. Logic lives in logic.js. */
(function () {
  "use strict";
  const { $, esc } = MG;
  const A = MG.ACO;

  const DEFAULTS = { alpha: 1, beta: 2, rho: 0.5, elitist: false };
  const SPEEDS = {
    // pause before a choice (ms), ms per map unit walked, pause between auto-play iterations
    1: { think: 1100, walk: 30, iter: 900, name: "Slow" },
    2: { think: 650, walk: 16, iter: 500, name: "Calm" },
    3: { think: 350, walk: 8, iter: 250, name: "Normal" },
    4: { think: 150, walk: 3, iter: 90, name: "Fast" },
    5: { think: 40, walk: 1, iter: 15, name: "Turbo" },
  };
  const STAGNATION_STOP = 8; // Play stops after this many iterations where every ant built the same tour
  const PLAY_MAX = 500; // ...or after this many iterations in one go
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

  const PRESETS = [
    { name: "Classic", p: { alpha: 1, beta: 2, rho: 0.5, elitist: false },
      what: "The textbook Ant System. Pheromone and distance both count." },
    { name: "Pheromone only", p: { alpha: 1, beta: 0, rho: 0.5, elitist: false },
      what: "β = 0: ants ignore distance. Early tours are pure luck, so it learns slowly." },
    { name: "Distance only", p: { alpha: 0, beta: 2, rho: 0.5, elitist: false },
      what: "α = 0: no memory at all. A randomized greedy that never improves over the iterations." },
    { name: "Goldfish memory", p: { alpha: 1, beta: 2, rho: 1, elitist: false },
      what: "ρ = 1: everything evaporates. The colony only remembers the last iteration." },
    { name: "Elephant memory", p: { alpha: 1, beta: 2, rho: 0.05, elitist: false },
      what: "ρ = 0.05: trails fade very slowly, so early (bad) tours keep influencing choices." },
    { name: "Herd instinct", p: { alpha: 4, beta: 2, rho: 0.5, elitist: true },
      what: "High α plus an elitist ant: very fast convergence, sometimes stuck on a so-so tour (stagnation)." },
  ];

  const CONCEPTS = [
    ["Traveling salesman problem", "Visit every city exactly once and return to the start, with the shortest total distance. The number of tours, (n − 1)! / 2, explodes: 26 cities already give about 7.8 × 10<sup>24</sup> tours."],
    ["Stigmergy", "Real ants don't talk to each other: they communicate <b>through the environment</b> by laying pheromone. Ants on a short path come back sooner, so that path collects pheromone faster and attracts more ants."],
    ["Pheromone τ", "A number on every edge, the colony's <b>shared memory</b>. It starts at 1 everywhere. On the map, thicker and darker orange edges have more pheromone."],
    ["Visibility η = 1 / d", "Local, greedy information: a closer city is more attractive. It never changes during the run."],
    ["Choice rule", "From city i, an ant goes to an unvisited city j with probability<br><b>P = τ<sub>ij</sub><sup>α</sup> · η<sub>ij</sub><sup>β</sup> / Σ</b><br>where Σ adds the same product over all unvisited cities. The ant spins a roulette wheel with those probabilities, so even an unlikely city is sometimes chosen."],
    ["α and β", "<b>α</b> = how much ants follow pheromone (exploitation of what the colony learned). <b>β</b> = how much they prefer close cities (greedy heuristic). α = 0 gives a randomized greedy; β = 0 gives a colony that must learn everything from scratch."],
    ["Evaporation ρ", "After each iteration, every edge keeps only (1 − ρ) of its pheromone. Evaporation lets the colony <b>forget</b> bad early choices. Too little and it locks in early; too much and it can't remember anything. τ never drops below 0.001, so no edge becomes impossible."],
    ["Deposit Q / L", "After evaporation, every ant of the iteration adds Q / L on each edge of its tour (L = its tour length). Shorter tour, more pheromone. Here Q = the greedy tour's length, so an ant as good as greedy deposits exactly 1."],
    ["Iteration", "One iteration = every ant builds a full tour using the <b>same</b> pheromone, then pheromone is updated once. Ants within an iteration don't influence each other."],
    ["Elitist ant", "An extra boost: the best tour found so far also deposits each iteration, as much as n extra ants (n = number of cities). Converges faster, but explores less."],
    ["Stagnation", "When one trail has almost all the pheromone, every ant builds the same tour and the search stops exploring. Watch the average line on the chart drop onto the best line: if that tour isn't optimal, the colony is stuck. Play stops by itself when this lasts " + STAGNATION_STOP + " iterations."],
    ["Metaheuristic", "ACO doesn't guarantee the optimum, but it finds very good tours after checking a tiny fraction of all possible tours. It has been applied to routing, scheduling and network problems."],
  ];

  // An ant drawn facing +x, centered on (0, 0).
  const ANT_SVG = `<g id="ant" class="ant"><g class="ant-body">
    <path class="ant-legs" d="M-1.3 0 L-2.4 -1.9 M-1.3 0 L-2.4 1.9 M0 0 L0.1 -2.1 M0 0 L0.1 2.1 M1 0 L2.1 -1.7 M1 0 L2.1 1.7"/>
    <path class="ant-antenna" d="M1.8 -0.3 Q2.5 -1.3 3.2 -1.1 M1.8 0.3 Q2.5 1.3 3.2 1.1"/>
    <ellipse cx="-1.9" cy="0" rx="1.35" ry="0.95"/><ellipse cx="0" cy="0" rx="0.75" ry="0.55"/><circle cx="1.35" cy="0" r="0.68"/>
  </g></g>`;

  let S = null;
  let token = 0; // bumped on reset/new game so running animations stop

  const fmt = (x) => (x == null ? "—" : x.toFixed(1));
  const fmtW = (x) => (x === 0 ? "0" : x >= 1e-4 && x < 1e5 ? String(Number(x.toPrecision(3))) : x.toExponential(2));
  const pct = (p) => (p >= 0.995 ? Math.round(p * 100) : (p * 100).toFixed(1)) + "%";
  const label = (i) => S.cities[i].label;
  const tourLabel = (t) => t.map(label).join(" → ") + " → " + label(t[0]);
  const speed = () => SPEEDS[S.speed];
  const angle = (a, b) => (Math.atan2(S.cities[b].y - S.cities[a].y, S.cities[b].x - S.cities[a].x) * 180) / Math.PI;

  // ── setup ─────────────────────────────────────────────────────────────
  $("concepts").innerHTML = CONCEPTS.map(([t, b]) => `<details><summary>${esc(t)}</summary><p>${b}</p></details>`).join("");
  $("presets").innerHTML = PRESETS.map((p, k) => `<button class="ac-preset" data-k="${k}" type="button">
      <strong>${esc(p.name)}</strong><span class="ac-preset-p">α ${p.p.alpha} · β ${p.p.beta} · ρ ${p.p.rho}${p.p.elitist ? " · ⭐ elitist" : ""}</span>
      <span>${esc(p.what)}</span></button>`).join("");

  $("start").addEventListener("click", () => {
    const level = A.LEVELS[document.querySelector('input[name="difficulty"]:checked').value];
    const code = ($("code").value.trim() || MG.newGameCode()).toUpperCase();
    startGame(level, code);
  });
  $("code").addEventListener("keydown", (e) => { if (e.key === "Enter") $("start").click(); });

  function startGame(level, code) {
    token++;
    const seed = MG.codeToSeed(code);
    const cities = A.makeCities(new MG.PyRandom(seed), level.n, level.minGap);
    const D = A.distances(cities);
    S = {
      level, code, seed, cities, D, n: cities.length,
      greedy: A.nearestNeighbor(D, 0),
      opt: A.heldKarp(D),
      params: { ...DEFAULTS, m: level.ants },
      // Keep the chips' current state across games (optimal tour always starts hidden).
      show: { pher: $("show-pher").checked, ants: $("show-ants").checked, best: $("show-best").checked, opt: false },
      edgeView: document.querySelector('input[name="edge-view"]:checked').value,
      viewHinted: false,
      speed: Number($("speed").value),
      runs: [],
      optCelebrated: false,
    };
    resetColony(false);
    $("phase-setup").hidden = true;
    $("phase-colony").hidden = false;
    $("main").classList.add("wide");
    $("colony-title").textContent = `${level.label} map · ${S.n} cities`;
    $("m-code").textContent = code;
    $("m-greedy").textContent = fmt(S.greedy.len);
    $("m-opt").textContent = S.opt ? fmt(S.opt.len) : "unknown";
    $("show-opt-wrap").hidden = !S.opt;
    $("show-opt").checked = false;
    buildMap();
    syncParamInputs();
    window.scrollTo({ top: 0 });
    renderAll();
    status(S.opt ? "Press 🐜 Watch next ant to see how one ant chooses its tour." : "26 cities: try ▶ Play, then compare with greedy.");
  }

  /** Pheromone back to τ0, ant RNG reseeded. The finished run is kept for the chart. */
  function resetColony(archive = true) {
    token++;
    if (archive && S.history && S.history.length) {
      const p = S.params;
      S.runs.push({
        name: `Run ${S.runs.length + 1}: α${p.alpha} β${p.beta} ρ${p.rho} m${p.m}${p.elitist ? " ⭐" : ""}`,
        y: S.history.map((h) => h.bestSoFar),
      });
      if (S.runs.length > 4) S.runs.shift();
    }
    Object.assign(S, {
      tau: A.initPheromone(S.n),
      rng: new MG.PyRandom(S.seed + 1n),
      iter: 0,
      pending: [],
      flash: [],
      flashId: 0,
      best: null,
      bestId: 0,
      yourBest: null,
      history: [],
      stagnant: 0,
      manual: null,
      watch: null,
      busy: false,
      playing: false,
    });
    if ($("ant")) $("L-ant").innerHTML = "";
  }

  function goSetup() {
    token++;
    if (S) { S.playing = false; S.busy = false; }
    $("phase-colony").hidden = true;
    $("phase-setup").hidden = false;
    $("main").classList.remove("wide");
    $("code").value = S ? S.code : "";
    window.scrollTo({ top: 0 });
  }

  // ── colony mechanics ──────────────────────────────────────────────────
  function addTour(tour, who) {
    const len = A.tourLength(tour, S.D);
    S.pending.push({ tour: tour.slice(), len, who });
    if (!S.best || len < S.best.len - 1e-9) {
      S.best = { tour: tour.slice(), len, who, iter: S.iter + 1 };
      S.bestId++;
      if (S.opt && len <= S.opt.len + 1e-9 && !S.optCelebrated && S.show.best) {
        S.optCelebrated = true;
        MG.toast(who === "you" ? "🎉 Your ant found the optimal tour!" : `🎉 The colony found the optimal tour in iteration ${S.iter + 1}!`);
        if (who === "you") MG.balloons();
      }
    }
    if (who === "you" && (!S.yourBest || len < S.yourBest.len)) S.yourBest = { tour: tour.slice(), len };
    if (S.pending.length >= S.params.m) endIteration();
    return len;
  }

  function endIteration() {
    const lens = S.pending.map((a) => a.len);
    const p = S.params;
    A.updatePheromone(S.tau, S.pending, p.rho, S.greedy.len, p.elitist ? S.best : null);
    S.iter++;
    const you = S.pending.find((a) => a.who === "you");
    const row = {
      iter: S.iter,
      best: Math.min(...lens),
      mean: lens.reduce((a, b) => a + b, 0) / lens.length,
      worst: Math.max(...lens),
      bestSoFar: S.best.len,
      ants: lens.length,
      you: you ? you.len : null,
    };
    S.history.push(row);
    S.stagnant = lens.length > 1 && row.worst - row.best < 1e-6 ? S.stagnant + 1 : 0;
    S.flash = S.pending.map((a) => a.tour);
    S.flashId++;
    S.pending = [];
    if (!S.playing) {
      status(`💨 Iteration ${S.iter} done: pheromone ×${(1 - p.rho).toFixed(2)} everywhere, then ${lens.length} ant${lens.length > 1 ? "s" : ""}${p.elitist ? " + the elitist ant" : ""} deposited Q / L.`);
    }
  }

  function antTour() {
    const p = S.params;
    return A.buildTour(S.rng, S.tau, S.D, p.alpha, p.beta);
  }

  function finishIteration() {
    const it = S.iter;
    while (S.iter === it) addTour(antTour(), "colony");
  }

  // ── animated ant ──────────────────────────────────────────────────────
  /** Sleep that ends early when the watched ant is skipped or the run reset. */
  async function wait(ms, my) {
    const end = performance.now() + ms;
    while (performance.now() < end) {
      if (my !== token || (S.watch && S.watch.skip)) return;
      await MG.sleep(Math.min(40, end - performance.now()));
    }
  }

  async function watchAnt() {
    if (S.busy || S.playing || S.manual) return;
    const my = token;
    S.busy = true;
    const n = S.n;
    const start = S.rng.randrange(n);
    const visited = new Uint8Array(n);
    visited[start] = 1;
    const tour = [start];
    S.watch = { tour, choice: null, chosen: null, k: S.pending.length + 1, skip: false };
    renderAll();
    placeAnt(start, null, false);
    while (tour.length < n) {
      const cur = tour[tour.length - 1];
      const p = S.params;
      const choice = A.choiceProbs(cur, visited, S.tau, S.D, p.alpha, p.beta);
      S.watch.choice = choice;
      S.watch.chosen = null;
      renderMap(); renderPanel();
      await wait(speed().think, my);
      if (my !== token) return;
      const j = A.roulette(S.rng, choice);
      S.watch.chosen = j;
      renderMap(); renderPanel();
      await wait(speed().think / 2, my);
      if (my !== token) return;
      await walk(cur, j, my);
      if (my !== token) return;
      tour.push(j);
      visited[j] = 1;
    }
    S.watch.choice = null;
    S.watch.chosen = null;
    renderMap(); renderPanel();
    await walk(tour[n - 1], start, my);
    if (my !== token) return;
    S.watch = null;
    S.busy = false;
    $("L-ant").innerHTML = "";
    const len = addTour(tour, "colony");
    if (S.pending.length) status(`🐜 Ant finished its tour: ${fmt(len)}. Its pheromone is laid when the iteration ends.`);
    renderAll();
  }

  /** Move the ant along one edge (direct DOM updates, no re-render). */
  function walk(a, b, my) {
    const from = S.cities[a];
    const to = S.cities[b];
    const instant = reducedMotion.matches || S.watch.skip;
    const dur = instant ? 0 : S.D[a][b] * speed().walk;
    const leg = $("ant-leg");
    const deg = angle(a, b);
    if (leg) { leg.setAttribute("x1", from.x); leg.setAttribute("y1", from.y); }
    $("ant").classList.add("walking");
    return new Promise((resolve) => {
      const t0 = performance.now();
      function frame(now) {
        if (my !== token) return resolve();
        const t = dur && !S.watch.skip ? Math.min(1, (now - t0) / dur) : 1;
        const e = t < 0.5 ? 2 * t * t : 1 - 2 * (1 - t) * (1 - t); // ease in-out
        const x = from.x + (to.x - from.x) * e;
        const y = from.y + (to.y - from.y) * e;
        setAntTransform(x, y, deg, false);
        if (leg) { leg.setAttribute("x2", x); leg.setAttribute("y2", y); }
        if (t < 1) requestAnimationFrame(frame);
        else { const el = $("ant"); if (el) el.classList.remove("walking"); resolve(); }
      }
      requestAnimationFrame(frame);
    });
  }

  function setAntTransform(x, y, deg, smooth) {
    let g = $("ant");
    if (!g) { $("L-ant").innerHTML = ANT_SVG; g = $("ant"); smooth = false; }
    g.style.transition = smooth && !reducedMotion.matches ? "" : "none";
    g.style.transform = `translate(${x}px, ${y}px) rotate(${deg}deg)`;
    S.antDeg = deg;
  }

  /** Put the ant on city i, facing from city `from` (or keep its heading). */
  function placeAnt(i, from, smooth) {
    const c = S.cities[i];
    setAntTransform(c.x, c.y, from == null ? S.antDeg || -30 : angle(from, i), smooth);
  }

  async function play() {
    if (S.playing) { S.playing = false; syncButtons(); return; }
    if (S.busy || S.manual) return;
    const my = token;
    S.playing = true;
    S.stagnant = 0;
    syncButtons();
    status("▶ Running… press Space or ⏸ to pause.");
    let count = 0;
    while (S.playing && my === token) {
      finishIteration();
      renderAll();
      count++;
      if (S.stagnant >= STAGNATION_STOP) {
        S.playing = false;
        status(`🛑 Paused: for ${STAGNATION_STOP} iterations every ant built the same tour (stagnation). Reset, or lower α / raise ρ.`);
        MG.toast("🛑 Stagnation: every ant now builds the same tour.");
        break;
      }
      if (count >= PLAY_MAX) { S.playing = false; status(`⏸ Paused after ${PLAY_MAX} iterations.`); break; }
      await MG.sleep(speed().iter);
    }
    if (my === token) {
      if (!S.playing && S.stagnant < STAGNATION_STOP && count < PLAY_MAX) status(`⏸ Paused at iteration ${S.iter}.`);
      S.playing = false;
      syncButtons();
    }
  }

  // ── you are an ant ────────────────────────────────────────────────────
  function startManual() {
    if (S.busy || S.playing) return;
    S.manual = { tour: [], visited: new Uint8Array(S.n) };
    status("🙋 Click the city where your ant starts.");
    renderAll();
  }

  function manualChoice() {
    const m = S.manual;
    if (!m || !m.tour.length || m.tour.length >= S.n) return null;
    return A.choiceProbs(m.tour[m.tour.length - 1], m.visited, S.tau, S.D, S.params.alpha, S.params.beta);
  }

  function manualPick(i) {
    const m = S.manual;
    if (!m || m.visited[i]) return;
    const prev = m.tour.length ? m.tour[m.tour.length - 1] : null;
    m.tour.push(i);
    m.visited[i] = 1;
    if (m.tour.length === S.n) {
      const tour = m.tour;
      S.manual = null;
      $("L-ant").innerHTML = "";
      const len = addTour(tour, "you");
      const rel = len < S.greedy.len - 1e-9 ? "shorter than" : len > S.greedy.len + 1e-9 ? "longer than" : "the same length as";
      MG.toast(`🙋 Your tour: ${fmt(len)}, ${rel} greedy (${fmt(S.greedy.len)}).`);
      status(`🙋 Your tour (${fmt(len)}) counts as one of this iteration's ants: it deposits pheromone like the others.`);
      renderAll();
      return;
    }
    if (m.tour.length === 1) status(`🙋 Your ant starts at ${label(i)}. Blue halos show how likely a real ant would be to go to each city.`);
    renderMap(); renderPanel(); syncButtons();
    placeAnt(i, prev, prev != null);
  }

  function manualChance() {
    const m = S.manual;
    if (!m) return;
    if (!m.tour.length) return manualPick(S.rng.randrange(S.n));
    manualPick(A.roulette(S.rng, manualChoice()));
  }

  function manualUndo() {
    const m = S.manual;
    if (!m || !m.tour.length) return;
    m.visited[m.tour.pop()] = 0;
    renderMap(); renderPanel();
    if (m.tour.length) placeAnt(m.tour[m.tour.length - 1], m.tour.length > 1 ? m.tour[m.tour.length - 2] : null, true);
    else $("L-ant").innerHTML = "";
  }

  function manualCancel() {
    if (!S.manual) return;
    S.manual = null;
    $("L-ant").innerHTML = "";
    status("Tour cancelled.");
    renderAll();
  }

  // ── map ───────────────────────────────────────────────────────────────
  const pts = (t, close = true) => (close ? t.concat(t[0]) : t).map((i) => `${S.cities[i].x},${S.cities[i].y}`).join(" ");

  /** Static layers, built once per game; renderMap() only updates them. */
  function buildMap() {
    const { cities: C, n } = S;
    let pher = "";
    for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) pher += `<line x1="${C[i].x}" y1="${C[i].y}" x2="${C[j].x}" y2="${C[j].y}" data-e="${i * n + j}"/>`;
    const cities = C.map((c, i) => `<g class="city" data-i="${i}"><title>${c.label}</title><circle class="city-ring" cx="${c.x}" cy="${c.y}" r="4.2"/><circle class="city-dot" cx="${c.x}" cy="${c.y}" r="2.9"/><text x="${c.x}" y="${c.y}">${c.label}</text></g>`).join("");
    $("map").innerHTML = `
      <defs><pattern id="ac-dots" width="5" height="5" patternUnits="userSpaceOnUse"><circle cx="2.5" cy="2.5" r="0.22" class="bg-dot"/></pattern></defs>
      <rect class="bg" x="-5" y="-5" width="110" height="110" fill="url(#ac-dots)"/>
      <g id="L-pher" class="L-pher">${pher}</g><g id="L-flash"></g><g id="L-opt"></g><g id="L-best"></g>
      <g id="L-cand"></g><g id="L-build"></g><g id="L-cities">${cities}</g><g id="L-pct"></g><g id="L-ant"></g>`;
    S.edgeEls = [...$("L-pher").children].map((l) => [Number(l.dataset.e), l]);
    S.cityEls = [...$("L-cities").children];
    S.flashDrawn = -1;
    S.bestDrawn = -1;
  }

  function renderMap() {
    const { cities: C, n, tau, show } = S;

    // pheromone: persistent lines, so width/opacity changes animate (CSS transitions)
    // Each edge's value: pheromone τ, or an ant's choice chance
    // P(i→j) = τ^α·η^β / Σ_k τ^α·η^β (from a city with nothing visited yet),
    // taking the higher of the edge's two ends so every city shows its own
    // favorites. Scaled between the weakest and the strongest edge: equal
    // values everywhere (e.g. pheromone at the start) draw thin, faint lines.
    const attr = S.edgeView === "attr";
    let val = (i, j) => tau[i][j];
    if (attr) {
      const { alpha, beta } = S.params;
      const W = Array.from({ length: n }, () => new Float64Array(n));
      const rowSum = new Float64Array(n);
      for (let i = 0; i < n; i++) {
        for (let j = 0; j < n; j++) {
          if (i === j) continue;
          W[i][j] = Math.pow(tau[i][j], alpha) * Math.pow(1 / S.D[i][j], beta);
          rowSum[i] += W[i][j];
        }
      }
      val = (i, j) => Math.max(W[i][j] / rowSum[i], W[j][i] / rowSum[j]);
    }
    const vals = new Map();
    let tmax = 0;
    let tmin = Infinity;
    for (const [e] of S.edgeEls) {
      const v = val(Math.floor(e / n), e % n);
      vals.set(e, v);
      if (v > tmax) tmax = v;
      if (v < tmin) tmin = v;
    }
    const spread = tmax - tmin;
    const uniform = spread <= 1e-9 * tmax;
    $("L-pher").classList.toggle("attr", attr);
    for (const [e, l] of S.edgeEls) {
      const r = uniform ? 0 : (vals.get(e) - tmin) / spread;
      const vis = show.pher && (uniform || r >= 0.03);
      l.style.strokeWidth = !vis ? "0" : uniform ? "0.3" : (0.15 + 1.25 * r).toFixed(2);
      l.style.strokeOpacity = !vis ? "0" : uniform ? "0.4" : (0.15 + 0.8 * r).toFixed(2);
    }

    // last iteration's tours (redrawn only when a new iteration ends, so the fade plays once)
    const flashL = $("L-flash");
    if (S.flashDrawn !== S.flashId) {
      flashL.innerHTML = S.flash.map((t) => `<polygon class="flash" points="${pts(t)}"/>`).join("");
      flashL.classList.remove("fresh"); void flashL.getBoundingClientRect(); flashL.classList.add("fresh");
      S.flashDrawn = S.flashId;
    }
    flashL.style.display = show.ants && !S.watch && !S.manual ? "" : "none";

    $("L-opt").innerHTML = show.opt && S.opt ? `<polygon class="opt" points="${pts(S.opt.tour)}"/>` : "";
    const bestL = $("L-best");
    if (show.best && S.best) {
      if (S.bestDrawn !== S.bestId || !bestL.firstChild) {
        bestL.innerHTML = `<polygon class="best${S.bestDrawn >= 0 ? " new" : ""}" points="${pts(S.best.tour)}"/>`;
        S.bestDrawn = S.bestId;
      }
    } else { bestL.innerHTML = ""; }

    // the tour being built (watched ant or you), and the candidates' halos
    const building = S.watch ? S.watch.tour : S.manual ? S.manual.tour : null;
    const choice = S.watch ? S.watch.choice : S.manual ? manualChoice() : null;
    let b = "";
    if (building && building.length > 1) b += `<polyline class="${S.watch ? "walk" : "you"}" points="${pts(building, false)}"/>`;
    if (S.watch) {
      const c = C[building[building.length - 1]];
      b += `<line id="ant-leg" class="walk" x1="${c.x}" y1="${c.y}" x2="${c.x}" y2="${c.y}"/>`;
    }
    $("L-build").innerHTML = b;

    let cand = "";
    let pctH = "";
    const pOf = new Map();
    if (choice) {
      const cur = C[building[building.length - 1]];
      for (const r of choice.rows) pOf.set(r.j, r.p);
      for (const r of choice.rows) {
        const c = C[r.j];
        cand += `<line class="cand-edge" x1="${cur.x}" y1="${cur.y}" x2="${c.x}" y2="${c.y}" stroke-opacity="${(0.12 + 0.88 * r.p).toFixed(2)}" stroke-width="${(0.2 + 1.2 * r.p).toFixed(2)}"/>`;
      }
      for (const r of choice.rows) {
        const chosen = S.watch && S.watch.chosen === r.j;
        cand += `<circle class="halo${chosen ? " chosen" : ""}" cx="${C[r.j].x}" cy="${C[r.j].y}" r="${(3.4 + 7 * Math.sqrt(r.p)).toFixed(2)}"/>`;
      }
      choice.rows.slice().sort((a, b2) => b2.p - a.p).slice(0, 6).forEach((r) => {
        if (r.p < 0.005) return;
        const c = C[r.j];
        const y = c.y < 10 ? c.y + 7.4 : c.y - 5;
        pctH += `<text class="pct" x="${c.x}" y="${y}">${Math.round(r.p * 100)}%</text>`;
      });
    }
    $("L-cand").innerHTML = cand;
    $("L-pct").innerHTML = pctH;

    // cities: persistent groups, only classes change
    const visited = building ? new Set(building) : null;
    const cur = building && building.length ? building[building.length - 1] : -1;
    const start = building && building.length ? building[0] : -1;
    const picking = !!S.manual;
    S.cityEls.forEach((g, i) => {
      const v = !!(visited && visited.has(i));
      g.classList.toggle("visited", v);
      g.classList.toggle("current", i === cur);
      g.classList.toggle("start", i === start && i !== cur);
      g.classList.toggle("clickable", picking && !v);
      const t = picking && pOf.has(i) ? `${C[i].label}: ${pct(pOf.get(i))} chance` : C[i].label;
      g.querySelector("title").textContent = t;
      if (picking && !v) { g.setAttribute("tabindex", "0"); g.setAttribute("role", "button"); g.setAttribute("aria-label", t); }
      else { g.removeAttribute("tabindex"); g.removeAttribute("role"); g.removeAttribute("aria-label"); }
    });
    $("map").classList.toggle("picking", picking);
  }

  /** A short message in the strip under the map (stays until the next one). */
  function status(text) {
    const el = $("map-status");
    el.textContent = text;
    el.classList.remove("show"); void el.offsetWidth; el.classList.add("show");
  }

  // ── side panel ────────────────────────────────────────────────────────
  function probTable(choice, cur, chosen, clickable) {
    const rows = choice.rows.slice().sort((a, b) => b.p - a.p);
    const LIMIT = 8;
    const shown = rows.slice(0, LIMIT);
    const rest = rows.length - shown.length;
    const restP = rows.slice(LIMIT).reduce((s, r) => s + r.p, 0);
    const pmax = rows.length ? rows[0].p : 1;
    return `<div class="ac-probs-wrap"><table class="ac-probs">
      <thead><tr><th class="text">Edge</th><th title="Distance">d</th><th title="Pheromone on the edge">τ</th><th title="Visibility η = 1/d">η</th><th title="τ^α · η^β">τ<sup>α</sup>η<sup>β</sup></th><th class="text">Chance</th></tr></thead>
      <tbody>${shown.map((r) => `<tr class="${r.j === chosen ? "chosen" : ""}${clickable ? " pick" : ""}" data-i="${r.j}"${clickable ? ` tabindex="0"` : ""}>
        <td class="text"><b>${label(cur)}→${label(r.j)}</b></td><td>${r.d.toFixed(1)}</td><td>${fmtW(r.tau)}</td><td>${r.eta.toFixed(3)}</td><td>${fmtW(r.w)}</td>
        <td class="text"><span class="pbar"><span style="width:${((r.p / pmax) * 100).toFixed(1)}%"></span></span><b>${pct(r.p)}</b></td></tr>`).join("")}
      ${rest ? `<tr class="more"><td class="text" colspan="6">+ ${rest} more cities · ${pct(restP)} in total</td></tr>` : ""}
      </tbody></table></div>
      <p class="ac-sum">Chance = τ<sup>α</sup>η<sup>β</sup> ÷ Σ, with Σ = ${fmtW(choice.total)}</p>`;
  }

  function steps(tour) {
    return `<p class="ac-tourline">${tour.map((i, k) => `<span class="${k === tour.length - 1 ? "now" : ""}">${label(i)}</span>`).join("<i>→</i>")}</p>`;
  }

  function renderPanel() {
    const el = $("panel");
    const p = S.params;
    let h = "";
    if (S.watch) {
      const w = S.watch;
      h += `<div class="ac-card-title"><span>🐜 Ant ${w.k} of ${p.m}</span><span class="ac-step">city ${w.tour.length} / ${S.n}</span></div>`;
      h += steps(w.tour);
      if (w.choice) {
        const cur = w.tour[w.tour.length - 1];
        const r = w.chosen == null ? null : w.choice.rows.find((x) => x.j === w.chosen);
        h += `<p class="ac-say">${r ? `🎯 The roulette wheel picked <b>${label(w.chosen)}</b> (${pct(r.p)} chance).` : `🎲 At <b>${label(cur)}</b>, spinning the roulette wheel…`}</p>`;
        h += probTable(w.choice, cur, w.chosen, false);
      } else {
        h += `<p class="ac-say">🏠 Every city visited: back to <b>${label(w.tour[0])}</b>.</p>`;
      }
      h += `<div class="row"><button class="btn small" data-act="skip" type="button"${w.skip ? " disabled" : ""}>⏩ Skip to the end <kbd>S</kbd></button></div>`;
    } else if (S.manual) {
      const m = S.manual;
      h += `<div class="ac-card-title"><span>🙋 You are ant ${S.pending.length + 1} of ${p.m}</span><span class="ac-step">${m.tour.length ? `city ${m.tour.length} / ${S.n}` : ""}</span></div>`;
      if (!m.tour.length) {
        h += `<p class="ac-say">👆 Click the city on the map where your ant starts.</p>`;
      } else {
        const cur = m.tour[m.tour.length - 1];
        h += steps(m.tour);
        h += `<p class="ac-say">👆 Click the next city, on the map or in the table. A real ant spins the wheel: try 🎲.</p>`;
        h += probTable(manualChoice(), cur, null, true);
      }
      h += `<div class="row"><button class="btn small primary" data-act="chance" type="button">🎲 Let chance decide <kbd>C</kbd></button>
        <button class="btn small" data-act="undo" type="button"${m.tour.length ? "" : " disabled"}>↶ Undo <kbd>Z</kbd></button>
        <button class="btn small" data-act="cancel" type="button">✖ Cancel <kbd>Esc</kbd></button></div>`;
    } else {
      h += `<div class="ac-card-title"><span>🐜 This iteration's ants</span><span class="ac-step">${S.pending.length} of ${p.m} done</span></div>`;
      if (S.pending.length) {
        h += `<ul class="ac-antlist">${S.pending.map((a, k) => `<li class="${a.who}"><span>${a.who === "you" ? "🙋 You" : "🐜 Ant " + (k + 1)}</span><b>${fmt(a.len)}</b></li>`).join("")}</ul>`;
        h += `<p class="caption">Pheromone is updated once all ${p.m} ants are done.</p>`;
      } else if (S.iter === 0) {
        h += `<p class="ac-say">Pheromone is 1 on every edge, so the first ants are guided by distance alone.</p>
          <ol class="ac-howto"><li><b>🐜 Watch</b> one ant choose, step by step.</li><li><b>🙋 Be an ant</b> and build a tour yourself.</li><li><b>▶ Play</b> and watch the trail form.</li></ol>`;
      } else {
        const last = S.history[S.history.length - 1];
        h += `<p class="ac-say">Last iteration: best ant <b>${fmt(last.best)}</b>, average <b>${fmt(last.mean)}</b>.</p>`;
      }
      if (S.best && S.show.best) {
        const gap = S.opt ? (S.best.len - S.opt.len) / S.opt.len : null;
        h += `<div class="ac-best"><div class="ac-card-title"><span><i class="lg best"></i> Best tour · ${fmt(S.best.len)}</span>
          ${gap != null ? `<span class="badge ${gap < 1e-9 ? "ok" : ""}">${gap < 1e-9 ? "✓ optimal" : "+" + (gap * 100).toFixed(1) + "% vs optimum"}</span>` : ""}</div>
          <p class="caption">${S.best.who === "you" ? "🙋 Found by you" : "🐜 Found by the colony"} in iteration ${S.best.iter}.</p>
          <p class="ac-tourline small">${tourLabel(S.best.tour)}</p></div>`;
      }
      if (S.yourBest) h += `<p class="caption">🙋 Your best tour: <b>${fmt(S.yourBest.len)}</b></p>`;
    }
    el.innerHTML = h;
  }

  // ── header, dots, chart, log ──────────────────────────────────────────
  function renderMetrics() {
    $("m-iter").textContent = S.iter;
    $("kpi-best").hidden = !S.show.best;
    $("m-best").textContent = S.best ? fmt(S.best.len) : "—";
    const gapEl = $("m-gap");
    if (!S.best) { gapEl.textContent = ""; gapEl.className = ""; }
    else if (S.opt) {
      const g = (S.best.len - S.opt.len) / S.opt.len;
      gapEl.textContent = g < 1e-9 ? "✓ optimal" : `+${(g * 100).toFixed(1)}%`;
      gapEl.className = g < 1e-9 ? "ok" : "";
    } else {
      const g = (S.best.len - S.greedy.len) / S.greedy.len;
      gapEl.textContent = `${g <= 0 ? "−" : "+"}${Math.abs(g * 100).toFixed(1)}% vs greedy`;
      gapEl.className = g < 0 ? "ok" : "";
    }
    $("iter-label").textContent = `Iteration ${S.iter + 1}`;
    const m = S.params.m;
    let dots = "";
    for (let k = 0; k < m; k++) {
      const a = S.pending[k];
      const active = k === S.pending.length && (S.watch || S.manual);
      dots += `<i class="${a ? (a.who === "you" ? "you" : "done") : active ? "active" : ""}" title="${a ? (a.who === "you" ? "You" : "Ant " + (k + 1)) + ": " + fmt(a.len) : "Ant " + (k + 1)}"></i>`;
    }
    $("ant-dots").innerHTML = dots;
    $("ant-dots").classList.toggle("many", m > 16);
  }

  function renderChart() {
    const c = MG.theme.colors();
    const dark = MG.theme.current() === "dark";
    const col = dark
      ? { pher: "#f0a838", best: "#3cc483", iter: "#6aa7f0", opt: "#b48af0" }
      : { pher: "#c77d12", best: "#1a9c5e", iter: "#2a78d6", opt: "#8a4fd6" };
    const x = S.history.map((h) => h.iter);
    const traces = [];
    // Earlier runs are "best so far" curves too, so they hide with the best tour.
    if (S.show.best) S.runs.forEach((r, k) => traces.push({
      x: r.y.map((_, i) => i + 1), y: r.y, name: r.name, mode: "lines",
      line: { width: 1.5, color: c.muted, dash: ["dot", "dash", "longdash", "dashdot"][k % 4] }, opacity: 0.75,
    }));
    traces.push(
      { x, y: S.history.map((h) => h.mean), name: "Average ant", mode: "lines", line: { width: 1.5, color: col.pher } },
      { x, y: S.history.map((h) => h.best), name: "Best ant of the iteration", mode: "lines", line: { width: 1, color: col.iter } },
    );
    if (S.show.best) traces.push({ x, y: S.history.map((h) => h.bestSoFar), name: "Best so far", mode: "lines", line: { width: 3, color: col.best, shape: "hv" } });
    const yours = S.history.filter((h) => h.you != null);
    if (yours.length) traces.push({ x: yours.map((h) => h.iter), y: yours.map((h) => h.you), name: "🙋 Your ant", mode: "markers", marker: { size: 11, symbol: "star", color: col.opt } });
    const maxX = Math.max(10, x.length, ...S.runs.map((r) => r.y.length));
    const shapes = [];
    const annotations = [];
    const hline = (y, text, color, below) => {
      shapes.push({ type: "line", x0: 0.5, x1: maxX + 0.5, y0: y, y1: y, line: { color, width: 1.5, dash: "dash" } });
      annotations.push({ x: maxX + 0.5, y, xanchor: "right", yanchor: below ? "top" : "bottom", text, showarrow: false, font: { size: 11, color } });
    };
    // Greedy is never below the optimum: label greedy above its line, the optimum below its own.
    hline(S.greedy.len, `Greedy ${fmt(S.greedy.len)}`, c.muted, false);
    if (S.opt) hline(S.opt.len, `Optimum ${fmt(S.opt.len)}`, col.opt, true);
    MG.plot($("chart"), traces, {
      height: 340, margin: { l: 56, r: 16, t: 10, b: 44 },
      xaxis: { title: { text: "Iteration" }, range: [0.5, maxX + 0.5], dtick: maxX <= 20 ? 1 : undefined },
      yaxis: { title: { text: "Tour length" } },
      legend: { orientation: "h", y: -0.22 },
      shapes, annotations, hovermode: "x unified",
    });
    $("chart-caption").textContent = S.history.length
      ? `${S.history.length} iterations · ${S.history.reduce((s, h) => s + h.ants, 0).toLocaleString("en-US")} tours built so far, out of ${A.tourCount(S.n)} possible. When the average line meets the best line, all ants build the same tour.`
      : "The chart starts once the first iteration is done.";
  }

  function renderTable() {
    const rows = S.history.slice(-50).reverse();
    MG.renderTable($("history"), [
      { key: "iter", label: "Iteration" },
      { key: "best", label: "Best ant", fmt },
      { key: "mean", label: "Average", fmt },
      { key: "worst", label: "Worst ant", fmt },
      ...(S.show.best ? [{ key: "bestSoFar", label: "Best so far", fmt }] : []),
      { key: "you", label: "🙋 You", fmt },
    ], rows);
    $("log-wrap").hidden = !rows.length;
  }

  function syncButtons() {
    const busy = !!(S.busy || S.manual);
    $("watch").disabled = busy || S.playing;
    $("finish-iter").disabled = busy || S.playing;
    $("be-ant").disabled = busy || S.playing;
    $("play").disabled = busy;
    $("play").classList.toggle("primary", S.playing);
    $("play").classList.toggle("running", S.playing);
    $("play-ico").textContent = S.playing ? "⏸" : "▶";
    $("play-txt").textContent = S.playing ? "Pause" : "Play";
    $("play-sub").textContent = S.playing ? "running…" : "run iterations";
    $("watch").classList.toggle("primary", !S.playing);
    document.querySelectorAll(".ac-preset").forEach((b) => { b.disabled = busy; });
  }

  function syncParamInputs() {
    const p = S.params;
    $("alpha").value = p.alpha; $("alpha-out").textContent = p.alpha;
    $("beta").value = p.beta; $("beta-out").textContent = p.beta;
    $("rho").value = p.rho; $("rho-out").textContent = p.rho;
    $("ants").value = p.m; $("m-out").textContent = p.m;
    $("elitist").checked = p.elitist;
    $("speed").value = S.speed;
    $("speed-out").textContent = speed().name;
    renderFormula();
  }

  function renderFormula() {
    const p = S.params;
    $("formula").innerHTML = `P(i→j) ∝ τ<sup>${p.alpha}</sup> · (1/d)<sup>${p.beta}</sup> &nbsp;·&nbsp; keep ${Math.round((1 - p.rho) * 100)}% each iteration`;
  }

  function renderAll() {
    renderMetrics();
    renderMap();
    renderPanel();
    renderChart();
    renderTable();
    syncButtons();
  }

  // ── events ────────────────────────────────────────────────────────────
  const actions = {
    watch: () => watchAnt(),
    finish: () => {
      if (S.busy || S.playing || S.manual) return;
      finishIteration();
      renderAll();
    },
    play: () => play(),
    beAnt: () => startManual(),
    reset: () => {
      resetColony(true);
      renderAll();
      status("↺ Colony reset: pheromone back to 1 everywhere. The previous run stays on the chart.");
    },
    skip: () => { if (S.watch) { S.watch.skip = true; renderPanel(); } },
  };
  $("watch").addEventListener("click", actions.watch);
  $("finish-iter").addEventListener("click", actions.finish);
  $("play").addEventListener("click", actions.play);
  $("be-ant").addEventListener("click", actions.beAnt);
  $("reset").addEventListener("click", actions.reset);
  $("new-game").addEventListener("click", goSetup);
  $("copy-code").addEventListener("click", async () => {
    try { await navigator.clipboard.writeText(S.code); MG.toast(`📋 Copied game code ${S.code}`); }
    catch (e) { MG.toast(`Game code: ${S.code}`); }
  });

  for (const key of ["alpha", "beta", "rho"]) {
    $(key).addEventListener("input", () => {
      S.params[key] = Number($(key).value);
      $(key + "-out").textContent = S.params[key];
      renderFormula();
      if (S.manual) { renderMap(); renderPanel(); }
      else if (S.edgeView === "attr" && key !== "rho" && !S.watch) renderMap();
      if (key === "rho") {
        status(`💨 ρ = ${S.params.rho}: at the next pheromone update, every edge keeps ${Math.round((1 - S.params.rho) * 100)}% of its pheromone.`);
      } else if (S.edgeView === "pher" && !S.viewHinted) {
        S.viewHinted = true;
        status("α and β don't change pheromone, only how ants weigh it. To see them, show “Ant's choice”.");
      }
    });
  }

  function setEdgeView(v) {
    S.edgeView = v;
    $("edge-chip-txt").textContent = v === "attr" ? "Ant's choice" : "Pheromone";
    $("edge-chip-lg").className = "lg " + (v === "attr" ? "attr" : "pher");
    renderMap();
    status(v === "attr"
      ? "🔵 Thicker = an ant is more likely to take that edge. Move α or β to see it change."
      : "🟠 Thicker = more pheromone. It changes when an iteration ends.");
  }
  document.querySelectorAll('input[name="edge-view"]').forEach((r) => r.addEventListener("change", () => { if (S) setEdgeView(r.value); }));
  $("ants").addEventListener("input", () => {
    S.params.m = Number($("ants").value);
    $("m-out").textContent = S.params.m;
    if (!S.busy && !S.manual && S.pending.length >= S.params.m) endIteration();
    if (!S.playing) renderAll(); else renderMetrics();
  });
  $("elitist").addEventListener("change", () => { S.params.elitist = $("elitist").checked; });
  $("speed").addEventListener("input", () => { S.speed = Number($("speed").value); $("speed-out").textContent = speed().name; });
  $("defaults").addEventListener("click", () => {
    Object.assign(S.params, DEFAULTS, { m: S.level.ants });
    syncParamInputs();
    if (!S.playing && !S.busy && !S.manual) renderAll();
    status("⚙️ Default settings restored. They apply from the next ant.");
  });

  for (const [id, key] of [["show-pher", "pher"], ["show-ants", "ants"], ["show-best", "best"], ["show-opt", "opt"]]) {
    $(id).addEventListener("change", () => {
      S.show[key] = $(id).checked;
      if (key !== "best") return renderMap();
      // The best tour hides everywhere, not only on the map.
      renderMetrics(); renderMap(); renderPanel(); renderChart(); renderTable();
      status(S.show.best ? "Best tour shown again." : "Best tour hidden everywhere: map, header, panel, chart and log.");
    });
  }

  $("presets").addEventListener("click", (e) => {
    const b = e.target.closest(".ac-preset");
    if (!b || b.disabled) return;
    const preset = PRESETS[Number(b.dataset.k)];
    resetColony(true);
    Object.assign(S.params, preset.p);
    syncParamInputs();
    renderAll();
    $("map").scrollIntoView({ behavior: reducedMotion.matches ? "auto" : "smooth", block: "center" });
    status(`🧪 ${preset.name}: ${preset.what}`);
    play();
  });

  // Map: click (or Enter/Space) on a city while you are the ant.
  const pickFrom = (e) => {
    const g = e.target.closest("[data-i]");
    if (g && S && S.manual) manualPick(Number(g.dataset.i));
  };
  $("map").addEventListener("click", pickFrom);
  $("map").addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); e.stopPropagation(); pickFrom(e); } });
  $("panel").addEventListener("click", (e) => {
    const act = e.target.closest("[data-act]");
    if (act) {
      const a = act.dataset.act;
      if (a === "chance") manualChance();
      else if (a === "undo") manualUndo();
      else if (a === "cancel") manualCancel();
      else if (a === "skip") actions.skip();
      return;
    }
    const row = e.target.closest("tr.pick[data-i]");
    if (row) manualPick(Number(row.dataset.i));
  });
  $("panel").addEventListener("keydown", (e) => {
    const row = e.target.closest("tr.pick[data-i]");
    if (row && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); e.stopPropagation(); manualPick(Number(row.dataset.i)); }
  });
  // Hovering a table row highlights that city on the map.
  const hl = (e, on) => {
    const row = e.target.closest("tr[data-i]");
    if (row && S.cityEls) S.cityEls[Number(row.dataset.i)].classList.toggle("hl", on);
  };
  $("panel").addEventListener("mouseover", (e) => hl(e, true));
  $("panel").addEventListener("mouseout", (e) => hl(e, false));

  // Keyboard shortcuts (ignored while typing in a field).
  document.addEventListener("keydown", (e) => {
    if (!S || $("phase-colony").hidden || e.ctrlKey || e.metaKey || e.altKey) return;
    const t = e.target;
    if (t.closest && t.closest("input[type=text], input[type=number], textarea, select")) return;
    const k = e.key.toLowerCase();
    if (k === " " && t.closest && t.closest("button, input, summary, a")) return; // Space keeps its normal job there
    let done = true;
    if (k === " " || k === "p") {
      if (!S.manual && !S.busy) actions.play(); else done = false;
    } else if (k === "n") actions.watch();
    else if (k === "f") actions.finish();
    else if (k === "y") actions.beAnt();
    else if (k === "r") actions.reset();
    else if (k === "s") actions.skip();
    else if (k === "c" && S.manual) manualChance();
    else if ((k === "z" || k === "backspace") && S.manual) manualUndo();
    else if (k === "escape" && S.manual) manualCancel();
    else done = false;
    if (done) e.preventDefault();
  });

  MG.theme.onChange(() => { if (S && !$("phase-colony").hidden) renderChart(); });
  window.addEventListener("beforeunload", (e) => { if (S && !$("phase-colony").hidden && (S.iter > 0 || S.pending.length)) e.preventDefault(); });
})();
