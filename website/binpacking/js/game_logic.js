/* Round/instance generation, placement validation, and scoring for the
 * 2D bin-packing intro game. Port of Greedy_BinPacking_App/game_logic.py —
 * same constants, same float operations in the same order, so a given seed
 * generates exactly the same instances as the Streamlit app.
 *
 * No reference greedy algorithm is implemented here on purpose — the whole
 * point of Game mode is for students to discover their own heuristic without
 * being anchored to one we hand them.
 */
(function () {
  "use strict";
  const BP = (globalThis.BP = globalThis.BP || {});
  const { pyRound } = MG;

  const BIN_WIDTH = 20;
  const BIN_HEIGHT = 14;

  // Game mode uses integer levels 1-5 (one per round) with a FIXED bin size
  // and a gentle, linear item-count ramp (~6-15 items). Challenge/Scoring
  // expose 1-10 and scale much harder: the bin grows AND the item count
  // grows exponentially, so difficulty 10 lands in the hundreds of items.
  const BASE_ITEM_COUNT = 6;
  const ITEM_COUNT_STEP = 2.2;
  const BASE_AREA_FRACTION = 0.7;
  const AREA_FRACTION_STEP = 0.15;
  const BASE_VARIANCE = 0.3;
  const VARIANCE_STEP = 0.15;
  const BIN_GROWTH_STEP = 0.15;
  const CHALLENGE_ITEM_COUNT_BASE = 6;
  const CHALLENGE_ITEM_COUNT_GROWTH = 1.6;

  // Game-mode hard variant: a bigger fixed bin, more items, and an item
  // area that always exceeds the bin's area, so in every round some items
  // must be left out and the choice of what to skip matters.
  const HARD_BIN_WIDTH = 26;
  const HARD_BIN_HEIGHT = 18;
  const HARD_BASE_ITEM_COUNT = 10;
  const HARD_ITEM_COUNT_STEP = 3;
  const HARD_BASE_AREA_FRACTION = 1.3;
  const HARD_AREA_FRACTION_STEP = 0.12;
  // Rounding/clamping can shrink the realized area; redraw until the total
  // is at least this multiple of the bin area (strictly > 1 => can't all fit).
  const HARD_MIN_OVERFILL = 1.1;
  const HARD_MAX_ATTEMPTS = 50;

  function binSizeForDifficulty(difficulty, baseW = BIN_WIDTH, baseH = BIN_HEIGHT) {
    const scale = 1 + (difficulty - 1) * BIN_GROWTH_STEP;
    return [Math.max(baseW, pyRound(baseW * scale)), Math.max(baseH, pyRound(baseH * scale))];
  }

  function challengeItemCount(difficulty) {
    return Math.max(1, pyRound(CHALLENGE_ITEM_COUNT_BASE * CHALLENGE_ITEM_COUNT_GROWTH ** (difficulty - 1)));
  }

  // Profit color gradient: pale yellow (low profit) -> deep red (high profit).
  const COLOR_LOW = [0xff, 0xf3, 0xb0];
  const COLOR_HIGH = [0xb3, 0x26, 0x1e];

  function profitColor(value, vmin, vmax) {
    let t = vmax <= vmin ? 0.5 : (value - vmin) / (vmax - vmin);
    t = Math.max(0.0, Math.min(1.0, t));
    return (
      "#" +
      [0, 1, 2]
        .map((c) => pyRound(COLOR_LOW[c] + t * (COLOR_HIGH[c] - COLOR_LOW[c])).toString(16).padStart(2, "0"))
        .join("")
    );
  }

  /** Item: {id, w, h, profit, color}. areaFraction overrides the
   * difficulty-based target (used by hard mode only; Challenge instances
   * keep the default so seeds stay reproducible). */
  function generateItems(difficulty, rng, binW = BIN_WIDTH, binH = BIN_HEIGHT, n = null, areaFraction = null) {
    const binArea = binW * binH;
    if (n === null) n = Math.max(1, pyRound(BASE_ITEM_COUNT + (difficulty - 1) * ITEM_COUNT_STEP));
    if (areaFraction === null) areaFraction = BASE_AREA_FRACTION + (difficulty - 1) * AREA_FRACTION_STEP;
    const targetArea = binArea * areaFraction;
    const avgItemArea = targetArea / n;
    const variance = BASE_VARIANCE + VARIANCE_STEP * (difficulty - 1);

    const raw = [];
    for (let i = 0; i < n; i++) {
      let area = rng.normalvariate(avgItemArea, avgItemArea * variance);
      area = Math.max(2, Math.min(area, binArea * 0.35));
      const aspect = rng.uniform(0.4, 2.5);
      let w = Math.sqrt(area * aspect);
      let h = area / w;
      w = Math.trunc(Math.max(1, Math.min(binW, pyRound(w))));
      h = Math.trunc(Math.max(1, Math.min(binH, pyRound(h))));
      // Profit is loosely tied to area but with enough spread that
      // "biggest first" and "best value first" are different strategies.
      const profit = Math.max(1, pyRound(w * h * rng.uniform(0.6, 2.4)));
      raw.push([w, h, profit]);
    }

    const profits = raw.map((r) => r[2]);
    const vmin = Math.min(...profits);
    const vmax = Math.max(...profits);
    return raw.map(([w, h, profit], id) => ({ id, w, h, profit, color: profitColor(profit, vmin, vmax) }));
  }

  /** Instance: {id, bin_w, bin_h, items}. The bin scales with difficulty. */
  function generateInstance(instanceId, difficulty, rng) {
    const [binW, binH] = binSizeForDifficulty(difficulty);
    const items = generateItems(difficulty, rng, binW, binH, challengeItemCount(difficulty));
    return { id: instanceId, bin_w: binW, bin_h: binH, items };
  }

  /** Reproducible from (seed, difficulty, nInstances) alone. */
  function generateInstances(seed, difficulty, nInstances) {
    const rng = new MG.PyRandom(seed);
    const out = [];
    for (let i = 0; i < nInstances; i++) out.push(generateInstance(i + 1, difficulty, rng));
    return out;
  }

  const totalArea = (items) => items.reduce((s, it) => s + it.w * it.h, 0);

  /** Hard-mode items: total area always exceeds the bin, so not all fit. */
  function generateHardItems(roundIdx, rng) {
    const binArea = HARD_BIN_WIDTH * HARD_BIN_HEIGHT;
    const n = HARD_BASE_ITEM_COUNT + (roundIdx - 1) * HARD_ITEM_COUNT_STEP;
    const fraction = HARD_BASE_AREA_FRACTION + (roundIdx - 1) * HARD_AREA_FRACTION_STEP;
    let items;
    for (let attempt = 0; attempt < HARD_MAX_ATTEMPTS; attempt++) {
      items = generateItems(roundIdx, rng, HARD_BIN_WIDTH, HARD_BIN_HEIGHT, n, fraction);
      if (totalArea(items) >= binArea * HARD_MIN_OVERFILL) return items;
    }
    return items; // practically unreachable with these parameters
  }

  /** Game-mode round. Difficulty == roundIdx (1-5), fixed bin per mode. */
  function generateRound(roundIdx, rng, hard = false) {
    const items = hard ? generateHardItems(roundIdx, rng) : generateItems(roundIdx, rng);
    return {
      round_idx: roundIdx, hard,
      bin_w: hard ? HARD_BIN_WIDTH : BIN_WIDTH, bin_h: hard ? HARD_BIN_HEIGHT : BIN_HEIGHT,
      items: items.slice(), // not yet placed
      all_items: items, // full original set, never mutated
      placed: [], // {item, x, y, rotated}
      start_time: null,
    };
  }

  // Placed item footprint (rotation swaps width/height).
  const placedW = (p) => (p.rotated ? p.item.h : p.item.w);
  const placedH = (p) => (p.rotated ? p.item.w : p.item.h);

  function rectsOverlap(x1, y1, w1, h1, x2, y2, w2, h2) {
    return !(x1 + w1 <= x2 || x2 + w2 <= x1 || y1 + h1 <= y2 || y2 + h2 <= y1);
  }

  /** Placement is unconditional — feasibility is only checked at round end. */
  function placeItem(rs, item, x, y, rotated) {
    rs.placed.push({ item, x, y, rotated });
    rs.items = rs.items.filter((it) => it.id !== item.id);
  }

  function movePlacedItem(rs, itemId, x, y, rotated) {
    const p = rs.placed.find((q) => q.item.id === itemId);
    if (p) Object.assign(p, { x, y, rotated });
  }

  function removePlacedItem(rs, itemId) {
    const idx = rs.placed.findIndex((q) => q.item.id === itemId);
    if (idx >= 0) {
      const [p] = rs.placed.splice(idx, 1);
      rs.items.push(p.item);
    }
  }

  function isFeasible(rs) {
    const placed = rs.placed;
    for (const p of placed) {
      if (p.x < 0 || p.y < 0 || p.x + placedW(p) > rs.bin_w || p.y + placedH(p) > rs.bin_h) return false;
    }
    for (let i = 0; i < placed.length; i++) {
      for (let j = i + 1; j < placed.length; j++) {
        const a = placed[i];
        const b = placed[j];
        if (rectsOverlap(a.x, a.y, placedW(a), placedH(a), b.x, b.y, placedW(b), placedH(b))) return false;
      }
    }
    return true;
  }

  function computeUtilization(rs) {
    const packed = rs.placed.reduce((s, p) => s + placedW(p) * placedH(p), 0);
    return Math.min(100.0, (100.0 * packed) / (rs.bin_w * rs.bin_h));
  }

  function computeProfit(rs) {
    return rs.placed.reduce((s, p) => s + p.item.profit, 0);
  }

  BP.game = {
    BIN_WIDTH, BIN_HEIGHT, HARD_BIN_WIDTH, HARD_BIN_HEIGHT,
    binSizeForDifficulty, totalArea, challengeItemCount, profitColor,
    generateItems, generateInstance, generateInstances, generateRound,
    placedW, placedH, rectsOverlap,
    placeItem, movePlacedItem, removePlacedItem,
    isFeasible, computeUtilization, computeProfit,
  };
})();
