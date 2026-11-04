import os
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "GA_WordGame_App"))

import game_logic as gl


def test_seeding_is_reproducible():
    print("1. Same code -> identical initial populations...")
    rng_a = gl.make_rng("CLASS01")
    rng_b = gl.make_rng("class01")  # case-insensitive
    pop_a = gl.random_population(6, 6, rng_a)
    pop_b = gl.random_population(6, 6, rng_b)
    assert pop_a == pop_b
    print("   - Reproducible across case and repeated calls.")

    print("2. Different code -> different populations...")
    rng_c = gl.make_rng("CLASS02")
    pop_c = gl.random_population(6, 6, rng_c)
    assert pop_c != pop_a
    print("   - Distinct seeds diverge as expected.")

    print("3. Blank code -> unpredictable (not reproducible on purpose)...")
    rng_d1 = gl.make_rng("")
    rng_d2 = gl.make_rng("")
    pop_d1 = gl.random_population(6, 6, rng_d1)
    pop_d2 = gl.random_population(6, 6, rng_d2)
    assert pop_d1 != pop_d2  # astronomically unlikely to collide by chance
    print("   - Blank code yields independent random populations.")


def test_clean_hidden_word():
    print("4. clean_hidden_word strips non-letters and uppercases...")
    assert gl.clean_hidden_word("planet") == "PLANET"
    assert gl.clean_hidden_word(" Pla-Net9! ") == "PLANET"
    assert gl.clean_hidden_word("") == ""
    print("   - Matches expected cleaning behavior.")


def test_fitness_counts_position_matches_only():
    print("5. fitness counts letters correct AND in position (slide's example)...")
    assert gl.fitness("PLANET", "PLANET") == 6
    assert gl.fitness("PLAZET", "PLANET") == 5  # matches the slide's worked example
    assert gl.fitness("TENALP", "PLANET") == 0  # right letters, all wrong positions
    print("   - Matches the slide's worked example exactly.")


def test_crossover_swaps_tails_and_preserves_length():
    print("6. crossover produces complementary children of the same length...")
    a, b = "AAAAAA", "BBBBBB"
    c1, c2 = gl.crossover(a, b, 2)
    assert c1 == "AABBBB"
    assert c2 == "BBAAAA"
    assert len(c1) == len(c2) == len(a)
    print(f"   - cut=2 -> child1={c1}, child2={c2}.")

    print("7. Every crossover cut point is reachable and reversible...")
    for cut in range(1, len(a)):
        c1, c2 = gl.crossover(a, b, cut)
        # Swapping the same cut again on the children recovers the original parents.
        back1, back2 = gl.crossover(c1, c2, cut)
        assert (back1, back2) == (a, b)
    print("   - All cuts round-trip correctly.")


def test_mutate_always_changes_the_letter():
    print("8. mutate always replaces the letter with a *different* one...")
    rng = gl.make_rng("MUTATE-TEST")
    word = "PLANET"
    for pos in range(len(word)):
        mutated = gl.mutate(word, pos, rng)
        assert len(mutated) == len(word)
        assert mutated[pos] != word[pos]
        assert mutated[:pos] + mutated[pos + 1:] == word[:pos] + word[pos + 1:]
    print("   - Every position mutates to a strictly different letter, rest unchanged.")


def test_population_stats():
    print("9. population_stats reports best/avg fitness correctly...")
    words = ["PLANET", "PLAZET", "ZZZZZZ"]
    hidden = "PLANET"
    stats = gl.population_stats(words, hidden)
    assert stats["fits"] == [6, 5, 0]
    assert stats["best"] == 6
    assert abs(stats["avg"] - (6 + 5 + 0) / 3) < 1e-9
    print(f"   - best={stats['best']}, avg={stats['avg']:.2f} as expected.")


def test_random_individual_and_population_shapes():
    print("10. random_individual/random_population respect length and alphabet...")
    rng = gl.make_rng("SHAPES")
    ind = gl.random_individual(8, rng)
    assert len(ind) == 8
    assert all(c in gl.ALPHABET for c in ind)

    pop = gl.random_population(6, 6, rng)
    assert len(pop) == 6
    assert all(len(w) == 6 for w in pop)
    print("   - Lengths and alphabet constraints hold.")


def test_letter_closeness():
    print("11. letter_closeness is 1.0 on a match, 0.0 on the worst mismatch...")
    assert gl.letter_closeness("A", "A") == 1.0
    assert gl.letter_closeness("A", "Z") == 0.0
    assert gl.letter_closeness("Z", "A") == 0.0
    print("   - Exact match and A<->Z extremes confirmed.")

    print("12. letter_closeness decreases smoothly with alphabet distance...")
    close = gl.letter_closeness("A", "B")   # distance 1
    far = gl.letter_closeness("A", "M")     # distance 12
    assert 0.0 < far < close < 1.0
    assert abs(close - (1 - 1 / 25)) < 1e-9
    print(f"   - closeness(A,B)={close:.3f} > closeness(A,M)={far:.3f}, both strictly between 0 and 1.")


