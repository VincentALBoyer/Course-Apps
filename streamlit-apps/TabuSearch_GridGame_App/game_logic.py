"""Pure game logic for the Tabu Search Grid Game minigame.

Mirrors the "Tabu Search: The Grid Game" in-class activity from IN2041
(TabuSearch_Game.tex): find a connected path of cells on a grid that
maximizes the sum of its values, then improve it with a swap-based local
search. Two move types, both exchanging one cell IN the current path for
one cell OUT of it while keeping the path connected - the grid-adjacency-
constrained analogues of the slide's "Replace" and "Shift" moves:
  - replace (swap_is_feasible/apply_swap): a cell is swapped in place,
    needing adjacency to whichever path neighbors sit on either side of
    its position.
  - shift (shift_is_feasible/apply_shift): only at an extremity (the head
    or tail) - that end is dropped entirely and the path grows from the
    *other* end instead, needing adjacency there.

A tabu list remembers the cell removed by each accepted move and forbids
re-inserting it for `tenure` future moves - this is what lets a search
escape a local optimum instead of immediately cycling straight back to it.
The cell that was just inserted is not itself restricted; only "coming
back" is tabu. Aspiration overrides the tabu list when a forbidden move
would beat the best solution found so far.

Every random choice (grid generation) is driven by an explicit
random.Random instance so a game can be reproduced from a shared code,
same convention as the other minigames in this repo.
"""

import hashlib
import random
import string

GRID_VALUE_MIN = 1
GRID_VALUE_MAX = 9

# Difficulty presets: grid grows and the required path gets longer, so the
# number of possible paths (see estimate_max_paths) explodes - by "hard" a
# brute-force check of every path is no longer realistic.
DIFFICULTIES = {
    "easy": {
        "label": "Easy",
        "grid_size": 6,
        "path_length": 5,
        "blurb": "6×6 grid · path of 5 cells",
    },
    "medium": {
        "label": "Medium",
        "grid_size": 9,
        "path_length": 7,
        "blurb": "9×9 grid · path of 7 cells",
    },
    "hard": {
        "label": "Hard",
        "grid_size": 13,
        "path_length": 10,
        "blurb": "13×13 grid · path of 10 cells — brute force is impractical here",
    },
}
DIFFICULTY_ORDER = ["easy", "medium", "hard"]

MAX_TENURE = 8  # deliberately allowed to exceed most path lengths, so deadlock is reachable
MAX_AUTOPLAY_ITERATIONS = 30


def new_game_code() -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=6))


def code_to_seed(code: str) -> int:
    """Deterministic seed from a share code (auto-generating one if blank),
    so the same code always regenerates the same grid - lets a class
    compare tabu search runs on an identical board, like the tex's
    side-by-side Team 1 / Team 2 grids."""
    code = (code or "").strip().upper()
    if not code:
        code = new_game_code()
    digest = hashlib.sha256(code.encode("utf-8")).hexdigest()
    return int(digest[:12], 16)


def make_rng(seed: int) -> random.Random:
    return random.Random(seed)


def generate_grid(size: int, rng: random.Random) -> list:
    return [[rng.randint(GRID_VALUE_MIN, GRID_VALUE_MAX) for _ in range(size)] for _ in range(size)]


def in_bounds(r: int, c: int, size: int) -> bool:
    return 0 <= r < size and 0 <= c < size


def neighbors4(cell: tuple, size: int) -> list:
    """Up/down/left/right in-bounds neighbors - no diagonals, matching the
    slide's path rules."""
    r, c = cell
    candidates = [(r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)]
    return [n for n in candidates if in_bounds(n[0], n[1], size)]


def is_adjacent(a: tuple, b: tuple) -> bool:
    return abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1


def path_sum(grid: list, path: list) -> int:
    return sum(grid[r][c] for r, c in path)


def available_next_cells(size: int, path: list) -> list:
    """Cells a student may click next while building the initial path: any
    cell if the path is still empty, otherwise the unused neighbors of the
    last cell placed. Can be empty (a dead end) before path_length is
    reached, even though every cell is distinct and in-bounds."""
    if not path:
        return [(r, c) for r in range(size) for c in range(size)]
    used = set(path)
    return [n for n in neighbors4(path[-1], size) if n not in used]


def swap_is_feasible(path: list, pos: int, new_cell: tuple) -> bool:
    """A swap replaces path[pos] with new_cell. Feasible only if new_cell
    isn't already used elsewhere in the path and the result stays a single
    connected, non-revisiting path - i.e. new_cell must be grid-adjacent to
    whichever path neighbors sit on either side of position `pos`."""
    if new_cell == path[pos] or new_cell in path:
        return False
    if pos > 0 and not is_adjacent(path[pos - 1], new_cell):
        return False
    if pos < len(path) - 1 and not is_adjacent(path[pos + 1], new_cell):
        return False
    return True


def apply_swap(path: list, pos: int, new_cell: tuple) -> list:
    new_path = list(path)
    new_path[pos] = new_cell
    return new_path


