/* Landscape generation and scoring for Peak and Valley (exhaustive vs.
 * local search). Port of ExhaustiveVsLocalSearch_App/game_logic.py: same
 * constants and NumPy-compatible random draws, so a game code produces the
 * same five landscapes as the Streamlit app.
 *
 * Mirrors the "Exhaustive vs Local Search" example from IN2041 Session 2:
 * a 1-D discrete function f(x) with a global minimum and a few local-minima
 * traps. Each round grows the x-axis (more candidate solutions), echoing
 * the combinatorial-explosion discussion in that session.
 */
(function () {
  "use strict";
  const PV = (globalThis.PV = globalThis.PV || {});

  // x ranges over 0..ROUND_XMAX[i] in round i, so the axis grows each round.
  const ROUND_XMAX = [10, 15, 20, 25, 30];
  // Gaussian "valleys" (potential local optima) carved into each landscape.
  const ROUND_VALLEYS = [2, 2, 3, 3, 4];
  const BASELINE = 6.0;
  const NOISE_STD = 0.12;
  const QUALITY_WEIGHT = 0.65;
  const EFFICIENCY_WEIGHT = 0.35;
  const NEIGHBORHOOD_CHOICES = [1, 2]; // closest neighbors revealed per side
  const MAX_RESTARTS_CAP = 5;

  /** Seed from a share code (a random code if blank) — returns {code, seed}. */
  function resolveCode(code) {
    const c = String(code || "").trim() || MG.newGameCode();
    return { code: c.toUpperCase(), seed: MG.codeToSeed(c) };
  }

  /** Five landscapes from one seed, via SeedSequence spawning so the rounds
   *  don't correlate (same as NumPy's recommended pattern in the original). */
  function generateAllRounds(seed) {
    const children = new MG.SeedSequence(seed).spawn(ROUND_XMAX.length);
    return children.map((child, i) => generateLandscape(new MG.NpGenerator(child), i));
  }

  function generateLandscape(rng, roundIndex) {
    const xmax = ROUND_XMAX[roundIndex];
    const nValleys = ROUND_VALLEYS[roundIndex];
    const n = xmax + 1;
    const centers = rng.uniform(0, xmax, nValleys);
    const depths = rng.uniform(3.0, 5.5, nValleys);
    const widths = rng.uniform(1.0, 2.2, nValleys);
    // Valleys combine by MAX (not sum), so overlapping valleys don't stack
    // into one wide flat-bottomed plateau.
    const y = [];
    for (let x = 0; x < n; x++) {
      let deepest = -Infinity;
      for (let i = 0; i < nValleys; i++) {
        const d = x - centers[i];
        const dip = depths[i] * Math.exp(-(d * d) / (2 * (widths[i] * widths[i])));
        if (dip > deepest) deepest = dip;
      }
      y.push(BASELINE - deepest);
    }
    const noise = rng.normal(0, NOISE_STD, n);
    return y.map((v, i) => Math.max(0, v + noise[i]));
  }

  /** Every point a local-search run could stop at (incl. the global min):
   *  neither existing neighbor is strictly better. */
  function localMinimaIndices(ys) {
    const out = [];
    for (let i = 0; i < ys.length; i++) {
      const leftOk = i === 0 || ys[i] <= ys[i - 1];
      const rightOk = i === ys.length - 1 || ys[i] <= ys[i + 1];
      if (leftOk && rightOk) out.push(i);
    }
    return out;
  }

  const isImproving = (candidateY, currentY) => candidateY < currentY;

  /** The n closest x's on each side of currentX, clipped to [0, xmax]. */
  function neighborXs(currentX, n, xmax) {
    const out = [];
    for (let x = Math.max(0, currentX - n); x <= Math.min(xmax, currentX + n); x++) if (x !== currentX) out.push(x);
    return out;
  }

  /** 65% solution quality + 35% efficiency (fewer reveals), scaled to 1000.
   *  Exhaustive always finds the optimum but never earns efficiency, so it
   *  scores a fixed 1000 * QUALITY_WEIGHT every round. */
  function scoreRound(foundY, ys, evaluations) {
    const gmin = Math.min(...ys);
    const gmax = Math.max(...ys);
    const span = gmax - gmin;
    const gap = Math.max(0.0, foundY - gmin);
    const quality = span <= 1e-9 ? 1.0 : Math.max(0.0, 1.0 - gap / span);
    const efficiency = Math.max(0.0, 1.0 - evaluations / ys.length);
    const raw = QUALITY_WEIGHT * quality + EFFICIENCY_WEIGHT * efficiency;
    return { score: MG.pyRound(1000 * raw), quality, efficiency, gap };
  }

  /** Index of the first minimum (Python's min(range(n), key=ys.__getitem__)). */
  function argmin(ys) {
    let best = 0;
    for (let i = 1; i < ys.length; i++) if (ys[i] < ys[best]) best = i;
    return best;
  }

  PV.logic = {
    ROUND_XMAX, ROUND_VALLEYS, QUALITY_WEIGHT, EFFICIENCY_WEIGHT, NEIGHBORHOOD_CHOICES, MAX_RESTARTS_CAP,
    resolveCode, generateAllRounds, localMinimaIndices, isImproving, neighborXs, scoreRound, argmin,
  };
})();
