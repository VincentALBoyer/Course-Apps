/* Pure game logic for Tabu Search: The Grid Game. Port of
 * TabuSearch_GridGame_App/game_logic.py — grids come from MG.PyRandom (an
 * exact port of Python's random.Random), so a game code gives the same grid
 * as the Streamlit app.
 *
 * Find a connected path of cells that maximizes the sum of its values, then
 * improve it with swap moves: take one cell out, put one cell in. A swap is
 * a neighbor whenever the resulting cells can still be walked as a single
 * connected path (the sum only depends on which cells are in it). Each
 * neighbor is labeled by how the path changes:
 *   - replace: the new cell takes the old one's place in the order;
 *   - shift: drop the head or tail and grow the path from the other end;
 *   - re-route: anything else (the path is re-ordered to stay connected).
 * (The Streamlit original only offered replace and shift, which missed
 * roughly half of the valid swaps, e.g. a new cell linking tail to head.)
 *
 * Tabu memory: each accepted move ages every entry by one, then forbids the
 * cell it removed for `tenure` moves, using the tenure in force when the
 * move is confirmed. A tenure change therefore starts with the very next
 * move, and the list visibly builds up one move at a time. Aspiration lets a
 * tabu move through anyway if it would beat the best solution found so far.
 *
 * Cells are [row, col] arrays; Maps/Sets key them as "r,c".
 */
