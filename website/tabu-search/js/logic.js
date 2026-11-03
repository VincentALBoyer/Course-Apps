/* Pure game logic for Tabu Search: The Grid Game. Port of
 * TabuSearch_GridGame_App/game_logic.py — grids come from MG.PyRandom (an
 * exact port of Python's random.Random), so a game code gives the same grid
 * as the Streamlit app.
 *
 * Find a connected path of cells that maximizes the sum of its values, then
 * improve it with swap moves that keep the path connected:
 *   - replace: swap a cell in place (adjacent to its path neighbors);
 *   - shift: at the head or tail only, drop that end and grow the path from
 *     the other end instead.
 * The tabu list forbids re-inserting the cell each accepted move removed,
 * for `tenure` future moves; aspiration lets a tabu move through anyway if
 * it would beat the best solution found so far.
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

  function scoreCandidate(grid, path, pos, cell, tabuRemaining, bestSum, moveType = "replace") {
    const outCell = path[pos];
    const newPath = moveType === "shift" ? applyShift(path, pos, cell) : applySwap(path, pos, cell);
    const newSum = pathSum(grid, newPath);
    const delta = newSum - pathSum(grid, path);
    const tabu = (tabuRemaining.get(key(cell)) || 0) > 0;
    const aspiration = tabu && newSum > bestSum;
    return {
      pos, out_cell: outCell, in_cell: cell, move_type: moveType, new_path: newPath,
      new_sum: newSum, delta, tabu, aspiration, admissible: !tabu || aspiration,
    };
  }

  /** Every feasible (position, cell, move type), best delta first. */
  function enumerateNeighborhood(grid, path, tabuRemaining, bestSum) {
    const size = grid.length;
    const out = [];
    for (let pos = 0; pos < path.length; pos++) {
      for (let r = 0; r < size; r++) {
        for (let c = 0; c < size; c++) {
          const cell = [r, c];
          if (inPath(path, cell)) continue;
          if (swapIsFeasible(path, pos, cell)) out.push(scoreCandidate(grid, path, pos, cell, tabuRemaining, bestSum, "replace"));
          if (shiftIsFeasible(path, pos, cell)) out.push(scoreCandidate(grid, path, pos, cell, tabuRemaining, bestSum, "shift"));
        }
      }
    }
    out.sort((a, b) => b.delta - a.delta); // stable, like Python's sort
    return out;
  }

  /** Age every tabu entry by one move, then forbid re-inserting outCell for
   *  `tenure` moves (tenure 0 never forbids anything). */
  function advanceTabu(tabuRemaining, tenure, outCell) {
    const updated = new Map();
    for (const [k, rem] of tabuRemaining) if (rem - 1 > 0) updated.set(k, rem - 1);
    // Map.set on an existing key keeps its position, like a Python dict.
    if (tenure > 0) updated.set(key(outCell), tenure);
    return updated;
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
    availableNextCells, swapIsFeasible, shiftIsFeasible, scoreCandidate, enumerateNeighborhood,
    advanceTabu, pickBestAdmissible, estimateMaxPaths,
  };
})();
