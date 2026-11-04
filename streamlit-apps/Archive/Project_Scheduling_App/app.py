import streamlit as st
import pandas as pd
import plotly.express as px
import sys
import os
sys.path.append(os.path.dirname(__file__))

from logic import SchedulingLogic, Task, Worker
from custom_scheduler import drag_and_drop_scheduler
import datetime

# --- Page Config ---
st.set_page_config(
    page_title="Project Scheduler Pro",
    page_icon="📅",
    layout="wide",
)

# --- Custom CSS ---
st.markdown("""
<style>
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        padding-left: 3rem;
        padding-right: 3rem;
    }
    .stApp > header {
        display: none;
    }
    [data-testid="stVerticalBlock"] {
        gap: 0.5rem;
    }
    .main {
        background-color: #0f1116;
        color: #e0e0e0;
    }
    .task-card {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 10px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        transition: all 0.3s ease;
    }
    .task-card:hover {
        border-color: #00ffcc;
        transform: translateY(-2px);
        background: rgba(255, 255, 255, 0.08);
    }
    .worker-header {
        background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%);
        padding: 10px;
        border-radius: 8px;
        text-align: center;
        margin-bottom: 20px;
        color: white;
        font-weight: bold;
    }
    .skill-tag {
        background: #2563eb;
        color: white;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.7em;
        margin-right: 5px;
    }
    .precedence-tag {
        background: #9333ea;
        color: white;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.7em;
        margin-right: 5px;
    }
    .makespan-stat {
        font-size: 2em;
        font-weight: bold;
        color: #00ffcc;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# --- State Management ---
if 'logic' not in st.session_state:
    st.session_state.logic = SchedulingLogic()

logic = st.session_state.logic

# --- Header ---
st.title("🚀 Project Scheduler Pro")


# --- Sidebar Stats ---
with st.sidebar:
    st.header("📊 Dashboard")
    
    unassigned = logic.get_unassigned_tasks()
    st.metric("Pending Tasks", f"{len(unassigned)}")
    
    st.divider()
    
    hard_mode = st.toggle("🔥 Hard Mode (Double Projects)", value=logic.hard_mode)
    if hard_mode != logic.hard_mode:
        logic.reset_game(hard_mode)
        st.rerun()

    st.divider()
    
    with st.expander("📖 How to Play"):
        st.write("""
        1. **Goal**: Finish all projects in the minimum time.
        2. **Tasks**: Each task has skill requirements and may depend on other tasks.
        3. **Workers**: Each team member has unique skills.
        4. **Strategy**: Minimize white space and resolve warnings on the board!
        """)
        
    st.divider()
    st.subheader("🛠 Skills Matrix")
    for w_id, w in logic.workers.items():
        st.write(f"**{w.name}**: {', '.join(w.skills)}")


# --- Interactive Scheduling Board ---
st.subheader("🎮 Visual Planning Board")
st.info("💡 **Planning Phase**: Use this board to visually draft your schedule. Watch for color-coded warnings!")
# Render the custom component
drag_and_drop_scheduler(logic)
