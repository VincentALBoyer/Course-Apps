/* Ant Colony: pure logic (no DOM). Ant System (Dorigo 1996) on a small
 * symmetric traveling salesman instance.
 *
 *   P(i → j) = τ_ij^α · η_ij^β / Σ_k τ_ik^α · η_ik^β     (η = 1 / d)
 *   τ ← (1 − ρ) · τ  +  Σ_ants Q / L_ant  on each edge the ant used
 *
 * τ starts at 1 on every edge and Q is the greedy tour's length, so an ant
 * whose tour is as good as greedy lays exactly 1.0 on each of its edges.
 */
(function () {
  "use strict";
  const MG = (globalThis.MG = globalThis.MG || {});

  const LEVELS = {
    easy: { key: "easy", label: "Easy", n: 8, ants: 8, minGap: 16 },
    medium: { key: "medium", label: "Medium", n: 14, ants: 10, minGap: 12 },
    hard: { key: "hard", label: "Hard", n: 26, ants: 15, minGap: 9 },
  };
  const LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
  const TAU0 = 1;
  const TAU_MIN = 0.001; // floor so a fully evaporated edge can still be picked
  const HELD_KARP_MAX = 15;

  /** Random cities in [6, 94]², kept a minimum distance apart. */
  function makeCities(rng, n, minGap) {
    const pts = [];
    let gap = minGap;
    let tries = 0;
    while (pts.length < n) {
      const x = Math.round(rng.uniform(6, 94) * 10) / 10;
      const y = Math.round(rng.uniform(6, 94) * 10) / 10;
      if (pts.every((p) => Math.hypot(p.x - x, p.y - y) >= gap)) pts.push({ x, y, label: LETTERS[pts.length] });
      if (++tries > 4000) { gap *= 0.9; tries = 0; }
    }
    return pts;
  }

  function distances(cities) {
    const n = cities.length;
    const D = Array.from({ length: n }, () => new Float64Array(n));
    for (let i = 0; i < n; i++) {
      for (let j = i + 1; j < n; j++) {
        const d = Math.hypot(cities[i].x - cities[j].x, cities[i].y - cities[j].y);
        D[i][j] = D[j][i] = d;
      }
    }
    return D;
  }

  function tourLength(tour, D) {
    let s = 0;
    for (let i = 0; i < tour.length; i++) s += D[tour[i]][tour[(i + 1) % tour.length]];
    return s;
  }

  /** Greedy: start at A, always go to the nearest unvisited city. */
  function nearestNeighbor(D, start = 0) {
    const n = D.length;
    const seen = new Uint8Array(n);
    const tour = [start];
    seen[start] = 1;
    while (tour.length < n) {
      const cur = tour[tour.length - 1];
      let best = -1;
      for (let j = 0; j < n; j++) if (!seen[j] && (best < 0 || D[cur][j] < D[cur][best])) best = j;
      tour.push(best);
      seen[best] = 1;
    }
    return { tour, len: tourLength(tour, D) };
  }

  /** Exact optimum by Held–Karp dynamic programming (small n only). */
  function heldKarp(D) {
    const n = D.length;
    if (n > HELD_KARP_MAX) return null;
    const m = n - 1; // city 0 is the fixed start; bit k = city k+1
    const FULL = 1 << m;
    const dp = new Float64Array(FULL * m).fill(Infinity);
    const par = new Int8Array(FULL * m).fill(-1);
    for (let j = 0; j < m; j++) dp[(1 << j) * m + j] = D[0][j + 1];
    for (let S = 1; S < FULL; S++) {
      for (let j = 0; j < m; j++) {
        if (!(S & (1 << j))) continue;
        const v = dp[S * m + j];
        if (v === Infinity) continue;
        for (let k = 0; k < m; k++) {
          if (S & (1 << k)) continue;
          const S2 = S | (1 << k);
          const nv = v + D[j + 1][k + 1];
          if (nv < dp[S2 * m + k]) { dp[S2 * m + k] = nv; par[S2 * m + k] = j; }
        }
      }
    }
    let bestJ = 0;
    let bestLen = Infinity;
    for (let j = 0; j < m; j++) {
      const v = dp[(FULL - 1) * m + j] + D[j + 1][0];
      if (v < bestLen) { bestLen = v; bestJ = j; }
    }
    const rev = [];
    let S = FULL - 1;
    let j = bestJ;
    while (j >= 0) {
      rev.push(j + 1);
      const pj = par[S * m + j];
      S ^= 1 << j;
      j = pj;
    }
    const tour = [0, ...rev.reverse()];
    return { tour, len: tourLength(tour, D) };
  }

  function initPheromone(n) {
    return Array.from({ length: n }, () => new Float64Array(n).fill(TAU0));
  }

  /** The choice rule at `cur`: one row per unvisited city, most likely first. */
  function choiceProbs(cur, visited, tau, D, alpha, beta) {
    const rows = [];
    let total = 0;
    for (let j = 0; j < D.length; j++) {
      if (visited[j]) continue;
      const eta = 1 / D[cur][j];
      const w = Math.pow(tau[cur][j], alpha) * Math.pow(eta, beta);
      rows.push({ j, d: D[cur][j], tau: tau[cur][j], eta, w, p: 0 });
      total += w;
    }
    for (const r of rows) r.p = total > 0 ? r.w / total : 1 / rows.length;
    // Roulette order is by city index (stable for a given seed); display
    // order is by probability.
    return { rows, total };
  }

  /** Roulette wheel: always draws exactly one random number. */
  function roulette(rng, choice) {
    const x = rng.random();
    let acc = 0;
    for (const r of choice.rows) {
      acc += r.p;
      if (x < acc) return r.j;
    }
    return choice.rows[choice.rows.length - 1].j;
  }

  /** One ant's full tour (same random draws as the animated ant). */
  function buildTour(rng, tau, D, alpha, beta) {
    const n = D.length;
    const start = rng.randrange(n);
    const visited = new Uint8Array(n);
    const tour = [start];
    visited[start] = 1;
    while (tour.length < n) {
      const j = roulette(rng, choiceProbs(tour[tour.length - 1], visited, tau, D, alpha, beta));
      tour.push(j);
      visited[j] = 1;
    }
    return tour;
  }

  function deposit(tau, tour, amount) {
    for (let i = 0; i < tour.length; i++) {
      const a = tour[i];
      const b = tour[(i + 1) % tour.length];
      tau[a][b] += amount;
      tau[b][a] = tau[a][b];
    }
  }

  /** End of an iteration: evaporate everywhere, then every ant deposits
   *  Q / L on its edges. Elitist: the best-so-far tour also deposits
   *  e · Q / L_best, with e = number of cities. */
  function updatePheromone(tau, ants, rho, Q, elite) {
    const n = tau.length;
    for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) if (i !== j) tau[i][j] = Math.max(TAU_MIN, (1 - rho) * tau[i][j]);
    for (const a of ants) deposit(tau, a.tour, Q / a.len);
    if (elite) deposit(tau, elite.tour, (n * Q) / elite.len);
  }

  /** Number of distinct tours, (n−1)!/2, as a short string. */
  function tourCount(n) {
    let c = 1;
    for (let k = 3; k <= n - 1; k++) c *= k;
    if (c < 1e6) return c.toLocaleString("en-US");
    if (c < 1e12) {
      const units = [[1e9, "billion"], [1e6, "million"]];
      for (const [u, name] of units) if (c >= u) return "≈ " + (c / u).toPrecision(2) + " " + name;
    }
    const e = Math.floor(Math.log10(c));
    return "≈ " + (c / 10 ** e).toFixed(1) + " × 10^" + e;
  }

  /** Same tour up to start city and direction? */
  function sameTour(a, b) {
    if (!a || !b || a.length !== b.length) return false;
    const n = a.length;
    const k = b.indexOf(a[0]);
    if (k < 0) return false;
    let fwd = true;
    let bwd = true;
    for (let i = 0; i < n; i++) {
      if (a[i] !== b[(k + i) % n]) fwd = false;
      if (a[i] !== b[(k - i + n) % n]) bwd = false;
    }
    return fwd || bwd;
  }

  MG.ACO = {
    LEVELS, TAU0, TAU_MIN, makeCities, distances, tourLength, nearestNeighbor, heldKarp,
    initPheromone, choiceProbs, roulette, buildTour, updatePheromone, tourCount, sameTour,
  };
})();