(function () {
  "use strict";
  const TS = (globalThis.TS = globalThis.TS || {});

  const GRID_VALUE_MIN = 1;
  const GRID_VALUE_MAX = 9;
  const DIFFICULTIES = {
    easy: { label: "Easy", grid_size: 6, path_length: 5, blurb: "6×6 grid · path of 5 cells" },
    medium: { label: "Medium", grid_size: 9, path_length: 7, blurb: "9×9 grid · path of 7 cells" },
    hard: { label: "Hard", grid_size: 13, path_length: 10, blurb: "13×13 grid · path of 10 cells — brute force is impractical here" },
  };
  const DIFFICULTY_ORDER = ["easy", "medium", "hard"];
  const MAX_TENURE = 8; // deliberately allowed to exceed most path lengths, so deadlock is reachable
  const MAX_AUTOPLAY_ITERATIONS = 30;

  const key = (cell) => cell[0] + "," + cell[1];
  const same = (a, b) => a[0] === b[0] && a[1] === b[1];
  const pathKey = (path) => path.map(key).join(";");
  const inPath = (path, cell) => path.some((p) => same(p, cell));

  /** Seed from a share code (a random code if blank) — returns {code, seed}. */
  function resolveCode(code) {
    const c = String(code || "").trim() || MG.newGameCode();
    return { code: c.toUpperCase(), seed: MG.codeToSeed(c) };
  }

  function generateGrid(size, rng) {
    const g = [];
    for (let r = 0; r < size; r++) {
      const row = [];
      for (let c = 0; c < size; c++) row.push(rng.randint(GRID_VALUE_MIN, GRID_VALUE_MAX));
      g.push(row);
    }
    return g;
  }

  const inBounds = (r, c, size) => r >= 0 && r < size && c >= 0 && c < size;

  /** Up/down/left/right in-bounds neighbors (no diagonals). */
  function neighbors4([r, c], size) {
    return [[r - 1, c], [r + 1, c], [r, c - 1], [r, c + 1]].filter(([a, b]) => inBounds(a, b, size));
  }

  const isAdjacent = (a, b) => Math.abs(a[0] - b[0]) + Math.abs(a[1] - b[1]) === 1;
  const pathSum = (grid, path) => path.reduce((s, [r, c]) => s + grid[r][c], 0);

  /** Cells clickable while building the initial path. */
  function availableNextCells(size, path) {
    if (!path.length) {
      const all = [];
      for (let r = 0; r < size; r++) for (let c = 0; c < size; c++) all.push([r, c]);
      return all;
    }
    return neighbors4(path[path.length - 1], size).filter((n) => !inPath(path, n));
  }

  function swapIsFeasible(path, pos, cell) {
    if (same(cell, path[pos]) || inPath(path, cell)) return false;
    if (pos > 0 && !isAdjacent(path[pos - 1], cell)) return false;
    if (pos < path.length - 1 && !isAdjacent(path[pos + 1], cell)) return false;
    return true;
  }

  function applySwap(path, pos, cell) {
    const p = path.slice();
    p[pos] = cell;
    return p;
  }

  function shiftIsFeasible(path, pos, cell) {
    if (pos !== 0 && pos !== path.length - 1) return false;
    if (inPath(path, cell)) return false;
    const anchor = pos === 0 ? path[path.length - 1] : path[0];
    return isAdjacent(anchor, cell);
  }

  /** pos=0: drop the head, append after the tail; pos=last: drop the tail, prepend. */
  const applyShift = (path, pos, cell) => (pos === 0 ? path.slice(1).concat([cell]) : [cell].concat(path.slice(0, -1)));

  /** An order that walks every cell in `cells` as one 4-connected path, or
   * null. Tries starting points in the given order (cells are passed in old
   * path order, so the result stays close to the previous path). */
  function hamiltonianPath(cells) {
    const n = cells.length;
    const index = new Map(cells.map((c, i) => [key(c), i]));
    const adj = cells.map((c) => neighbors4(c, Infinity).map((m) => index.get(key(m))).filter((i) => i !== undefined));
    const order = [];
    const used = new Array(n).fill(false);
    const dfs = (i) => {
      used[i] = true; order.push(i);
      if (order.length === n) return true;
      for (const j of adj[i]) if (!used[j] && dfs(j)) return true;
      used[i] = false; order.pop();
      return false;
    };
    // Only cells with at most one neighbor can't be in the middle; if any
    // exist, a path must start at one of them.
    const ends = cells.map((_, i) => i).filter((i) => adj[i].length <= 1);
    if (ends.length > 2) return null;
    const starts = ends.length ? ends : cells.map((_, i) => i);
    for (const s of starts) if (dfs(s)) return order.map((i) => cells[i]);
    return null;
  }

  /** The move that swaps path[pos] out for `cell`, or null if the result
   * can't be walked as one connected path: {type, new_path}. */
  function moveFor(path, pos, cell) {
    if (inPath(path, cell)) return null;
    if (swapIsFeasible(path, pos, cell)) return { type: "replace", new_path: applySwap(path, pos, cell) };
    if (shiftIsFeasible(path, pos, cell)) return { type: "shift", new_path: applyShift(path, pos, cell) };
    const rest = path.filter((_, i) => i !== pos);
    if (!rest.some((p) => isAdjacent(p, cell))) return null; // can't even touch the path
    const walk = hamiltonianPath(rest.concat([cell]));
    return walk ? { type: "reroute", new_path: walk } : null;
  }

  /** One accepted move: age every tabu entry (dropping expired ones), forget
   * the cell that just came back in, then forbid the removed cell for
   * `tenure` moves (tenure 0 adds nothing). tabu: key -> {rem, inCell}. */
  function advanceTabu(tabu, tenure, outCell, inCell) {
    const updated = new Map();
    for (const [k, e] of tabu) if (e.rem - 1 > 0) updated.set(k, { rem: e.rem - 1, inCell: e.inCell });
    updated.delete(key(inCell));
    if (tenure > 0) updated.set(key(outCell), { rem: tenure, inCell });
    return updated;
  }

  /** key -> moves remaining, the form scoreCandidate expects. */
  const tabuRemaining = (tabu) => new Map([...tabu].map(([k, e]) => [k, e.rem]));

  function scoreCandidate(grid, path, pos, cell, tabuRem, bestSum, move = moveFor(path, pos, cell)) {
    const outCell = path[pos];
    const newPath = move.new_path;
    const newSum = pathSum(grid, newPath);
    const delta = newSum - pathSum(grid, path);
    const tabu = (tabuRem.get(key(cell)) || 0) > 0;
    const aspiration = tabu && newSum > bestSum;
    return {
      pos, out_cell: outCell, in_cell: cell, move_type: move.type, new_path: newPath,
      new_sum: newSum, delta, tabu, aspiration, admissible: !tabu || aspiration,
    };
  }

  /** Refresh tabu/aspiration flags (e.g. after a tenure change). */
  function rescore(cand, tabuRem, bestSum) {
    const tabu = (tabuRem.get(key(cand.in_cell)) || 0) > 0;
    const aspiration = tabu && cand.new_sum > bestSum;
    return Object.assign(cand, { tabu, aspiration, admissible: !tabu || aspiration });
  }

  /** Every feasible (position, cell) swap, best delta first. */
  function enumerateNeighborhood(grid, path, tabuRem, bestSum) {
    const size = grid.length;
    const out = [];
    for (let pos = 0; pos < path.length; pos++) {
      for (let r = 0; r < size; r++) {
        for (let c = 0; c < size; c++) {
          const cell = [r, c];
          const move = moveFor(path, pos, cell);
          if (move) out.push(scoreCandidate(grid, path, pos, cell, tabuRem, bestSum, move));
        }
      }
    }
    out.sort((a, b) => b.delta - a.delta); // stable
    return out;
  }

  /** Best admissible candidate (first maximum), or null on deadlock. */
  function pickBestAdmissible(cands) {
    let best = null;
    for (const c of cands) if (c.admissible && (best === null || c.delta > best.delta)) best = c;
    return best;
  }

  /** Rough upper bound on simple paths of this length (order of magnitude). */
  function estimateMaxPaths(gridSize, pathLength) {
    const cells = gridSize * gridSize;
    if (pathLength <= 1) return cells;
    let est = cells * 4;
    for (let i = 0; i < pathLength - 2; i++) est *= 3;
    return est;
  }

  TS.logic = {
    DIFFICULTIES, DIFFICULTY_ORDER, MAX_TENURE, MAX_AUTOPLAY_ITERATIONS,
    key, same, pathKey, inPath, resolveCode, generateGrid, neighbors4, isAdjacent, pathSum,
    availableNextCells, swapIsFeasible, shiftIsFeasible, hamiltonianPath, moveFor, advanceTabu, tabuRemaining,
    scoreCandidate, rescore, enumerateNeighborhood, pickBestAdmissible, estimateMaxPaths,
  };
})();
