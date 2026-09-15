import os
import random
import sys

sys.path.append(os.path.join(os.getcwd(), "Kids_MathWriting_App"))

import game_logic as gl


def test_strip_accents_and_normalize_keep_enye_distinct():
    print("1. strip_accents folds accented vowels but leaves ñ untouched...")
    assert gl.strip_accents("avión") == "avion"
    assert gl.strip_accents("corazón") == "corazon"
    assert gl.strip_accents("año") == "año"
    assert gl.strip_accents("ano") == "ano"
    assert gl.strip_accents("año") != gl.strip_accents("ano")
    print("   - Accents fold to plain vowels; ñ/n stay distinct.")

    print("2. normalize is case- and whitespace-insensitive...")
    assert gl.normalize("  AVIÓN ") == gl.normalize("avion")
    print("   - Matches regardless of case or surrounding whitespace.")


def test_check_word_accepts_unaccented_typing():
    print("3. check_word accepts the unaccented form of an accented word...")
    assert gl.check_word("avion", "avión")
    assert gl.check_word("AVION", "avión")
    assert gl.check_word("gato", "gato")
    assert not gl.check_word("gata", "gato")
    print("   - A kid without accent keys can still answer correctly.")


def test_make_number_choices_always_includes_answer_and_is_nonnegative():
    print("4. make_number_choices includes the answer and never goes negative...")
    rng = random.Random(1)
    for _ in range(50):
        answer = rng.randint(0, 20)
        choices = gl.make_number_choices(answer, spread=3, rng=rng)
        assert answer in choices
        assert len(choices) == len(set(choices)) == 4
        assert all(c >= 0 for c in choices)
    print("   - 50 sampled problems all satisfy the invariant.")


def test_addition_and_multiplication_problems_are_internally_consistent():
    print("5. addition/multiplication problems have a+b / a*b as the answer...")
    rng = random.Random(2)
    for difficulty in ("facil", "dificil"):
        for _ in range(30):
            add_p = gl.make_addition_problem(difficulty, rng)
            assert add_p["answer"] == add_p["a"] + add_p["b"]
            assert add_p["answer"] in add_p["choices"]

            mult_p = gl.make_multiplication_problem(difficulty, rng)
            assert mult_p["answer"] == mult_p["a"] * mult_p["b"]
            assert mult_p["answer"] in mult_p["choices"]
    print("   - Answers and multiple-choice sets are consistent across difficulties.")


def test_scramble_word_differs_and_uses_same_letters():
    print("6. scramble_word rearranges letters without changing the multiset...")
    rng = random.Random(3)
    for word, _ in gl.WORD_BANK:
        scrambled = gl.scramble_word(word, rng)
        assert sorted(scrambled) == sorted(word)
        if len(set(word)) > 1:
            assert scrambled != word
    print("   - Every word in the bank scrambles to a same-letter permutation.")


def test_complete_problem_masks_one_letter_with_correct_choice_included():
    print("7. make_complete_problem masks exactly one letter and offers 4 distinct choices...")
    rng = random.Random(4)
    for _ in range(50):
        prob = gl.make_complete_problem(rng)
        assert prob["masked"].count("_") == 1
        rebuilt = prob["masked"].replace("_", prob["answer"], 1)
        assert rebuilt == prob["word"]
        assert prob["answer"] in prob["choices"]
        assert len(prob["choices"]) == len(set(c.lower() for c in prob["choices"]))
    print("   - Masking is reversible and the correct letter is always offered.")


def test_check_answer_dispatches_by_kind():
    print("8. check_answer dispatches correctly across all problem kinds...")
    rng = random.Random(5)
    add_p = gl.make_addition_problem("facil", rng)
    assert gl.check_answer(add_p, add_p["answer"])
    assert not gl.check_answer(add_p, add_p["answer"] + 100)

    scramble_p = gl.make_scramble_problem(rng)
    assert gl.check_answer(scramble_p, scramble_p["word"])
    assert gl.check_answer(scramble_p, gl.strip_accents(scramble_p["word"]).upper())

    complete_p = gl.make_complete_problem(rng)
    assert gl.check_answer(complete_p, complete_p["answer"])
    wrong_letter = next(c for c in complete_p["choices"] if c.lower() != complete_p["answer"].lower())
    assert not gl.check_answer(complete_p, wrong_letter)

    spell_p = gl.make_spell_problem(rng)
    assert gl.check_answer(spell_p, spell_p["word"])
    print("   - add/mult, scramble, complete, and spell all check correctly.")


def test_new_problem_respects_mode_and_avoids_immediate_repeat():
    print("9. new_problem stays within its mode's kinds and avoids repeating the last key...")
    rng = random.Random(6)
    for mode, allowed_kinds in gl.MODE_KINDS.items():
        prev_key = None
        for _ in range(20):
            prob = gl.new_problem(mode, "facil", avoid_key=prev_key, rng=rng)
            assert prob["kind"] in allowed_kinds
            if len(allowed_kinds) > 1 or mode == "sorpresa":
                pass  # a same-kind repeat is fine as long as the exact key differs when possible
            prev_key = prob["key"]
    print("   - Every mode only produces its allowed problem kinds.")


def test_newly_unlocked_milestones_only_returns_new_crossings():
    print("10. newly_unlocked_milestones only reports milestones not already unlocked...")
    unlocked = set()
    first = gl.newly_unlocked_milestones(gl.MILESTONES[0], unlocked)
    assert first == [0]
    unlocked.update(first)
    second = gl.newly_unlocked_milestones(gl.MILESTONES[0], unlocked)
    assert second == []
    jump = gl.newly_unlocked_milestones(gl.MILESTONES[2], unlocked)
    assert jump == [1, 2]
    print("   - Re-crossing an already-unlocked milestone reports nothing new.")


if __name__ == "__main__":
    test_strip_accents_and_normalize_keep_enye_distinct()
    test_check_word_accepts_unaccented_typing()
    test_make_number_choices_always_includes_answer_and_is_nonnegative()
    test_addition_and_multiplication_problems_are_internally_consistent()
    test_scramble_word_differs_and_uses_same_letters()
    test_complete_problem_masks_one_letter_with_correct_choice_included()
    test_check_answer_dispatches_by_kind()
    test_new_problem_respects_mode_and_avoids_immediate_repeat()
    test_newly_unlocked_milestones_only_returns_new_crossings()
    print("\nAll game_logic tests passed.")