def shift_is_feasible(path: list, pos: int, new_cell: tuple) -> bool:
    """The other move at an extremity, matching the slide's "Shift" move:
    drop the head or tail entirely and grow the path from the *opposite*
    end. Only valid when `pos` is an extremity (0 or the last index) -
    new_cell must be adjacent to the OTHER extremity, not the neighbor
    swap_is_feasible would require. The cells between the two extremities
    keep their existing order and adjacencies untouched, so no other check
    is needed."""
    if pos not in (0, len(path) - 1):
        return False
    if new_cell in path:
        return False
    anchor = path[-1] if pos == 0 else path[0]
    return is_adjacent(anchor, new_cell)


def apply_shift(path: list, pos: int, new_cell: tuple) -> list:
    """pos=0: drop the head, append new_cell after the old tail.
    pos=last: drop the tail, prepend new_cell before the old head."""
    if pos == 0:
        return path[1:] + [new_cell]
    return [new_cell] + path[:-1]


def score_candidate(
    grid: list, path: list, pos: int, new_cell: tuple, tabu_remaining: dict, best_sum: int,
    move_type: str = "replace",
) -> dict:
    """Builds one fully-scored candidate move: the resulting path/sum, its
    delta versus the current path, and whether it's blocked by the tabu
    list - or let through anyway by the aspiration criterion because it
    would beat the best solution found so far. Caller must have already
    confirmed swap_is_feasible(path, pos, new_cell) (move_type="replace")
    or shift_is_feasible(path, pos, new_cell) (move_type="shift")."""
    out_cell = path[pos]
    new_path = apply_shift(path, pos, new_cell) if move_type == "shift" else apply_swap(path, pos, new_cell)
    new_sum = path_sum(grid, new_path)
    delta = new_sum - path_sum(grid, path)
    tabu = tabu_remaining.get(new_cell, 0) > 0
    aspiration = tabu and new_sum > best_sum
    return {
        "pos": pos,
        "out_cell": out_cell,
        "in_cell": new_cell,
        "move_type": move_type,
        "new_path": new_path,
        "new_sum": new_sum,
        "delta": delta,
        "tabu": tabu,
        "aspiration": aspiration,
        "admissible": (not tabu) or aspiration,
    }


def enumerate_neighborhood(grid: list, path: list, tabu_remaining: dict, best_sum: int) -> list:
    """The full move neighborhood of `path`: every feasible (position,
    replacement cell, move type) triple, fully scored, best delta first.
    Every position supports "replace"; the two extremities additionally
    support "shift". This is what "auto" neighbor generation reveals in
    one shot - manual mode builds the same kind of entries one clicked
    pair at a time."""
    size = len(grid)
    used = set(path)
    candidates = []
    for pos in range(len(path)):
        for r in range(size):
            for c in range(size):
                cell = (r, c)
                if cell in used:
                    continue
                if swap_is_feasible(path, pos, cell):
                    candidates.append(score_candidate(grid, path, pos, cell, tabu_remaining, best_sum, "replace"))
                if shift_is_feasible(path, pos, cell):
                    candidates.append(score_candidate(grid, path, pos, cell, tabu_remaining, best_sum, "shift"))
    candidates.sort(key=lambda cand: -cand["delta"])
    return candidates


def advance_tabu(tabu_remaining: dict, tenure: int, out_cell: tuple, in_cell: tuple) -> dict:
    """Ages every existing tabu entry down by one move (dropping expired
    ones), then - if tenure > 0 - freshly forbids re-inserting the cell
    just removed (`out_cell`) for the next `tenure` moves, so the search
    can't immediately undo the move it just made. `in_cell` is left free to
    be removed again later - only "coming back" is tabu, not touching the
    cell that just entered the path. tenure=0 never adds anything, so no
    move is ever blocked: exactly the "no memory" state that lets a greedy
    search cycle."""
    updated = {cell: remaining - 1 for cell, remaining in tabu_remaining.items() if remaining - 1 > 0}
    if tenure > 0:
        updated[out_cell] = tenure
    return updated


def pick_best_admissible(candidates: list) -> dict:
    """The move a fully-automatic tabu search step would take: the best
    (highest delta) admissible candidate, or None if every candidate is
    tabu-blocked (or there are no feasible candidates at all) - a
    deadlock."""
    admissible = [c for c in candidates if c["admissible"]]
    if not admissible:
        return None
    return max(admissible, key=lambda c: c["delta"])


def estimate_max_paths(grid_size: int, path_length: int) -> int:
    """A rough upper bound on the number of simple paths of this length in
    this grid: any of the grid_size**2 cells to start, up to 4 directions
    for the second cell, then up to 3 non-backtracking directions per
    remaining step. Ignores self-crossing limits (so it slightly
    overcounts) but conveys the right order of magnitude - the point being
    that it gets astronomically large fast."""
    n_cells = grid_size * grid_size
    if path_length <= 1:
        return n_cells
    estimate = n_cells * 4
    for _ in range(path_length - 2):
        estimate *= 3
    return estimate
