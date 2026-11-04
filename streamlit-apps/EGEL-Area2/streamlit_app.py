import streamlit as st
from game_utils import PUZZLES, FINAL_KEYWORD, GameLogic
import os

# Page Config - WIDE LAYOUT for laptops/tablets
st.set_page_config(page_title="Mega-Factory Escape", page_icon="🏭", layout="wide")
st.warning(
    "⚠️ **Esta aplicación ya no recibe mantenimiento.** "
    "Sigue funcionando, pero no tendrá correcciones ni actualizaciones."
)

# Base path for images (calculated relative to this script for portability)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_BASE_PATH = os.path.join(SCRIPT_DIR, "images")

# Dark Theme CSS (Optimized for density & no scrolling)
st.markdown("""
<style>
    .main { background-color: #0e1117; color: #ffffff; }
    .stApp { background-color: #0e1117; }
    .room-container {
        background: #1a1c24; border: 1px solid #30363d;
        padding: 1.2em; border-radius: 12px; margin-bottom: 0.5em;
        box-shadow: 0 4px 8px rgba(0,0,0,0.5);
    }
    .story-text { font-style: italic; color: #a5adb9; font-size: 0.95em; border-left: 3px solid #58a6ff; padding-left: 15px; margin-bottom: 1em; }
    .fact-box { background: #161b22; color: #58a6ff; padding: 12px; border-radius: 8px; border: 1px dashed #58a6ff; margin: 10px 0; }
    .stSelectbox label, .stTextInput label { font-size: 0.85em; color: #8b949e; }
    [data-testid="stSidebar"] { min-width: 250px; max-width: 350px; }
    .stButton>button { border-radius: 8px; }
    h1, h2, h3 { color: #ffffff !important; }
    h3 { margin-top: 0 !important; }
</style>
""", unsafe_allow_html=True)

# Session States
if 'game_logic' not in st.session_state:
    st.session_state.game_logic = GameLogic(platform="streamlit")
if 'show_hint' not in st.session_state:
    st.session_state.show_hint = False
if 'game_started' not in st.session_state:
    st.session_state.game_started = False

logic = st.session_state.game_logic

# Header
st.title("🛡️ Mega-Factory: Lockdown")

if not st.session_state.game_started:
    st.markdown("<div class='room-container'>", unsafe_allow_html=True)
    st.markdown("### 🛑 Acceso Restringido: Nivel 0")
    st.info("La fábrica está en cierre de emergencia. Todos los ingenieros deben iniciar la misión simultáneamente.")
    
    formulario_path = os.path.join(SCRIPT_DIR, "6.-Formulario-EGELD-IINDU-EAM-190922.pdf")
    if os.path.exists(formulario_path):
        with open(formulario_path, "rb") as pdf_file:
            st.download_button(
                label="📥 Descargar Formulario EGEL",
                data=pdf_file,
                file_name="Formulario_EGEL_IINDU.pdf",
                mime="application/pdf"
            )

    start_code = st.text_input("Ingrese el Código de Autorización General:", placeholder="Código de 3 letras...", key="start_input")
    
    if st.button("Iniciar Misión General", type="primary"):
        if start_code.strip().upper() == "TEC":
            st.session_state.game_started = True
            st.rerun()
        else:
            st.error("❌ Código incorrecto. Espera a que el supervisor dicte la clave.")
            
    st.markdown("</div>", unsafe_allow_html=True)

else:
    # Sidebar: Mission Status & Visuals
    with st.sidebar:
        st.markdown("<h2 style='text-align:center; color:#58a6ff; margin-bottom:0;'>MISSION CONTROL</h2>", unsafe_allow_html=True)
        st.progress(logic.get_progress()/100)
        
        c1, c2 = st.columns(2)
        c1.metric("Sala", f"{logic.current_room + 1}/10")
        c2.metric("Pistas", logic.hints_used)
        
        st.divider()
        
        # Visuals moved to sidebar as requested
        if not logic.completed:
            puzzle = PUZZLES[logic.current_room]
            if puzzle['img']:
                img_path = os.path.join(IMG_BASE_PATH, puzzle['img'])
                if os.path.exists(img_path):
                    st.image(img_path, caption=f"Ubicación: {puzzle['title']}")
                else:
                    st.warning(f"Cargando visual de {puzzle['title']}...")
        
        st.info("💡 Usa el Formulario EGEL PLUS IINDU (Págs 24-30).")
        
        formulario_path = os.path.join(SCRIPT_DIR, "6.-Formulario-EGELD-IINDU-EAM-190922.pdf")
        if os.path.exists(formulario_path):
            with open(formulario_path, "rb") as pdf_file:
                st.download_button(
                    label="📥 Descargar Formulario EGEL",
                    data=pdf_file,
                    file_name="Formulario_EGEL_IINDU.pdf",
                    mime="application/pdf",
                    key="sidebar_dl_btn"
                )

    # Main Stage
    if logic.completed:
        st.balloons()
        st.success("## 🏆 MISIÓN CUMPLIDA")
        st.write("¡Has salvado la fábrica global!")
        st.write(f"Rango de Honor: **{logic.get_rank()}**")
        st.markdown(f"<div style='font-size:2em; text-align:center; padding:20px; border:4px double #4CAF50; background:#161b22; color: white;'>🔑 CLAVE FINAL: {FINAL_KEYWORD}</div>", unsafe_allow_html=True)
        if st.button("Nueva Partida"):
            st.session_state.game_logic = GameLogic(platform="streamlit")
            st.session_state.game_started = False
            st.rerun()
    else:
        puzzle = PUZZLES[logic.current_room]
        
        st.markdown(f"<div class='room-container'>", unsafe_allow_html=True)
        st.subheader(puzzle['title'])
        st.markdown(f"<p class='story-text'>{puzzle['story']}</p>", unsafe_allow_html=True)
        
        st.markdown(f"<p style='color: white;'><b>🔍 Análisis de Situación:</b> {puzzle['clue']}</p>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: white;'><b>🎯 Requerimiento:</b> {puzzle['task']}</p>", unsafe_allow_html=True)
        
        if not logic.show_fact:
            if puzzle['type'] == 'choice':
                user_ans = st.selectbox("Comando de Desbloqueo:", ["-- Selecciona --"] + puzzle['choices'], key=f"sel_{logic.current_room}")
            else:
                user_ans = st.text_input("Comando de Desbloqueo:", key=f"ans_{logic.current_room}", placeholder="Escriba aquí...")

            act_col1, act_col2 = st.columns([1,1])
            with act_col1:
                if st.button("⚡ Ejecutar Protocolo", type="primary", use_container_width=True):
                    if user_ans and user_ans not in ["-- Selecciona --", "-- Elige --"]:
                        correct, msg = logic.check_answer(user_ans)
                        if correct:
                            st.rerun()
                        else:
                            st.error(msg)
                    else:
                        st.warning("Ingrese un código de acceso.")
            with act_col2:
                if st.button("💡 Solicitar Pista", use_container_width=True):
                    st.session_state.show_hint = True
            
            if st.session_state.get('show_hint', False):
                st.info(f"Frecuencia detectada: {logic.use_hint()}")
                st.session_state.show_hint = False
        else:
            st.markdown(f"<div class='fact-box'>💡 <b>PROTOCOLO APRENDIDO</b><br>{puzzle['fact']}</div>", unsafe_allow_html=True)
            if st.button("Entrar a la siguiente sala 🔓", type="primary", use_container_width=True):
                logic.next_level()
                st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)
