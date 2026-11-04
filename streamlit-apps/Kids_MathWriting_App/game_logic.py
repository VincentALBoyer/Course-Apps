"""Pure game logic for the Kids Math & Writing app - no Streamlit imports,
so every function here is unit-testable in isolation (see
../test_kids_mathwriting_logic.py)."""

import random

# ---------------------------------------------------------------------------
# Content banks
# ---------------------------------------------------------------------------
ICON_THEMES = {
    "animales": ["\U0001f436", "\U0001f431", "\U0001f430", "\U0001f43b", "\U0001f981", "\U0001f438", "\U0001f435", "\U0001f437"],
    "frutas": ["\U0001f34e", "\U0001f34c", "\U0001f347", "\U0001f353", "\U0001f34a", "\U0001f34d", "\U0001f349", "\U0001f351"],
    "estrellas": ["⭐", "\U0001f31f", "✨", "\U0001f4ab"],
    "vehiculos": ["\U0001f697", "\U0001f695", "\U0001f693", "\U0001f68c", "\U0001f680", "✈️"],
    "juguetes": ["⚽", "\U0001f9f8", "\U0001f388", "\U0001f3b2", "\U0001fa80", "\U0001fa81"],
}

# (word, emoji) - words carry their correct Spanish spelling (accents
# included) for display, but check_word() accepts the unaccented form too
# since a 6-year-old's keyboard rarely has accent keys.
WORD_BANK = [
    ("gato", "\U0001f431"), ("perro", "\U0001f436"), ("pez", "\U0001f41f"), ("oso", "\U0001f43b"),
    ("pato", "\U0001f986"), ("vaca", "\U0001f42e"), ("rana", "\U0001f438"), ("mono", "\U0001f412"),
    ("tigre", "\U0001f42f"), ("conejo", "\U0001f430"), ("abeja", "\U0001f41d"), ("mariposa", "\U0001f98b"),
    ("tortuga", "\U0001f422"), ("elefante", "\U0001f418"), ("sol", "☀️"), ("luna", "\U0001f319"),
    ("estrella", "⭐"), ("flor", "\U0001f338"), ("nube", "☁️"), ("árbol", "\U0001f333"),
    ("casa", "\U0001f3e0"), ("pelota", "⚽"), ("libro", "\U0001f4d6"), ("tren", "\U0001f682"),
    ("barco", "⛵"), ("cohete", "\U0001f680"), ("coche", "\U0001f697"), ("globo", "\U0001f388"),
    ("regalo", "\U0001f381"), ("corazón", "❤️"), ("ratón", "\U0001f42d"),
    ("avión", "✈️"), ("mamá", "\U0001f469"), ("papá", "\U0001f468"), ("león", "\U0001f981"),
]

MILESTONES = [5, 10, 20, 35, 50, 75, 100, 150, 200]
STICKERS = ["\U0001f31f", "\U0001f388", "\U0001f984", "\U0001f308", "\U0001f3c6", "\U0001f947", "\U0001f451", "\U0001f48e", "\U0001f680"]

MASCOTS = {
    "\U0001f984": "Uni el Unicornio",
    "\U0001f409": "Draco el Dragón",
    "\U0001f431": "Mimi la Gatita",
    "\U0001f98a": "Foxi el Zorro",
    "\U0001f43c": "Pandi el Panda",
}

PRAISE_CORRECT = [
    "¡Genial!", "¡Excelente!", "¡Lo lograste!", "¡Increíble!",
    "¡Muy bien!", "¡Perfecto!", "¡Eres un crack!", "¡Sigue así!",
]
PRAISE_TRY_AGAIN = [
    "¡Casi! Intenta de nuevo.", "¡Muy cerca! Prueba otra vez.",
    "No pasa nada, ¡tú puedes!", "¡Vamos, un intento más!",
]
PRAISE_REVEAL = [
    "¡Buen intento! La respuesta era", "No te preocupes, la respuesta correcta es",
    "¡Casi lo tienes! Era",
]

# Letters used for wrong-answer distractors in the "complete the word" game.
LETTER_POOL = "abcdefghijlmnoprstuvz"

