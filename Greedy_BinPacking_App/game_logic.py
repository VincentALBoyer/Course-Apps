"""Round/instance generation, placement validation, and scoring for the
2D bin-packing intro game.

No reference greedy algorithm is implemented here on purpose — the whole
point of Game mode is for students to discover their own heuristic without
being anchored to one we hand them."""

import math
import random
from dataclasses import dataclass, field

BIN_WIDTH = 20
BIN_HEIGHT = 14

# Difficulty schedule (1 = easiest). Game mode uses integer levels 1-5 (one
# per round) with a FIXED bin size and a gentle, linear item-count ramp —
# it's a few-minute classroom minigame, so it stays small (~6-15 items).
#
# Challenge/Scoring mode expose a wider 1-10 range and scale much more
# aggressively: the bin itself grows (bin_size_for_difficulty) AND the item
# count grows exponentially (challenge_item_count) so that difficulty 10
# lands in the hundreds of items — genuinely impractical to solve by hand,
# which is the point of an offline/coded challenge instance.
BASE_ITEM_COUNT = 6
ITEM_COUNT_STEP = 2.2
BASE_AREA_FRACTION = 0.70
AREA_FRACTION_STEP = 0.15
BASE_VARIANCE = 0.30
VARIANCE_STEP = 0.15
BIN_GROWTH_STEP = 0.15  # +15% bin width/height per difficulty level above 1
CHALLENGE_ITEM_COUNT_BASE = 6
CHALLENGE_ITEM_COUNT_GROWTH = 1.6  # exponential: ~400+ items by difficulty 10
MIN_DIFFICULTY = 1
MAX_DIFFICULTY = 10


def bin_size_for_difficulty(difficulty: float, base_w: int = BIN_WIDTH, base_h: int = BIN_HEIGHT):
    scale = 1 + (difficulty - 1) * BIN_GROWTH_STEP
    return max(base_w, round(base_w * scale)), max(base_h, round(base_h * scale))


def challenge_item_count(difficulty: float) -> int:
    return max(1, round(CHALLENGE_ITEM_COUNT_BASE * (CHALLENGE_ITEM_COUNT_GROWTH ** (difficulty - 1))))

# Profit color gradient: pale yellow (low profit) -> deep red (high profit).
_COLOR_LOW = (0xFF, 0xF3, 0xB0)
_COLOR_HIGH = (0xB3, 0x26, 0x1E)


def profit_color(value: float, vmin: float, vmax: float) -> str:
    t = 0.5 if vmax <= vmin else (value - vmin) / (vmax - vmin)
    t = max(0.0, min(1.0, t))
    r = round(_COLOR_LOW[0] + t * (_COLOR_HIGH[0] - _COLOR_LOW[0]))
    g = round(_COLOR_LOW[1] + t * (_COLOR_HIGH[1] - _COLOR_LOW[1]))
    b = round(_COLOR_LOW[2] + t * (_COLOR_HIGH[2] - _COLOR_LOW[2]))
    return f"#{r:02x}{g:02x}{b:02x}"


@dataclass
class Item:
    id: int
    w: int
    h: int
    profit: int
    color: str

    @property
    def area(self) -> int:
        return self.w * self.h

    @property
    def density(self) -> float:
        return self.profit / self.area if self.area else 0.0


@dataclass
class PlacedItem:
    item: Item
    x: int
    y: int
    rotated: bool

    @property
    def w(self) -> int:
        return self.item.h if self.rotated else self.item.w

    @property
    def h(self) -> int:
        return self.item.w if self.rotated else self.item.h


@dataclass
class RoundState:
    round_idx: int
    bin_w: int
    bin_h: int
    items: list  # list[Item], not yet placed/skipped
    all_items: list = field(default_factory=list)  # full original set, never mutated
    placed: list = field(default_factory=list)  # list[PlacedItem]
    skipped_ids: set = field(default_factory=set)
    start_time: float = None


@dataclass
class Instance:
    """A static (non-mutable, no play state) problem instance — the unit
    used by Challenge mode (generate + export) and Scoring mode (import +
    grade). A game-mode RoundState is generated from the same item pool."""

    id: int
    bin_w: int
    bin_h: int
    items: list  # list[Item]


