# =============================================================================
# EIS Simulator — Main Entry Point
# Enterprise Information System: ERP + SRM + CRM
# =============================================================================
import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from Archive.ERP_Sim_Integrated.engine.erp_engine import init_simulation, advance_day, get_kpis
from Archive.ERP_Sim_Integrated.config import COMPANY_NAME, THEME, MODULE_COLORS

st.set_page_config(
    page_title=f"EIS Simulator | {COMPANY_NAME}",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================================================================
# GLOBAL CSS
# =============================================================================
st.html(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    html, body, .stApp {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        background-color: {THEME['bg']} !important;
    }}

    /* Sidebar */
    section[data-testid="stSidebar"] {{
        background: {THEME['sidebar_bg']} !important;
    }}
    section[data-testid="stSidebar"] * {{
        color: #CBD5E1 !important;
    }}
    section[data-testid="stSidebar"] .stRadio label {{
        color: #E2E8F0 !important;
    }}
    section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3, section[data-testid="stSidebar"] h4 {{
        color: #F8FAFC !important;
    }}

    /* Cards */
    .eis-card {{
        background: white;
        border: 1px solid {THEME['border']};
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 0.75rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }}
    .eis-card-header {{
        font-weight: 700;
        font-size: 0.95rem;
        margin-bottom: 0.5rem;
        color: #1E293B;
    }}

    /* Module badges */
    .badge-erp {{ background:#DBEAFE; color:#1D4ED8; padding:2px 8px; border-radius:20px; font-size:0.72rem; font-weight:600; }}
    .badge-srm {{ background:#EDE9FE; color:#6D28D9; padding:2px 8px; border-radius:20px; font-size:0.72rem; font-weight:600; }}
    .badge-crm {{ background:#D1FAE5; color:#065F46; padding:2px 8px; border-radius:20px; font-size:0.72rem; font-weight:600; }}
    .badge-off {{ background:#F1F5F9; color:#64748B; padding:2px 8px; border-radius:20px; font-size:0.72rem; font-weight:600; }}

    /* Alert boxes */
    .alert-green {{ background:#D1FAE5; border-left:4px solid #10B981; padding:10px 14px; border-radius:6px; margin:4px 0; font-size:0.86rem; }}
    .alert-amber {{ background:#FEF3C7; border-left:4px solid #F59E0B; padding:10px 14px; border-radius:6px; margin:4px 0; font-size:0.86rem; }}
    .alert-red   {{ background:#FEE2E2; border-left:4px solid #EF4444; padding:10px 14px; border-radius:6px; margin:4px 0; font-size:0.86rem; }}
    .alert-blue  {{ background:#DBEAFE; border-left:4px solid #3B82F6; padding:10px 14px; border-radius:6px; margin:4px 0; font-size:0.86rem; }}

    /* Page header */
    .page-header {{
        background: linear-gradient(135deg, #1A56DB 0%, #7E3AF2 100%);
        padding: 1.25rem 1.75rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        color: white !important;
    }}
    .page-header h2 {{ color: white !important; margin: 0 !important; font-weight: 700; }}
    .page-header p {{ color: rgba(255,255,255,0.8) !important; margin: 0.25rem 0 0 0; font-size: 0.9rem; }}

    /* KPI Metric cards */
    [data-testid="stMetric"] {{
        background: white !important;
        border: 1px solid {THEME['border']} !important;
        border-radius: 10px !important;
        padding: 1rem !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05) !important;
    }}
    [data-testid="stMetricValue"] {{ font-weight: 800 !important; }}

    /* Section separation */
    .section-title {{
        font-size: 1rem;
        font-weight: 700;
        color: #1E293B;
        border-bottom: 2px solid {THEME['border']};
        padding-bottom: 0.4rem;
        margin-bottom: 1rem;
        margin-top: 0.5rem;
    }}

    /* Kanban stage chip */
    .stage-chip {{
        display: inline-block;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
    }}

    /* Scroll feed */
    .event-feed {{ max-height: 280px; overflow-y: auto; }}

    /* Inbox email card */
    .inbox-card {{ background:white; border:1px solid #E2E8F0; border-radius:8px; padding:12px 14px; margin-bottom:8px; }}
    .inbox-unread {{ border-left: 4px solid #3B82F6; }}
    .inbox-read   {{ border-left: 4px solid #E2E8F0; opacity: 0.75; }}

    /* Progress bar styling */
    .stProgress > div > div {{ background: linear-gradient(90deg, #1A56DB, #7E3AF2) !important; }}
</style>
""")


# =============================================================================
# SESSION STATE INITIALIZATION
# =============================================================================
if "sim_state" not in st.session_state:
    st.session_state.sim_state = init_simulation()

state = st.session_state.sim_state


# =============================================================================
# SIDEBAR
# =============================================================================
with st.sidebar:
    # Company header
    st.html(f"""
    <div style='text-align:center; padding: 0.5rem 0 1rem 0;'>
        <div style='font-size:2rem;'>🏭</div>
        <div style='color:#F8FAFC; font-weight:800; font-size:1.1rem;'>{COMPANY_NAME}</div>
        <div style='color:#94A3B8; font-size:0.75rem;'>Enterprise Information System</div>
    </div>
    """)

    # Module status indicators
    srm_label = "🟢 SRM Active" if state.srm_enabled else "⚪ SRM Off"
    crm_label = "🟢 CRM Active" if state.crm_enabled else "⚪ CRM Off"
    st.html(f"""
    <div style='display:flex; gap:6px; justify-content:center; margin-bottom:1rem;'>
        <span class='badge-erp'>ERP</span>
        <span class='badge-{"srm" if state.srm_enabled else "off"}'>SRM{"✓" if state.srm_enabled else ""}</span>
        <span class='badge-{"crm" if state.crm_enabled else "off"}'>CRM{"✓" if state.crm_enabled else ""}</span>
    </div>
    """)

    st.divider()

    # Day progress
    c1, c2 = st.columns(2)
    c1.metric("Day", f"{state.current_day}/{state.max_days}")
    c2.metric("Cash", f"${state.cash:,.0f}")

    st.progress(min(1.0, state.current_day / state.max_days),
                text=f"Period: {min(state.current_day, state.max_days)}/{state.max_days} days")

    st.divider()

    # NEXT DAY button
    if not state.game_over:
        if st.button("➡️ ADVANCE DAY", type="primary", use_container_width=True):
            from Archive.ERP_Sim_Integrated.engine.srm_engine import update_supplier_prices
            update_supplier_prices(state)
            advance_day(state)
            st.rerun()
    else:
        st.error("🏁 Simulation Complete")
        
        from Archive.ERP_Sim_Integrated.engine.erp_engine import evaluate_performance
        perf = evaluate_performance(state)
        
        st.markdown(f"""
        <div style='background:#F8FAFC; padding:10px; border-radius:8px; border:1px solid #E2E8F0; margin-bottom:12px;'>
            <div style='font-weight:800; color:#1E293B; font-size:1.1rem;'>Final Grade: {perf["grade"]}</div>
            <div style='color:#64748B; font-size:0.85rem; margin-bottom:4px;'>Score: {perf["score"]}/100</div>
            <div style='font-size:0.8rem; color:#475569;'>{perf["summary"]}</div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("🔄 Reset Simulation", use_container_width=True):
            del st.session_state.sim_state
            st.rerun()

    st.divider()

    # =========================================================================
    # INSTRUCTOR SETTINGS (open, no password)
    # =========================================================================
    with st.expander("⚙️ Instructor Settings", expanded=False):
        st.html("<div style='color:#94A3B8; font-size:0.75rem; margin-bottom:8px;'>MODULE ACTIVATION</div>")

        col_srm, col_crm = st.columns(2)

        new_srm = col_srm.toggle("SRM", value=state.srm_enabled, help="Supplier Relationship Management")
        new_crm = col_crm.toggle("CRM", value=state.crm_enabled, help="Customer Relationship Management")

        if new_srm != state.srm_enabled:
            state.srm_enabled = new_srm
            if new_srm:
                st.toast("✅ SRM Module activated!", icon="🔗")
                state.daily_events.append("⚙️ INSTRUCTOR: SRM module activated")
            else:
                st.toast("SRM Module deactivated")
            st.rerun()

        if new_crm != state.crm_enabled:
            state.crm_enabled = new_crm
            if new_crm:
                # Initialize customers if first time
                if not state.customers:
                    from Archive.ERP_Sim_Integrated.engine.crm_engine import init_customers
                    init_customers(state)
                st.toast("✅ CRM Module activated!", icon="📊")
                state.daily_events.append("⚙️ INSTRUCTOR: CRM module activated")
            else:
                st.toast("CRM Module deactivated")
            st.rerun()

        st.divider()
        st.html("<div style='color:#94A3B8; font-size:0.75rem; margin-bottom:8px;'>QUICK ACTIONS</div>")
        jump = st.number_input("Advance N days", 1, 30, 1)
        if st.button("⏩ Auto-Run", use_container_width=True):
            from Archive.ERP_Sim_Integrated.engine.srm_engine import update_supplier_prices
            for _ in range(min(jump, state.max_days - state.current_day + 1)):
                if not state.game_over:
                    with st.spinner(f"Simulating Day {state.current_day}..."):
                        update_supplier_prices(state)
                        advance_day(state)
            
            # UX: Post-advance Summary Toasts
            delivered = len([e for e in state.daily_events if "Received PO" in e])
            orders = len([e for e in state.daily_events if "New order" in e])
            if delivered > 0:
                st.toast(f"📦 {delivered} Materials Delivered", icon="🚛")
            if orders > 0:
                st.toast(f"💰 {orders} New Customer Orders", icon="🛒")
            
            st.rerun()

        if st.button("🔄 Reset", use_container_width=True):
            del st.session_state.sim_state
            st.rerun()

    # Unread inbox count
    if not state.crm_enabled or not state.srm_enabled:
        unread = len([m for m in state.inbox if not m.is_read])
        if unread > 0:
            st.html(f"<div style='color:#F59E0B; font-weight:600; margin-top:8px;'>📬 {unread} unread messages</div>")


# =============================================================================
# NAVIGATION PAGES
# =============================================================================
pages = [
    st.Page("pages/01_dashboard.py",   title="📊 Dashboard",   icon="📊", default=True),
    st.Page("pages/02_production.py",  title="🏗️ Production",  icon="🏗️"),
    st.Page("pages/03_inventory.py",   title="📦 Inventory",   icon="📦"),
    st.Page("pages/04_procurement.py", title="🛒 Procurement", icon="🛒"),
    st.Page("pages/05_sales.py",       title="📈 Sales",       icon="📈"),
    st.Page("pages/06_finance.py",     title="💰 Finance",     icon="💰"),
    st.Page("pages/08_reports.py",     title="📑 Reports",     icon="📑"),
]

pg = st.navigation(pages)
pg.run()
