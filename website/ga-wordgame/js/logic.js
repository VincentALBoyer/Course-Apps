/* Pure game logic for the GA Word Game. Port of
 * GA_WordGame_App/game_logic.py — every random choice goes through
 * MG.PyRandom (an exact port of Python's random.Random), so a class code
 * gives the same starting population as the Streamlit app.
 *
 * Mirrors the "Genetic Algorithm: The Word Game" in-class activity from
 * IN2041: gene = one letter, chromosome = a candidate word, fitness =
 * letters correct AND in the right position.
 *
 * Candidate words are always plain A–Z (they're built from ALPHABET); only
 * the hidden word may contain other letters, so it's handled as an array
 * of characters for comparisons.
 */
(function () {
  "use strict";
  const GA = (globalThis.GA = globalThis.GA || {});

  const ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
  const MAX_LETTER_DISTANCE = ALPHABET.length - 1; // A<->Z, the worst mismatch
  const POP_SIZE_CHOICES = [4, 6, 8]; // even, so parent pairs divide evenly
  const MIN_WORD_LEN = 4;
  const MAX_WORD_LEN = 8;
  const SCORING_LABELS = { exact: "Exact match (classic)", partial: "Partial credit (alphabet distance)" };
  const MAX_AUTOPLAY_GENERATIONS = 20;

  /** Seeded from `code` if given, otherwise unpredictable. */
  function makeRng(code) {
    const c = String(code || "").trim();
    return c ? new MG.PyRandom(MG.codeToSeed(c)) : new MG.PyRandom(null);
  }

  /** Letters only, uppercased (Python: ch.isalpha() over raw.upper()). */
  function cleanHiddenWord(raw) {
    return Array.from(String(raw).toUpperCase()).filter((ch) => /\p{L}/u.test(ch)).join("");
  }

  const chars = (w) => Array.from(w);

  function randomIndividual(length, rng) {
    let s = "";
    for (let i = 0; i < length; i++) s += rng.choice(ALPHABET);
    return s;
  }

  function randomPopulation(size, length, rng) {
    const out = [];
    for (let i = 0; i < size; i++) out.push(randomIndividual(length, rng));
    return out;
  }

  /** Letters correct AND in the right position. */
  function fitness(word, hidden) {
    const a = chars(word);
    const b = chars(hidden);
    let n = 0;
    for (let i = 0; i < Math.min(a.length, b.length); i++) if (a[i] === b[i]) n++;
    return n;
  }

  /** 1.0 for a match, else alphabet closeness scaled so A vs Z scores 0. */
  function letterCloseness(a, b) {
    if (a === b) return 1.0;
    return 1.0 - Math.abs(a.codePointAt(0) - b.codePointAt(0)) / MAX_LETTER_DISTANCE;
  }

  function fitnessPartial(word, hidden) {
    const a = chars(word);
    const b = chars(hidden);
    const parts = [];
    for (let i = 0; i < Math.min(a.length, b.length); i++) parts.push(letterCloseness(a[i], b[i]));
    return MG.pySum(parts); // Python's sum() is compensated for floats
  }

  const computeFitness = (word, hidden, mode = "exact") => (mode === "partial" ? fitnessPartial(word, hidden) : fitness(word, hidden));

  /** Single-point crossover: child 1 = A[:cut] + B[cut:], child 2 the opposite. */
  const crossover = (a, b, cut) => [a.slice(0, cut) + b.slice(cut), b.slice(0, cut) + a.slice(cut)];

  /** Replace the letter at `position` with a different random letter. */
  function mutate(word, position, rng) {
    const current = word[position];
    const options = Array.from(ALPHABET).filter((c) => c !== current);
    return word.slice(0, position) + rng.choice(options) + word.slice(position + 1);
  }

  function populationStats(words, hidden, mode = "exact") {
    const fits = words.map((w) => computeFitness(w, hidden, mode));
    return { best: Math.max(...fits), avg: MG.pySum(fits) / fits.length, fits };
  }

  /** One full generation with no human input (auto-play): fitness-weighted
   *  parent selection, random single-point crossover, per-gene mutation at
   *  ~1/length odds, then elitist survivor selection (offspring win ties). */
  function autoRunGeneration(population, hidden, popSize, mode, rng) {
    const length = chars(hidden).length;
    const popFits = population.map((w) => computeFitness(w, hidden, mode));
    const weights = popFits.map((f) => f + 1e-6); // avoid an all-zero weight vector

    const offspring = [];
    for (let k = 0; k < Math.floor(popSize / 2); k++) {
      const [pa, pb] = rng.choices(population, weights, 2);
      const cut = rng.randint(1, length - 1);
      for (let child of crossover(pa, pb, cut)) {
        const mutated = [];
        for (let i = 0; i < length; i++) if (rng.random() < 1.0 / length) mutated.push(i);
        for (const pos of mutated) child = mutate(child, pos, rng);
        offspring.push({ word: child, fitness: computeFitness(child, hidden, mode), mutated: new Set(mutated) });
      }
    }

    const candidates = population.map((w, i) => [w, popFits[i], 1]).concat(offspring.map((o) => [o.word, o.fitness, 0]));
    candidates.sort((x, y) => (y[1] - x[1]) || (x[2] - y[2]));
    const next = candidates.slice(0, popSize).map((c) => c[0]);
    next.sort((x, y) => computeFitness(y, hidden, mode) - computeFitness(x, hidden, mode));
    return { offspring, population: next };
  }

  GA.logic = {
    ALPHABET, POP_SIZE_CHOICES, MIN_WORD_LEN, MAX_WORD_LEN, SCORING_LABELS, MAX_AUTOPLAY_GENERATIONS,
    makeRng, cleanHiddenWord, chars, randomPopulation, fitness, computeFitness, crossover, mutate,
    populationStats, autoRunGeneration,
  };
})();