ACCENT_MAP = {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ü": "u"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def strip_accents(text: str) -> str:
    """Folds accented vowels to their plain form but leaves letters like
    ñ untouched, so e.g. 'año' and 'ano' are never treated as equal."""
    return "".join(ACCENT_MAP.get(ch, ch) for ch in text)


def normalize(text: str) -> str:
    return strip_accents(text.strip().lower())


def check_word(user_input: str, answer: str) -> bool:
    return normalize(user_input) == normalize(answer)


def random_theme_icon(rng: random.Random = random) -> str:
    theme = rng.choice(list(ICON_THEMES.keys()))
    return rng.choice(ICON_THEMES[theme])


def make_number_choices(answer: int, spread: int, n: int = 4, rng: random.Random = random) -> list:
    """Multiple-choice distractors near `answer`, always including it."""
    choices = {answer}
    guard = 0
    while len(choices) < n and guard < 200:
        guard += 1
        delta = rng.randint(-spread, spread)
        candidate = answer + delta
        if candidate >= 0:
            choices.add(candidate)
    choices = list(choices)
    rng.shuffle(choices)
    return choices


# ---------------------------------------------------------------------------
# Math problems
# ---------------------------------------------------------------------------
def make_addition_problem(difficulty: str = "facil", rng: random.Random = random) -> dict:
    if difficulty == "facil":
        a, b = rng.randint(1, 5), rng.randint(1, 5)
        spread = 3
    else:
        a, b = rng.randint(1, 10), rng.randint(1, 10)
        spread = 5
    answer = a + b
    return {
        "kind": "add",
        "a": a,
        "b": b,
        "answer": answer,
        "icon": random_theme_icon(rng),
        "choices": make_number_choices(answer, spread, rng=rng),
        "key": ("add", a, b),
    }


def make_multiplication_problem(difficulty: str = "facil", rng: random.Random = random) -> dict:
    if difficulty == "facil":
        a, b = rng.randint(1, 3), rng.randint(1, 3)
        spread = 3
    else:
        a, b = rng.randint(1, 5), rng.randint(1, 5)
        spread = 6
    answer = a * b
    return {
        "kind": "mult",
        "a": a,
        "b": b,
        "answer": answer,
        "icon": random_theme_icon(rng),
        "choices": make_number_choices(answer, spread, rng=rng),
        "key": ("mult", a, b),
    }


def check_math_answer(problem: dict, chosen: int) -> bool:
    return chosen == problem["answer"]


# ---------------------------------------------------------------------------
# Writing (Spanish) problems
# ---------------------------------------------------------------------------
def scramble_word(word: str, rng: random.Random = random) -> str:
    letters = list(word)
    scrambled = word
    for _ in range(20):
        rng.shuffle(letters)
        scrambled = "".join(letters)
        if scrambled != word:
            break
    return scrambled


def make_scramble_problem(rng: random.Random = random) -> dict:
    candidates = [wp for wp in WORD_BANK if len(strip_accents(wp[0])) <= 7]
    word, emoji = rng.choice(candidates)
    return {
        "kind": "w_scramble",
        "word": word,
        "emoji": emoji,
        "display": scramble_word(word, rng),
        "answer": word,
        "key": ("w_scramble", word),
    }


def make_complete_problem(rng: random.Random = random) -> dict:
    word, emoji = rng.choice(WORD_BANK)
    idx = rng.randrange(len(word))
    correct_letter = word[idx]
    masked = word[:idx] + "_" + word[idx + 1:]

    pool = [c for c in LETTER_POOL if c != correct_letter.lower()]
    distractors = rng.sample(pool, min(3, len(pool)))
    letter_choices = [correct_letter] + distractors
    rng.shuffle(letter_choices)

    return {
        "kind": "w_complete",
        "word": word,
        "emoji": emoji,
        "masked": masked,
        "answer": correct_letter,
        "choices": letter_choices,
        "key": ("w_complete", word, idx),
    }


def make_spell_problem(rng: random.Random = random) -> dict:
    candidates = [wp for wp in WORD_BANK if len(strip_accents(wp[0])) <= 8]
    word, emoji = rng.choice(candidates)
    return {
        "kind": "w_spell",
        "word": word,
        "emoji": emoji,
        "answer": word,
        "key": ("w_spell", word),
    }


WRITING_KINDS = ("w_scramble", "w_complete", "w_spell")

_MAKERS = {
    "add": make_addition_problem,
    "mult": make_multiplication_problem,
    "w_scramble": lambda difficulty="facil", rng=random: make_scramble_problem(rng),
    "w_complete": lambda difficulty="facil", rng=random: make_complete_problem(rng),
    "w_spell": lambda difficulty="facil", rng=random: make_spell_problem(rng),
}

MODE_KINDS = {
    "sumas": ["add"],
    "multiplicar": ["mult"],
    "escritura": list(WRITING_KINDS),
    "sorpresa": ["add", "mult", *WRITING_KINDS],
}


def new_problem(mode: str, difficulty: str = "facil", avoid_key=None, rng: random.Random = random) -> dict:
    """Builds a new problem for `mode`, retrying a few times to avoid
    immediately repeating the previous problem's key."""
    kinds = MODE_KINDS[mode]
    problem = None
    for _ in range(6):
        kind = rng.choice(kinds)
        problem = _MAKERS[kind](difficulty, rng)
        if problem["key"] != avoid_key:
            break
    return problem


def check_answer(problem: dict, user_answer) -> bool:
    kind = problem["kind"]
    if kind in ("add", "mult"):
        return check_math_answer(problem, user_answer)
    if kind == "w_complete":
        return isinstance(user_answer, str) and user_answer.lower() == problem["answer"].lower()
    return check_word(str(user_answer), problem["answer"])


# ---------------------------------------------------------------------------
# Rewards
# ---------------------------------------------------------------------------
def newly_unlocked_milestones(stars: int, already_unlocked: set) -> list:
    """Returns milestone indices newly crossed by `stars` that aren't in
    `already_unlocked` (does not mutate the set)."""
    return [i for i, m in enumerate(MILESTONES) if stars >= m and i not in already_unlocked]
