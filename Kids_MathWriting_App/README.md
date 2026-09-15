# Aventura Mágica: Números y Letras

A colorful, mascot-guided Streamlit game for young kids (built for a
6-year-old) to practice **addition**, **multiplication as equal groups**,
and **Spanish spelling** - all in one continuous, no-pressure play session.
Everything in the UI is in Spanish, matching the writing practice.

## How it plays

1. **Bienvenida** - the child types their name and picks a mascot
   companion (unicorn, dragon, cat, fox, or panda) that cheers them on
   throughout.
2. **Menú** - four big colorful cards to choose what to practice:
   - **➕ Sumas** - addition shown as two groups of emoji (animals, fruit,
     stars, vehicles, toys - a new theme each time) building up to
     `a + b = ?`, answered via 4 big multiple-choice buttons.
   - **✖️ Multiplicar** - multiplication introduced the way a 6-year-old
     actually learns it: as *"a grupos de b"* equal-sized emoji groups,
     reinforcing repeated addition rather than rote times-tables.
   - **✍️ Escritura** - Spanish spelling practice mixing three activity
     types pulled from a ~35-word picture bank (animals, nature, everyday
     objects): unscramble the letters, fill in the missing letter (4
     multiple-choice letters, including the correctly-accented one), or
     spell the whole word from just the picture.
   - **\U0001f389 Sorpresa** - randomly mixes all of the above for variety.
3. Every answer gets immediate, encouraging feedback - wrong answers get
   up to 3 gentle retries (never a penalty) before the answer is revealed;
   correct answers earn a star, extend a streak, and occasionally trigger
   a balloons celebration. Every few stars unlocks a new sticker badge in
   the sidebar's "Mi colección".
4. A sidebar difficulty toggle ("Fácil" / "Un poco más difícil") adjusts
   the number ranges for Sumas and Multiplicar independent of Escritura.

There's no win/lose state or timer - it's designed for open-ended,
low-pressure repeat play, with a "Reiniciar progreso" button to start a
fresh session.

### A note on typing accents

Spanish words are stored and displayed with their correct accents (e.g.
*avión*, *corazón*), but typed answers are checked accent-insensitively
(á/é/í/ó/ú/ü all fold to their plain vowel) since a kid's keyboard rarely
has accent keys - while `ñ` is always kept distinct from `n`. The
"complete the word" activity uses click-to-choose letters instead of
typing, so it can safely include the correctly-accented letter as one of
the options.

## Run it

```bash
streamlit run Kids_MathWriting_App/app.py
```

## Files

- `app.py` - Streamlit UI: mascot/name setup, mode menu, problem
  rendering, rewards (stars, streaks, badges).
- `game_logic.py` - pure functions: problem generation, the word bank,
  scrambling/masking, and answer checking (unit-tested in
  `../test_kids_mathwriting_logic.py`).