def test_fitness_partial_matches_only_on_perfect_word():
    print("13. fitness_partial: a near-miss (shifted letters) still scores above 0...")
    exact = gl.fitness("TENALP", "PLANET")  # all letters right, all positions wrong
    partial = gl.fitness_partial("TENALP", "PLANET")
    assert exact == 0
    assert partial > 0
    print(f"   - exact fitness={exact}, partial fitness={partial:.2f} (rewards near letters where exact gives nothing).")

    print("14. fitness_partial only reaches len(hidden) on a perfect match...")
    hidden = "PLANET"
    assert gl.fitness_partial(hidden, hidden) == len(hidden)
    for candidate in ["PLAZET", "ZZZZZZ", "QLANET"]:
        assert gl.fitness_partial(candidate, hidden) < len(hidden)
    print("   - Only the exact word sums to a full score; every mismatch scores strictly less.")


def test_compute_fitness_dispatches_by_mode():
    print("15. compute_fitness dispatches to the right scoring function...")
    word, hidden = "PLAZET", "PLANET"
    assert gl.compute_fitness(word, hidden, "exact") == float(gl.fitness(word, hidden))
    assert gl.compute_fitness(word, hidden, "partial") == gl.fitness_partial(word, hidden)
    assert gl.compute_fitness(word, hidden) == gl.compute_fitness(word, hidden, "exact")  # default mode
    print("   - 'exact' and 'partial' modes match their dedicated functions; default is 'exact'.")


def test_population_stats_supports_partial_mode():
    print("16. population_stats accepts a scoring mode and stays consistent with compute_fitness...")
    words = ["PLANET", "TENALP", "ZZZZZZ"]
    hidden = "PLANET"
    stats = gl.population_stats(words, hidden, mode="partial")
    expected = [gl.compute_fitness(w, hidden, "partial") for w in words]
    assert stats["fits"] == expected
    assert stats["best"] == max(expected)
    print(f"   - partial-mode stats match compute_fitness for each word: {[round(f, 2) for f in expected]}.")


def test_auto_run_generation_shapes_and_determinism():
    print("17. auto_run_generation returns correctly-sized offspring and next population...")
    hidden = "PLANET"
    rng = gl.make_rng("AUTOPLAY")
    population = gl.random_population(6, len(hidden), rng)
    result = gl.auto_run_generation(population, hidden, pop_size=6, mode="exact", rng=rng)
    assert len(result["offspring"]) == 6  # pop_size // 2 pairs -> 2 children each
    assert len(result["population"]) == 6
    assert all(len(w) == len(hidden) for w in result["population"])
    assert all(set(w) <= set(gl.ALPHABET) for w in result["population"])
    print(f"   - offspring pool size={len(result['offspring'])}, next population size={len(result['population'])}.")

    print("18. auto_run_generation is deterministic for a given rng state...")
    rng_a = gl.make_rng("REPLAY")
    pop_a = gl.random_population(6, len(hidden), rng_a)
    result_a = gl.auto_run_generation(pop_a, hidden, pop_size=6, mode="exact", rng=rng_a)

    rng_b = gl.make_rng("REPLAY")
    pop_b = gl.random_population(6, len(hidden), rng_b)
    result_b = gl.auto_run_generation(pop_b, hidden, pop_size=6, mode="exact", rng=rng_b)
    assert result_a["population"] == result_b["population"]
    print("   - Same seeded rng -> identical next generation.")


def test_auto_run_generation_never_loses_the_best_individual():
    print("19. auto_run_generation's elitist selection never drops the best-known individual...")
    hidden = "PLANET"
    rng = gl.make_rng("ELITISM-CHECK")
    for _ in range(20):
        population = gl.random_population(6, len(hidden), rng)
        result = gl.auto_run_generation(population, hidden, pop_size=6, mode="exact", rng=rng)
        best_before = max(gl.compute_fitness(w, hidden) for w in population + [o["word"] for o in result["offspring"]])
        best_after = max(gl.compute_fitness(w, hidden) for w in result["population"])
        assert best_after == best_before
    print("   - Best fitness never regresses across 20 sampled generations.")


if __name__ == "__main__":
    test_seeding_is_reproducible()
    test_clean_hidden_word()
    test_fitness_counts_position_matches_only()
    test_crossover_swaps_tails_and_preserves_length()
    test_mutate_always_changes_the_letter()
    test_population_stats()
    test_random_individual_and_population_shapes()
    test_letter_closeness()
    test_fitness_partial_matches_only_on_perfect_word()
    test_compute_fitness_dispatches_by_mode()
    test_population_stats_supports_partial_mode()
    test_auto_run_generation_shapes_and_determinism()
    test_auto_run_generation_never_loses_the_best_individual()
    print("\nAll game_logic tests passed.")
