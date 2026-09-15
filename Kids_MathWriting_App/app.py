import os
os.environ.pop("SSLKEYLOGFILE", None)

import random

import streamlit as st

import game_logic as gl

st.set_page_config(page_title="Aventura Mágica: Números y Letras", page_icon="\U0001f984", layout="wide")

CUSTOM_CSS = """
<style>
.stApp {
    background: linear-gradient(180deg, #FFF9F0 0%, #F0FBFF 100%);
}
div.stButton > button {
    border-radius: 16px !important;
    font-weight: 700 !important;
    font-size: 1.15em !important;
    padding: 0.6em 1em !important;
    border: none !important;
    box-shadow: 0 4px 0 rgba(0,0,0,0.12);
    transition: transform 0.05s ease-in-out;
}
div.stButton > button:hover { transform: translateY(-2px); }
div.stButton > button:active { transform: translateY(2px); box-shadow: 0 1px 0 rgba(0,0,0,0.12); }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

BIG_SYMBOL = '<span style="font-size:2.2em;font-weight:800;margin:0 14px;vertical-align:middle;">{}</span>'
PALETTE = ["#FF6B6B", "#4ECDC4", "#FFD93D", "#6BCB77", "#4D96FF", "#B983FF"]


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------
def init_state():
    defaults = {
        "setup_done": False,
        "name": "",
        "mascot": None,
        "mode": None,
        "difficulty": "facil",
        "stars": 0,
        "streak": 0,
        "best_streak": 0,
        "total_answered": 0,
        "total_correct": 0,
        "unlocked": set(),
        "problem": None,
        "attempts": 0,
        "resolved": False,
        "last_correct": None,
        "feedback": "",
        "new_milestones": [],
        "celebrate": False,
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)


def start_new_problem():
    prev_key = st.session_state.problem["key"] if st.session_state.problem else None
    st.session_state.problem = gl.new_problem(st.session_state.mode, st.session_state.difficulty, avoid_key=prev_key)
    st.session_state.attempts = 0
    st.session_state.resolved = False
    st.session_state.last_correct = None
    st.session_state.feedback = ""
    st.session_state.new_milestones = []
    st.session_state.celebrate = False


def go_to_mode(mode):
    st.session_state.mode = mode
    start_new_problem()


def go_to_menu():
    st.session_state.mode = None
    st.session_state.problem = None


def reset_progress():
    st.session_state.stars = 0
    st.session_state.streak = 0
    st.session_state.best_streak = 0
    st.session_state.total_answered = 0
    st.session_state.total_correct = 0
    st.session_state.unlocked = set()
    go_to_menu()


def submit_answer(user_answer):
    prob = st.session_state.problem
    correct = gl.check_answer(prob, user_answer)
    if correct:
        first_try = st.session_state.attempts == 0
        st.session_state.resolved = True
        st.session_state.last_correct = True
        st.session_state.total_answered += 1
        st.session_state.total_correct += 1
        st.session_state.stars += 1
        if first_try:
            st.session_state.streak += 1
            st.session_state.best_streak = max(st.session_state.best_streak, st.session_state.streak)
        new_ms = gl.newly_unlocked_milestones(st.session_state.stars, st.session_state.unlocked)
        st.session_state.unlocked.update(new_ms)
        st.session_state.new_milestones = new_ms
        st.session_state.feedback = random.choice(gl.PRAISE_CORRECT)
        st.session_state.celebrate = bool(new_ms) or (first_try and st.session_state.streak > 0 and st.session_state.streak % 5 == 0)
    else:
        st.session_state.attempts += 1
        st.session_state.streak = 0
        if st.session_state.attempts >= 3:
            st.session_state.resolved = True
            st.session_state.last_correct = False
            st.session_state.total_answered += 1
            st.session_state.feedback = random.choice(gl.PRAISE_REVEAL)
        else:
            st.session_state.feedback = random.choice(gl.PRAISE_TRY_AGAIN)


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------
def icon_group_html(icon: str, count: int, size: int = 40) -> str:
    tiles = "".join(f'<span style="font-size:{size}px;margin:2px;">{icon}</span>' for _ in range(count))
    return (
        f'<span style="display:inline-block;padding:8px 14px;background:#FFF3D6;'
        f'border-radius:16px;margin:4px;vertical-align:middle;">{tiles}</span>'
    )


def letter_tiles_html(letters: str, size: int = 44) -> str:
    parts = []
    for i, ch in enumerate(letters):
        color = PALETTE[i % len(PALETTE)]
        parts.append(
            f'<span style="display:inline-flex;align-items:center;justify-content:center;'
            f'width:{size}px;height:{size}px;margin:3px;border-radius:10px;font-weight:800;'
            f'font-family:ui-monospace,Consolas,monospace;font-size:{int(size * 0.5)}px;'
            f'background:{color};color:#fff;box-shadow:0 3px 0 rgba(0,0,0,0.15);">{ch}</span>'
        )
    return '<span style="white-space:nowrap;">' + "".join(parts) + "</span>"


def masked_word_html(masked: str, size: int = 48) -> str:
    parts = []
    for ch in masked:
        if ch == "_":
            style = "background:#fff;border:3px dashed #FF6B6B;color:#FF6B6B;"
            content = "?"
        else:
            style = "background:#4D96FF;color:#fff;border:3px solid #4D96FF;"
            content = ch.upper()
        parts.append(
            f'<span style="display:inline-flex;align-items:center;justify-content:center;'
            f'width:{size}px;height:{size}px;margin:3px;border-radius:10px;font-weight:800;'
            f'font-family:ui-monospace,Consolas,monospace;font-size:{int(size * 0.5)}px;{style}">{content}</span>'
        )
    return '<span style="white-space:nowrap;">' + "".join(parts) + "</span>"


def centered(html: str):
    st.markdown(f"<div style='text-align:center;'>{html}</div>", unsafe_allow_html=True)


def render_choice_buttons(choices, key_prefix: str):
    if st.session_state.resolved:
        return
    cols = st.columns(len(choices))
    for i, c in enumerate(choices):
        label = c.upper() if isinstance(c, str) else str(c)
        if cols[i].button(label, key=f"{key_prefix}_{i}", width="stretch"):
            submit_answer(c)
            st.rerun()


def render_math(prob: dict):
    mascot = st.session_state.mascot
    a, b, icon = prob["a"], prob["b"], prob["icon"]
    if prob["kind"] == "add":
        st.markdown(f"<h3 style='text-align:center;'>{mascot} ¿Cuánto es esto?</h3>", unsafe_allow_html=True)
        expr = (
            icon_group_html(icon, a) + BIG_SYMBOL.format("+") + icon_group_html(icon, b)
            + BIG_SYMBOL.format("=") + BIG_SYMBOL.format("❓")
        )
        centered(expr)
        st.markdown(f"<h2 style='text-align:center;'>{a} + {b} = ?</h2>", unsafe_allow_html=True)
    else:
        st.markdown(f"<h3 style='text-align:center;'>{mascot} ¿Cuántos hay en total?</h3>", unsafe_allow_html=True)
        group_word = "grupo" if a == 1 else "grupos"
        st.markdown(f"<p style='text-align:center;font-size:1.2em;'>{a} {group_word} de {b}</p>", unsafe_allow_html=True)
        centered("".join(icon_group_html(icon, b) for _ in range(a)))
        st.markdown(f"<h2 style='text-align:center;'>{a} × {b} = ?</h2>", unsafe_allow_html=True)

    st.write("")
    render_choice_buttons(prob["choices"], key_prefix=f"choice_{prob['key']}")


def render_complete(prob: dict):
    mascot = st.session_state.mascot
    st.markdown(f"<h3 style='text-align:center;'>{mascot} Completa la palabra</h3>", unsafe_allow_html=True)
    st.markdown(f"<div style='text-align:center;font-size:4em;'>{prob['emoji']}</div>", unsafe_allow_html=True)
    centered(masked_word_html(prob["masked"]))
    st.write("")
    render_choice_buttons(prob["choices"], key_prefix=f"choice_{prob['key']}")


def render_text_answer(prob: dict, prompt: str, show_letters: bool = False):
    mascot = st.session_state.mascot
    st.markdown(f"<h3 style='text-align:center;'>{mascot} {prompt}</h3>", unsafe_allow_html=True)
    size = "4em" if show_letters else "6em"
    st.markdown(f"<div style='text-align:center;font-size:{size};'>{prob['emoji']}</div>", unsafe_allow_html=True)
    if show_letters:
        centered(letter_tiles_html(prob["display"].upper()))
    st.write("")
    if st.session_state.resolved:
        return
    with st.form(key=f"form_{prob['key']}", clear_on_submit=True):
        c1, c2 = st.columns([3, 1])
        answer = c1.text_input("Escribe la palabra", label_visibility="collapsed", placeholder="Escribe aquí...")
        submitted = c2.form_submit_button("Comprobar ✅", width="stretch")
    if submitted:
        submit_answer(answer)
        st.rerun()


def render_problem(prob: dict):
    if prob["kind"] in ("add", "mult"):
        render_math(prob)
    elif prob["kind"] == "w_complete":
        render_complete(prob)
    elif prob["kind"] == "w_scramble":
        render_text_answer(prob, "¡Ordena las letras!", show_letters=True)
    elif prob["kind"] == "w_spell":
        render_text_answer(prob, "¿Qué es esto? ¡Escríbelo!", show_letters=False)


def render_feedback_and_next():
    if st.session_state.attempts > 0 and not st.session_state.resolved:
        st.write("")
        st.warning(f"{st.session_state.mascot} {st.session_state.feedback}")
        return
    if not st.session_state.resolved:
        return
    prob = st.session_state.problem
    st.write("")
    if st.session_state.last_correct:
        st.success(f"{st.session_state.mascot} {st.session_state.feedback} ⭐")
        if st.session_state.celebrate:
            st.balloons()
        for i in st.session_state.new_milestones:
            st.info(f"\U0001f389 ¡Insignia nueva! {gl.STICKERS[i]} — ¡llegaste a {gl.MILESTONES[i]} estrellas!")
    else:
        answer_word = prob["word"] if prob["kind"] == "w_complete" else prob["answer"]
        st.warning(f"{st.session_state.feedback} **{str(answer_word).upper()}**")

    if st.button("Siguiente ➡️", type="primary", width="stretch"):
        start_new_problem()
        st.rerun()


def render_game_header():
    top = st.columns([1, 3, 1])
    if top[0].button("\U0001f3e0 Menú", width="stretch"):
        go_to_menu()
        st.rerun()
    mode_titles = {
        "sumas": "➕ Sumas", "multiplicar": "✖️ Multiplicar",
        "escritura": "✍️ Escritura", "sorpresa": "\U0001f389 Sorpresa",
    }
    top[1].markdown(f"<h3 style='text-align:center;'>{mode_titles[st.session_state.mode]}</h3>", unsafe_allow_html=True)
    top[2].metric("⭐ Estrellas", st.session_state.stars)
    st.divider()


def render_welcome():
    st.markdown("<h1 style='text-align:center;'>\U0001f984 Aventura Mágica: Números y Letras \U0001f308</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p style='text-align:center;font-size:1.3em;'>¡Practica sumas, multiplicaciones y palabras "
        "en español jugando!</p>",
        unsafe_allow_html=True,
    )
    st.write("")
    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        name = st.text_input("¿Cómo te llamas?", value=st.session_state.name, placeholder="Escribe tu nombre aquí")
        st.markdown("**Elige a tu compañero de aventuras:**")
        cols = st.columns(len(gl.MASCOTS))
        for col, (emoji, label) in zip(cols, gl.MASCOTS.items()):
            with col:
                is_chosen = st.session_state.mascot == emoji
                if st.button(emoji, key=f"mascot_{emoji}", width="stretch", type="primary" if is_chosen else "secondary"):
                    st.session_state.mascot = emoji
                    st.rerun()
                st.caption(label)
        st.write("")
        ready = bool(name.strip()) and st.session_state.mascot is not None
        if st.button("¡Vamos a jugar! \U0001f680", type="primary", disabled=not ready, width="stretch"):
            st.session_state.name = name.strip()
            st.session_state.setup_done = True
            st.rerun()
        if not ready:
            st.caption("Escribe tu nombre y elige un compañero para comenzar.")


def render_menu():
    st.markdown(
        f"<h2 style='text-align:center;'>{st.session_state.mascot} ¡Hola, {st.session_state.name}! "
        "¿Qué quieres practicar hoy?</h2>",
        unsafe_allow_html=True,
    )
    st.write("")
    cards = [
        ("sumas", "➕", "Sumas", "#B3E5FC"),
        ("multiplicar", "✖️", "Multiplicar", "#FFE0B2"),
        ("escritura", "✍️", "Escritura", "#C8E6C9"),
        ("sorpresa", "\U0001f389", "Sorpresa", "#E1BEE7"),
    ]
    cols = st.columns(4)
    for col, (mode, emoji, label, color) in zip(cols, cards):
        with col:
            st.markdown(
                f"<div style='background:{color};border-radius:20px;padding:30px 10px;"
                f"text-align:center;font-size:3em;'>{emoji}</div>",
                unsafe_allow_html=True,
            )
            if st.button(label, key=f"mode_{mode}", width="stretch", type="primary"):
                go_to_mode(mode)
                st.rerun()


def render_sidebar():
    with st.sidebar:
        if not st.session_state.setup_done:
            st.markdown("### \U0001f984 Aventura Mágica")
            return

        st.markdown(f"### {st.session_state.mascot} ¡Hola, {st.session_state.name}!")
        st.divider()
        c1, c2 = st.columns(2)
        c1.metric("⭐ Estrellas", st.session_state.stars)
        c2.metric("\U0001f525 Racha", st.session_state.streak)
        if st.session_state.total_answered:
            st.caption(
                f"Mejor racha: {st.session_state.best_streak} · "
                f"Correctas: {st.session_state.total_correct}/{st.session_state.total_answered}"
            )

        st.divider()
        st.markdown("**Nivel de matemáticas**")
        difficulty_label = st.radio(
            "Nivel de matemáticas", ["Fácil", "Un poco más difícil"],
            index=0 if st.session_state.difficulty == "facil" else 1,
            label_visibility="collapsed",
        )
        st.session_state.difficulty = "facil" if difficulty_label == "Fácil" else "dificil"

        st.divider()
        st.markdown("**\U0001f3c5 Mi colección**")
        if st.session_state.unlocked:
            stickers = " ".join(f"<span style='font-size:1.8em;'>{gl.STICKERS[i]}</span>" for i in sorted(st.session_state.unlocked))
            st.markdown(stickers, unsafe_allow_html=True)
        else:
            st.caption("¡Consigue estrellas para desbloquear insignias!")
        next_milestone = next((m for m in gl.MILESTONES if st.session_state.stars < m), None)
        if next_milestone:
            st.progress(
                min(1.0, st.session_state.stars / next_milestone),
                text=f"{st.session_state.stars}/{next_milestone} para la próxima insignia",
            )

        st.divider()
        if st.session_state.mode is not None and st.button("\U0001f3e0 Volver al menú", width="stretch"):
            go_to_menu()
            st.rerun()
        if st.button("\U0001f504 Reiniciar progreso", width="stretch"):
            reset_progress()
            st.rerun()


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
init_state()
render_sidebar()

if not st.session_state.setup_done:
    render_welcome()
elif st.session_state.mode is None:
    render_menu()
else:
    render_game_header()
    render_problem(st.session_state.problem)
    render_feedback_and_next()
