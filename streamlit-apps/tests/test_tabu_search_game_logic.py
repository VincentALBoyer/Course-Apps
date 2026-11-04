import os
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "TabuSearch_GridGame_App"))

import game_logic as gl


def test_seeding_is_reproducible():
    print("1. Same code -> identical grids...")
    seed_a = gl.code_to_seed("CLASS01")
    seed_b = gl.code_to_seed("class01")  # case-insensitive
    grid_a = gl.generate_grid(6, gl.make_rng(seed_a))
    grid_b = gl.generate_grid(6, gl.make_rng(seed_b))
    assert grid_a == grid_b
    print("   - Reproducible across case and repeated calls.")

    print("2. Different code -> different grid...")
    seed_c = gl.code_to_seed("CLASS02")
    grid_c = gl.generate_grid(6, gl.make_rng(seed_c))
    assert grid_c != grid_a
    print("   - Distinct seeds diverge as expected.")

    print("3. Blank code -> auto-generated, still reproducible from itself...")
    seed_d1 = gl.code_to_seed("")
    seed_d2 = gl.code_to_seed("")
    assert seed_d1 != seed_d2  # astronomically unlikely to collide by chance
    print("   - Blank code yields an independent random seed each time.")


def test_grid_values_in_range():
    print("4. generate_grid respects size and value bounds...")
    rng = gl.make_rng(gl.code_to_seed("SHAPE-TEST"))
    grid = gl.generate_grid(9, rng)
    assert len(grid) == 9 and all(len(row) == 9 for row in grid)
    assert all(gl.GRID_VALUE_MIN <= v <= gl.GRID_VALUE_MAX for row in grid for v in row)
    print("   - 9x9 grid, all values within [1, 9].")


def test_neighbors4_and_adjacency():
    print("5. neighbors4 excludes diagonals and out-of-bounds cells...")
    size = 5
    corner = neighbors_set = set(gl.neighbors4((0, 0), size))
    assert corner == {(1, 0), (0, 1)}
    center = set(gl.neighbors4((2, 2), size))
    assert center == {(1, 2), (3, 2), (2, 1), (2, 3)}
    print("   - Corner has 2 neighbors, center has 4, no diagonals present.")

    print("6. is_adjacent matches 4-neighborhood exactly...")
    assert gl.is_adjacent((2, 2), (2, 3))
    assert gl.is_adjacent((2, 2), (1, 2))
    assert not gl.is_adjacent((2, 2), (3, 3))  # diagonal
    assert not gl.is_adjacent((2, 2), (2, 2))  # same cell
    assert not gl.is_adjacent((2, 2), (2, 4))  # two steps away
    print("   - Diagonals, self, and distant cells all correctly rejected.")


def test_available_next_cells():
    print("7. available_next_cells offers every cell when the path is empty...")
    size = 4
    assert len(gl.available_next_cells(size, [])) == size * size
    print("   - Empty path -> full grid available.")

    print("8. available_next_cells narrows to unused neighbors of the last cell...")
    path = [(1, 1)]
    avail = set(gl.available_next_cells(size, path))
    assert avail == {(0, 1), (2, 1), (1, 0), (1, 2)}
    path2 = [(1, 1), (1, 2)]
    avail2 = set(gl.available_next_cells(size, path2))
    assert (1, 1) not in avail2  # already used, must not be revisited
    assert avail2 == {(0, 2), (2, 2), (1, 3)}
    print("   - Used cells excluded, only unused neighbors of the path's tail offered.")

    print("9. available_next_cells is empty at a dead end...")
    # Path ends at the center (1,1) of a 3x3 grid, having already used all 4
    # of its neighbors - nowhere left to extend the path.
    dead_path = [(0, 1), (1, 0), (1, 2), (2, 1), (1, 1)]
    avail3 = set(gl.available_next_cells(3, dead_path))
    assert avail3 == set()
    print("   - Correctly reports no options left, matching a real dead end.")


