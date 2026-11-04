import streamlit as st

from game_engine import GameState, generate_customer_demand, create_customer_order, update_supplier_availability, get_kpis, save_day_snapshot
from ui.theme import inject_css
from ui.components import render_topbar
from ui import home, srm, crm, inventory, finance, learn

st.set_page_config(
    page_title="ERP Sim | Global Gadgets Inc.",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.warning(
    "⚠️ **This app is no longer maintained.** "
    "It still works, but it won't receive fixes or updates."
)

inject_css()

# --- Shared state (one GameState per browser session) ---
if "game_state" not in st.session_state:
    st.session_state.game_state = GameState()
    update_supplier_availability(st.session_state.game_state)
    d = generate_customer_demand(1)
    create_customer_order(st.session_state.game_state, d)
    save_day_snapshot(st.session_state.game_state, get_kpis(st.session_state.game_state))

# --- Navigation: one page per ERP module, all sharing the same GameState ---
pages = {
    "home": st.Page(home.render, title="Dashboard", icon="🏠", url_path="home", default=True),
    "srm": st.Page(srm.render, title="SRM · Suppliers", icon="🚚", url_path="srm"),
    "crm": st.Page(crm.render, title="CRM · Customers", icon="🤝", url_path="crm"),
    "inventory": st.Page(inventory.render, title="Inventory & Ops", icon="📦", url_path="inventory"),
    "finance": st.Page(finance.render, title="Finance", icon="💰", url_path="finance"),
    "learn": st.Page(learn.render, title="Learn: What is an ERP?", icon="🎓", url_path="learn"),
}
st.session_state.nav_pages = pages
nav = st.navigation(list(pages.values()))

with st.sidebar:
    st.caption("🏭 **ERP Sim** — a teaching simulation of an integrated Enterprise "
               "Resource Planning system (SRM · CRM · Inventory · Finance).")
    if st.session_state.get("student_name"):
        st.caption(f"👤 {st.session_state.student_name} ({st.session_state.get('student_id', '')})")

render_topbar()
nav.run()