def generate_items(
    difficulty: float, rng: random.Random,
    bin_w: int = BIN_WIDTH, bin_h: int = BIN_HEIGHT, n: int = None,
) -> list:
    """Procedurally generate an item set for a given difficulty level
    (total area pressure and size variance increase with difficulty; item
    count too, unless an explicit `n` is given — see challenge_item_count
    for the much steeper curve Challenge/Scoring mode uses)."""
    bin_area = bin_w * bin_h
    if n is None:
        n = max(1, round(BASE_ITEM_COUNT + (difficulty - 1) * ITEM_COUNT_STEP))
    target_area = bin_area * (BASE_AREA_FRACTION + (difficulty - 1) * AREA_FRACTION_STEP)
    avg_item_area = target_area / n
    variance = BASE_VARIANCE + VARIANCE_STEP * (difficulty - 1)

    raw = []  # (w, h, profit) before color assignment
    for _ in range(n):
        area = rng.normalvariate(avg_item_area, avg_item_area * variance)
        area = max(2, min(area, bin_area * 0.35))
        aspect = rng.uniform(0.4, 2.5)
        w = math.sqrt(area * aspect)
        h = area / w
        w = int(max(1, min(bin_w, round(w))))
        h = int(max(1, min(bin_h, round(h))))
        # Profit is loosely tied to area but with enough spread that
        # "biggest first" and "best value first" are different strategies.
        profit = max(1, round(w * h * rng.uniform(0.6, 2.4)))
        raw.append((w, h, profit))

    profits = [p for _, _, p in raw]
    vmin, vmax = min(profits), max(profits)

    return [
        Item(id=i, w=w, h=h, profit=profit, color=profit_color(profit, vmin, vmax))
        for i, (w, h, profit) in enumerate(raw)
    ]


def generate_instance(
    instance_id: int, difficulty: float, rng: random.Random,
    bin_w: int = None, bin_h: int = None,
) -> Instance:
    """Generate one static instance. Unless bin_w/bin_h are given explicitly,
    the bin itself scales up with difficulty (see bin_size_for_difficulty)."""
    if bin_w is None or bin_h is None:
        auto_w, auto_h = bin_size_for_difficulty(difficulty)
        bin_w = auto_w if bin_w is None else bin_w
        bin_h = auto_h if bin_h is None else bin_h
    items = generate_items(difficulty, rng, bin_w, bin_h, n=challenge_item_count(difficulty))
    return Instance(id=instance_id, bin_w=bin_w, bin_h=bin_h, items=items)


def generate_round(round_idx: int, rng: random.Random) -> RoundState:
    """Generate a game-mode round. Difficulty == round_idx (1-5)."""
    items = generate_items(float(round_idx), rng)
    return RoundState(round_idx=round_idx, bin_w=BIN_WIDTH, bin_h=BIN_HEIGHT, items=list(items), all_items=items)


def rects_overlap(x1, y1, w1, h1, x2, y2, w2, h2) -> bool:
    return not (x1 + w1 <= x2 or x2 + w2 <= x1 or y1 + h1 <= y2 or y2 + h2 <= y1)


def place_item(round_state: RoundState, item: Item, x: int, y: int, rotated: bool) -> None:
    """Place an item from the queue into the bin at the given position.

    Placement is unconditional — overlaps and out-of-bounds spots are
    allowed. Feasibility (and therefore scoring) is only checked when the
    round ends, via is_feasible().
    """
    round_state.placed.append(PlacedItem(item=item, x=x, y=y, rotated=rotated))
    round_state.items = [it for it in round_state.items if it.id != item.id]


def move_placed_item(round_state: RoundState, item_id: int, x: int, y: int, rotated: bool) -> None:
    """Reposition an already-placed item (drag within the bin)."""
    for p in round_state.placed:
        if p.item.id == item_id:
            p.x = x
            p.y = y
            p.rotated = rotated
            return


def remove_placed_item(round_state: RoundState, item_id: int) -> None:
    """Pull a placed item back out of the bin and return it to the queue."""
    for p in round_state.placed:
        if p.item.id == item_id:
            round_state.placed.remove(p)
            round_state.items.append(p.item)
            return


def skip_item(round_state: RoundState, item_id: int) -> None:
    round_state.items = [it for it in round_state.items if it.id != item_id]
    round_state.skipped_ids.add(item_id)


def is_feasible(round_state: RoundState) -> bool:
    """True if every placed item is in-bounds and nothing overlaps."""
    placed = round_state.placed
    for p in placed:
        if p.x < 0 or p.y < 0 or p.x + p.w > round_state.bin_w or p.y + p.h > round_state.bin_h:
            return False
    for i in range(len(placed)):
        for j in range(i + 1, len(placed)):
            a, b = placed[i], placed[j]
            if rects_overlap(a.x, a.y, a.w, a.h, b.x, b.y, b.w, b.h):
                return False
    return True


def compute_utilization(round_state: RoundState) -> float:
    packed_area = sum(p.w * p.h for p in round_state.placed)
    bin_area = round_state.bin_w * round_state.bin_h
    return min(100.0, 100.0 * packed_area / bin_area)


def compute_profit(round_state: RoundState) -> int:
    return sum(p.item.profit for p in round_state.placed)