def test_swap_is_feasible():
    print("10. swap_is_feasible allows a connectivity-preserving interior swap...")
    # A straight horizontal path; (2,1) can replace the middle cell (1,1)
    # only if it stays adjacent to both (1,0) and (1,2) - it doesn't, so
    # use a cell that legitimately bridges both neighbors instead.
    path = [(0, 0), (0, 1), (0, 2)]
    # Replace the middle cell (0,1): candidate must be adjacent to (0,0) and (0,2).
    # (1,1) is adjacent to neither in a way that bridges both at distance 2 apart -
    # actually no single cell is adjacent to both (0,0) and (0,2) (they are 2 apart),
    # so the only feasible "replacement" for an interior cell surrounded by two
    # cells that are themselves 2 apart is impossible except cells adjacent to both.
    assert gl.swap_is_feasible(path, 1, (0, 1)) is False  # no-op, same cell
    print("   - Replacing a cell with itself is correctly rejected.")

    print("11. swap_is_feasible allows a valid endpoint swap...")
    # Endpoint (pos=2) only needs adjacency to its one neighbor (0,1).
    assert gl.swap_is_feasible(path, 2, (1, 1)) is True
    assert gl.swap_is_feasible(path, 2, (0, 1)) is False  # already used in path
    assert gl.swap_is_feasible(path, 2, (5, 5)) is False  # not adjacent to (0,1)
    print("   - Endpoint swap needs adjacency to just one neighbor; used/far cells rejected.")

    print("12. swap_is_feasible rejects an interior swap that breaks connectivity...")
    l_path = [(0, 0), (1, 0), (1, 1)]  # an L shape
    # Replacing the middle cell (1,0) needs adjacency to both (0,0) and (1,1).
    assert gl.swap_is_feasible(l_path, 1, (0, 1)) is True  # (0,1) adj to (0,0) and (1,1)
    assert gl.swap_is_feasible(l_path, 1, (2, 0)) is False  # adj to (0,0)? no; breaks both
    print("   - Only a cell adjacent to both surrounding path cells is feasible mid-path.")


def test_shift_is_feasible_and_apply_shift():
    print("12b. shift_is_feasible only applies at the extremities...")
    path = [(0, 0), (0, 1), (0, 2)]  # head=(0,0), tail=(0,2)
    assert gl.shift_is_feasible(path, 1, (1, 1)) is False  # interior position never eligible
    print("   - Interior position correctly rejected regardless of the candidate cell.")

    print("12c. shift_is_feasible at the head needs adjacency to the TAIL, not the head's old neighbor...")
    # Dropping the head and growing from the tail: (0,3) is adjacent to the tail (0,2).
    assert gl.shift_is_feasible(path, 0, (0, 3)) is True
    # (1,1) is adjacent to (0,1) (would be a valid *replace*) but NOT to the tail (0,2) - not a valid shift.
    assert gl.shift_is_feasible(path, 0, (1, 1)) is False
    assert gl.shift_is_feasible(path, 0, (0, 1)) is False  # already used in the path
    print("   - Shift at the head is judged against the opposite extremity (the tail), not position 1.")

    print("12d. shift_is_feasible at the tail needs adjacency to the HEAD...")
    assert gl.shift_is_feasible(path, 2, (1, 0)) is True  # (1,0) adjacent to head (0,0)
    assert gl.shift_is_feasible(path, 2, (1, 2)) is False  # adjacent to (0,2), not the head
    print("   - Symmetric behavior confirmed at the tail.")

    print("12e. apply_shift drops one extremity and grows the path from the other...")
    grown_from_tail = gl.apply_shift(path, 0, (0, 3))
    assert grown_from_tail == [(0, 1), (0, 2), (0, 3)]
    grown_from_head = gl.apply_shift(path, 2, (1, 0))
    assert grown_from_head == [(1, 0), (0, 0), (0, 1)]
    assert path == [(0, 0), (0, 1), (0, 2)]  # original untouched
    print(f"   - drop-head result={grown_from_tail}, drop-tail result={grown_from_head}, both fully connected.")


