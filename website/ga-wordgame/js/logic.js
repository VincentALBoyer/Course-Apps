/* Pure game logic for the GA Word Game. Port of
 * GA_WordGame_App/game_logic.py — every random choice goes through
 * MG.PyRandom (an exact port of Python's random.Random), so a class code
 * gives the same starting population as the Streamlit app.
 *
 * Mirrors the "Genetic Algorithm: The Word Game" in-class activity from
 * IN2041: gene = one letter, chromosome = a candidate word, fitness =
 * letters correct AND in the right position.
 *
 * Candidate words and the hidden word are both plain A–Z: the hidden word
 * has its accents stripped (Ñ→N, Á→A) so the game is always winnable.
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

  /** Common English words (4-6 letters, A-Z only) for the 🎲 Random word button. */
  const WORD_BANK = (
    "BIRD BOOK CAKE CITY DOOR FARM FISH GAME GOLD HAND HOME KING LAKE LAMP LION MILK MOON NOTE PARK " +
    "RAIN ROAD ROCK ROSE SALT SHIP SNOW SONG STAR TREE WIND WOLF WOOD BEAR CORN DUCK FROG GIFT HILL " +
    "APPLE BEACH BREAD BRICK CHAIR CLOCK CLOUD DANCE DREAM EARTH FIELD FLAME GHOST GRAPE GRASS HEART " +
    "HORSE HOUSE LEMON LIGHT MAGIC MONEY MUSIC NIGHT OCEAN PAPER PIANO PLANT QUEEN RIVER ROBOT SHEEP " +
    "SMILE SPACE STONE STORM SUGAR TABLE TIGER TOAST TRAIN WATER WHALE WORLD ZEBRA BRAIN CANDY CHESS " +
    "ANIMAL BASKET BRIDGE BUTTER CAMERA CANDLE CASTLE CHEESE CIRCLE COFFEE COOKIE DESERT DINNER DOCTOR " +
    "DRAGON FOREST FLOWER GARDEN GUITAR HAMMER ISLAND JACKET JUNGLE LETTER MARKET MIRROR MONKEY NUMBER " +
    "ORANGE PENCIL PEPPER PLANET POCKET RABBIT ROCKET SCHOOL SILVER SPIDER SPRING SUMMER TICKET TOMATO " +
    "TURTLE WINDOW WINTER YELLOW BUTTON PUZZLE"
  ).split(" ");

  /** A random word from WORD_BANK (not tied to the class code, so it stays secret). */
  const randomWord = () => WORD_BANK[Math.floor(Math.random() * WORD_BANK.length)];

  /** Seeded from `code` if given, otherwise unpredictable. */
  function makeRng(code) {
    const c = String(code || "").trim();
    return c ? new MG.PyRandom(MG.codeToSeed(c)) : new MG.PyRandom(null);
  }

  /** Uppercased, accents stripped (É→E, Ñ→N, Ü→U), then A–Z only, so the
   *  hidden word always uses the same alphabet as the candidates. */
  function cleanHiddenWord(raw) {
    return String(raw).normalize("NFD").replace(/\p{M}/gu, "").toUpperCase().replace(/[^A-Z]/g, "");
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

  // ── operators used by auto mode ──────────────────────────────────────
  const PARENT_METHODS = { random: "Random", roulette: "Roulette wheel", tournament: "Tournament" };
  const SURVIVOR_RULES = { best: "Best of all", offspring: "Offspring only", elitism: "Elitism" };
  const ROULETTE_EPS = 1e-6; // so fitness-0 members (and an all-zero population) still have a slice

  /** Pick one parent index from `fits`, never `exclude` (so the two parents
   *  of a pair differ). Returns the pick plus what's needed to show *why*:
   *  roulette → each slice's share and where the wheel stopped (0..1);
   *  tournament → the contestants drawn. */
  function pickParent(fits, exclude, method, tourK, rng) {
    const pool = fits.map((_, i) => i).filter((i) => i !== exclude);
    if (method === "random") return { method, index: rng.choice(pool), pool };
    if (method === "tournament") {
      const contestants = rng.sample(pool, Math.max(1, Math.min(tourK, pool.length)));
      let index = contestants[0];
      for (const c of contestants) if (fits[c] > fits[index]) index = c; // ties: first drawn wins
      return { method, index, pool, contestants };
    }
    const w = pool.map((i) => fits[i] + ROULETTE_EPS);
    const total = MG.pySum(w);
    const spin = rng.random() * total;
    let index = pool[pool.length - 1];
    let acc = 0;
    for (let j = 0; j < pool.length; j++) {
      acc += w[j];
      if (spin < acc) { index = pool[j]; break; }
    }
    return { method, index, pool, shares: pool.map((i, j) => ({ i, p: w[j] / total })), spin: spin / total };
  }

  /** Survivor selection. Returns the kept parent and offspring indices.
   *  best      — parents and offspring compete, the popSize fittest stay (offspring win ties);
   *  offspring — the offspring replace every parent (generational);
   *  elitism   — the eliteK best parents stay, the rest are the best offspring. */
  function selectSurvivors(popFits, offFits, rule, eliteK, popSize) {
    const ranked = (fits) => fits.map((f, i) => [i, f]).sort((x, y) => y[1] - x[1]).map((x) => x[0]);
    if (rule === "offspring") return { p: new Set(), o: new Set(ranked(offFits).slice(0, popSize)) };
    if (rule === "elitism") {
      const k = Math.max(0, Math.min(eliteK, popSize));
      return { p: new Set(ranked(popFits).slice(0, k)), o: new Set(ranked(offFits).slice(0, popSize - k)) };
    }
    const cands = popFits.map((f, i) => ["p", i, f, 1]).concat(offFits.map((f, i) => ["o", i, f, 0]));
    cands.sort((x, y) => (y[2] - x[2]) || (x[3] - y[3]));
    const keep = { p: new Set(), o: new Set() };
    for (const [src, i] of cands.slice(0, popSize)) keep[src].add(i);
    return keep;
  }

  /** One full generation with no human input (auto mode).
   *  cfg = { parent, tourK, survivor, eliteK, pMut } — pMut is the per-gene
   *  mutation probability. Every step is returned so the page can show it. */
  function autoRunGeneration(population, hidden, popSize, mode, rng, cfg) {
    const length = chars(hidden).length;
    const fits = population.map((w) => computeFitness(w, hidden, mode));

    const pairs = [];
    const offspring = [];
    for (let k = 0; k < Math.floor(popSize / 2); k++) {
      const a = pickParent(fits, -1, cfg.parent, cfg.tourK, rng);
      const b = pickParent(fits, a.index, cfg.parent, cfg.tourK, rng);
      const cut = rng.randint(1, length - 1);
      pairs.push({ a, b, cut });
      for (let child of crossover(population[a.index], population[b.index], cut)) {
        const mutated = [];
        for (let i = 0; i < length; i++) if (rng.random() < cfg.pMut) mutated.push(i);
        for (const pos of mutated) child = mutate(child, pos, rng);
        offspring.push({ word: child, fitness: computeFitness(child, hidden, mode), mutated: new Set(mutated) });
      }
    }

    const keep = selectSurvivors(fits, offspring.map((o) => o.fitness), cfg.survivor, cfg.eliteK, popSize);
    const next = population.filter((_, i) => keep.p.has(i)).concat(offspring.filter((_, i) => keep.o.has(i)).map((o) => o.word));
    next.sort((x, y) => computeFitness(y, hidden, mode) - computeFitness(x, hidden, mode));
    return { fits, pairs, offspring, keep, population: next };
  }

  GA.logic = {
    ALPHABET, POP_SIZE_CHOICES, MIN_WORD_LEN, MAX_WORD_LEN, SCORING_LABELS,
    PARENT_METHODS, SURVIVOR_RULES,
    WORD_BANK, randomWord, makeRng, cleanHiddenWord, chars, randomPopulation, fitness, computeFitness, crossover, mutate,
    populationStats, pickParent, selectSurvivors, autoRunGeneration,
  };
})();
