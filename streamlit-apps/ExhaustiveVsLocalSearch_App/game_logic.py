"""Landscape generation and scoring for the Exhaustive vs. Local Search minigame.

Mirrors the "Exhaustive vs Local Search" illustrative example from IN2041
Session 2: a 1-D discrete function f(x) with a global minimum and a few
local-minima traps. Each round grows the x-axis (more candidate solutions),
echoing the combinatorial-explosion discussion earlier in that session.
"""

import hashlib
import random
import string

import numpy as np

# x ranges from 0..ROUND_XMAX[i] in round i (0-indexed) -> the axis grows each round.
ROUND_XMAX = [10, 15, 20, 25, 30]
# Number of Gaussian "valleys" (potential local optima) carved into each round's landscape.
ROUND_VALLEYS = [2, 2, 3, 3, 4]

BASELINE = 6.0
NOISE_STD = 0.12

QUALITY_WEIGHT = 0.65
EFFICIENCY_WEIGHT = 0.35

# Local search advanced settings, chosen once at game start (see app.py intro).
NEIGHBORHOOD_CHOICES = [1, 2]  # closest neighbors revealed per side of the current position
MAX_RESTARTS_CAP = 5           # upper bound offered for "restarts allowed"


def new_game_code() -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=6))


def code_to_seed(code: str) -> int:
    """Deterministic seed from a share code, so the same code always regenerates
    the same 5 landscapes (for repeatability across players/sessions)."""
    code = (code or "").strip().upper()
    if not code:
        code = new_game_code()
    digest = hashlib.sha256(code.encode("utf-8")).hexdigest()
    return int(digest[:12], 16)


def generate_all_rounds(seed: int) -> list:
    """Returns a list of 5 landscapes (list of floats), one per round, all
    independently derived from a single seed via NumPy's recommended
    SeedSequence spawning so rounds don't correlate with each other."""
    base = np.random.SeedSequence(seed)
    child_seeds = base.spawn(len(ROUND_XMAX))
    return [
        _generate_landscape(np.random.default_rng(child), round_index)
        for round_index, child in enumerate(child_seeds)
    ]


def _generate_landscape(rng: np.random.Generator, round_index: int) -> list:
    xmax = ROUND_XMAX[round_index]
    n_valleys = ROUND_VALLEYS[round_index]
    xs = np.arange(0, xmax + 1, dtype=float)

    centers = rng.uniform(0, xmax, size=n_valleys)
    depths = rng.uniform(3.0, 5.5, size=n_valleys)
    widths = rng.uniform(1.0, 2.2, size=n_valleys)
    # Each valley's dip is combined by MAX (not sum) so nearby/overlapping
    # valleys don't stack and clip into one wide flat-bottomed plateau —
    # every x is shaped by whichever single valley pulls it down the most.
    dips = np.zeros((n_valleys, xs.shape[0]))
    for i, (center, depth, width) in enumerate(zip(centers, depths, widths)):
        dips[i] = depth * np.exp(-((xs - center) ** 2) / (2 * width ** 2))
    y = BASELINE - dips.max(axis=0)

    y += rng.normal(0, NOISE_STD, size=xs.shape)
    y = np.clip(y, 0, None)
    return y.tolist()


def local_minima_indices(ys: list) -> list:
    """Indices where neither existing neighbor is strictly better — i.e. every
    point a local-search run could possibly stop at (includes the global min)."""
    n = len(ys)
    idxs = []
    for i in range(n):
        left_ok = (i == 0) or (ys[i] <= ys[i - 1])
        right_ok = (i == n - 1) or (ys[i] <= ys[i + 1])
        if left_ok and right_ok:
            idxs.append(i)
    return idxs


def is_improving(candidate_y: float, current_y: float) -> bool:
    return candidate_y < current_y


def neighbor_xs(current_x: int, n: int, xmax: int) -> list:
    """The n closest candidate x's on each side of current_x (clipped to
    [0, xmax], excluding current_x itself) - the neighborhood a local-search
    step reveals and can move into. n=1 is the slide's basic left/right
    neighborhood; n=2 widens it to the two closest on each side."""
    lo = max(0, current_x - n)
    hi = min(xmax, current_x + n)
    return [x for x in range(lo, hi + 1) if x != current_x]


def score_round(found_y: float, ys: list, evaluations: int) -> dict:
    """Round score blends solution quality against the true optimum with
    search efficiency (fewer reveals is better), scaled to 1000 points.

    Exhaustive search always evaluates every point (efficiency = 0) but always
    finds the exact optimum (quality = 1), so it scores a fixed
    1000 * QUALITY_WEIGHT points every round. Local search can score higher by
    converging quickly, or lower if it gets trapped in a poor local optimum.
    """
    n_points = len(ys)
    global_min = min(ys)
    global_max = max(ys)
    span = global_max - global_min

    gap = max(0.0, found_y - global_min)
    quality = 1.0 if span <= 1e-9 else max(0.0, 1.0 - gap / span)
    efficiency = max(0.0, 1.0 - evaluations / n_points)

    raw = QUALITY_WEIGHT * quality + EFFICIENCY_WEIGHT * efficiency
    return {
        "score": round(1000 * raw),
        "quality": quality,
        "efficiency": efficiency,
        "gap": gap,
    }