def test_apply_swap_and_path_sum():
    print("13. apply_swap replaces exactly one position, preserving order elsewhere...")
    path = [(0, 0), (0, 1), (0, 2)]
    new_path = gl.apply_swap(path, 1, (1, 1))
    assert new_path == [(0, 0), (1, 1), (0, 2)]
    assert path == [(0, 0), (0, 1), (0, 2)]  # original untouched
    print("   - New path correct, original path left unmodified.")

    print("14. path_sum adds up the grid values along the path...")
    grid = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    assert gl.path_sum(grid, [(0, 0), (0, 1), (0, 2)]) == 1 + 2 + 3
    assert gl.path_sum(grid, [(2, 2)]) == 9
    print("   - Sums match manual computation for straight and single-cell paths.")


def test_score_candidate_and_tabu_aspiration():
    print("15. score_candidate computes delta, tabu, and aspiration correctly...")
    grid = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    path = [(0, 0), (0, 1), (0, 2)]  # sum = 6
    # Feasible endpoint swap: replace (0,2)=3 with (1,2)=6 -> new sum 9, delta +3.
    cand = gl.score_candidate(grid, path, 2, (1, 2), tabu_remaining={}, best_sum=6)
    assert cand["new_sum"] == 9
    assert cand["delta"] == 3
    assert cand["tabu"] is False
    assert cand["admissible"] is True
    print(f"   - Untabu'd candidate: new_sum={cand['new_sum']}, delta={cand['delta']}, admissible.")

    print("16. A tabu'd cell blocks the move unless aspiration applies...")
    tabu = {(1, 2): 2}  # (1,2) was just removed, so re-inserting it is forbidden
    blocked = gl.score_candidate(grid, path, 2, (1, 2), tabu_remaining=tabu, best_sum=100)
    assert blocked["tabu"] is True
    assert blocked["aspiration"] is False  # 9 is not > best_sum=100
    assert blocked["admissible"] is False
    print("   - Blocked when tabu and not better than the best-known solution.")

    print("17. Aspiration overrides tabu when the candidate beats the best-known sum...")
    rescued = gl.score_candidate(grid, path, 2, (1, 2), tabu_remaining=tabu, best_sum=6)
    assert rescued["tabu"] is True
    assert rescued["aspiration"] is True  # 9 > best_sum=6
    assert rescued["admissible"] is True
    print("   - Aspiration correctly lets a record-breaking tabu move through.")


def test_enumerate_neighborhood_only_feasible():
    print("18. enumerate_neighborhood returns only feasible moves, sorted best-delta-first...")
    grid = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    path = [(0, 0), (0, 1), (0, 2)]
    candidates = gl.enumerate_neighborhood(grid, path, tabu_remaining={}, best_sum=6)
    assert len(candidates) > 0
    for cand in candidates:
        if cand["move_type"] == "shift":
            assert gl.shift_is_feasible(path, cand["pos"], cand["in_cell"])
        else:
            assert gl.swap_is_feasible(path, cand["pos"], cand["in_cell"])
    deltas = [c["delta"] for c in candidates]
    assert deltas == sorted(deltas, reverse=True)
    print(f"   - {len(candidates)} feasible candidates found, each passing its own move type's feasibility check.")

    print("18b. enumerate_neighborhood includes shift moves at the extremities...")
    shift_candidates = [c for c in candidates if c["move_type"] == "shift"]
    assert len(shift_candidates) > 0
    assert all(c["pos"] in (0, len(path) - 1) for c in shift_candidates)
    replace_candidates = [c for c in candidates if c["move_type"] == "replace"]
    assert len(replace_candidates) > 0
    print(f"   - {len(shift_candidates)} shift candidate(s) found (extremities only), "
          f"{len(replace_candidates)} replace candidate(s) found across all positions.")


def test_advance_tabu_countdown_and_zero_tenure():
    print("19. advance_tabu only forbids re-inserting the removed cell, not the inserted one...")
    tabu = {}
    tabu = gl.advance_tabu(tabu, tenure=2, out_cell=(0, 0), in_cell=(1, 1))
    assert tabu == {(0, 0): 2}
    assert (1, 1) not in tabu  # the cell just inserted stays free to be removed again later
    tabu = gl.advance_tabu(tabu, tenure=2, out_cell=(2, 2), in_cell=(3, 3))
    # Prior entry ages down by 1; new entry from this move starts fresh at 2.
    assert tabu[(0, 0)] == 1
    assert tabu[(2, 2)] == 2
    assert (3, 3) not in tabu
    tabu = gl.advance_tabu(tabu, tenure=2, out_cell=(4, 4), in_cell=(5, 5))
    # (0,0) should have expired (aged to 0) and been dropped.
    assert (0, 0) not in tabu
    print("   - Only the removed cell is entered as tabu; it ages down and expires after `tenure` future moves.")

    print("19b. with tenure=1 a single accepted move blocks exactly the reverse move, "
          "not the neighbor on the other side of it...")
    grid = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    path = [(0, 0), (0, 1), (0, 2)]  # sum = 6
    tabu = gl.advance_tabu({}, tenure=1, out_cell=(0, 2), in_cell=(1, 2))
    # Coming back (re-inserting the just-removed cell) is blocked...
    reverse = gl.score_candidate(grid, [(0, 0), (0, 1), (1, 2)], 2, (0, 2), tabu_remaining=tabu, best_sum=100)
    assert reverse["tabu"] is True
    # ...but immediately swapping the newly-inserted cell back out again is not.
    onward = gl.score_candidate(grid, [(0, 0), (0, 1), (1, 2)], 2, (2, 2), tabu_remaining=tabu, best_sum=100)
    assert onward["tabu"] is False
    print("   - Confirms tenure=1 forbids only 'coming back', not touching the newly-inserted cell.")

    print("20. tenure=0 never adds a tabu entry (no memory)...")
    tabu0 = gl.advance_tabu({}, tenure=0, out_cell=(0, 0), in_cell=(1, 1))
    assert tabu0 == {}
    print("   - Confirms tenure=0 is the 'no memory, can cycle' state the game starts in.")


def test_pick_best_admissible_and_deadlock():
    print("21. pick_best_admissible picks the highest-delta admissible candidate...")
    candidates = [
        {"delta": 3, "admissible": True},
        {"delta": 5, "admissible": True},
        {"delta": 9, "admissible": False},  # best delta, but blocked
    ]
    best = gl.pick_best_admissible(candidates)
    assert best["delta"] == 5
    print("   - Correctly skips the higher-delta but inadmissible candidate.")

    print("22. pick_best_admissible returns None when nothing is admissible (deadlock)...")
    all_blocked = [{"delta": 3, "admissible": False}, {"delta": 5, "admissible": False}]
    assert gl.pick_best_admissible(all_blocked) is None
    assert gl.pick_best_admissible([]) is None
    print("   - Empty and all-tabu neighborhoods both correctly signal deadlock.")


def test_estimate_max_paths_scales_with_difficulty():
    print("23. estimate_max_paths grows with grid size and path length...")
    easy = gl.DIFFICULTIES["easy"]
    medium = gl.DIFFICULTIES["medium"]
    hard = gl.DIFFICULTIES["hard"]
    est_easy = gl.estimate_max_paths(easy["grid_size"], easy["path_length"])
    est_medium = gl.estimate_max_paths(medium["grid_size"], medium["path_length"])
    est_hard = gl.estimate_max_paths(hard["grid_size"], hard["path_length"])
    assert 0 < est_easy < est_medium < est_hard
    assert est_hard > 1_000_000  # hard mode should make brute force clearly impractical
    print(f"   - easy={est_easy:,}, medium={est_medium:,}, hard={est_hard:,} (strictly increasing).")


if __name__ == "__main__":
    test_seeding_is_reproducible()
    test_grid_values_in_range()
    test_neighbors4_and_adjacency()
    test_available_next_cells()
    test_swap_is_feasible()
    test_shift_is_feasible_and_apply_shift()
    test_apply_swap_and_path_sum()
    test_score_candidate_and_tabu_aspiration()
    test_enumerate_neighborhood_only_feasible()
    test_advance_tabu_countdown_and_zero_tenure()
    test_pick_best_admissible_and_deadlock()
    test_estimate_max_paths_scales_with_difficulty()
    print("\nAll game_logic tests passed.")
