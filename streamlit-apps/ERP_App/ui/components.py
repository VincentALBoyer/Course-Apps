"""Shared widgets used across every module page: the persistent topbar (day
counter, headline KPIs, Advance Day control) and small markup helpers.
"""

import streamlit as st

from game_engine import SUPPLIERS, GameState, advance_day, get_kpis
from ui.report import build_pdf


def _game_state() -> GameState:
    return st.session_state.game_state


def render_topbar() -> None:
    """Renders the company header, headline KPI strip and the Advance Day /
    Restart control. Called once from app.py, above the page navigation, so
    it is identical and always visible on every module."""
    state = _game_state()
    kpis = get_kpis(state)

    h1, h2 = st.columns([0.7, 0.3])
    with h1:
        st.markdown('<div class="erp-eyebrow">Global Gadgets Inc. &middot; Unified Business System</div>', unsafe_allow_html=True)
        st.markdown(f"### 🏭 ERP Sim — Day {state.current_day} / {state.max_days}")
        st.progress(min(state.current_day / state.max_days, 1.0))
    with h2:
        st.write("")
        if state.game_over:
            st.error(f"Simulation complete — Net Profit: ${kpis['profit']:,.0f}")
            if st.button("Restart Simulation", width='stretch'):
                for key in ("game_state", "onboarded", "student_name", "student_id"):
                    st.session_state.pop(key, None)
                st.rerun()
        else:
            if st.button("▶️ Advance to Next Day", type="primary", width='stretch'):
                qtys = {sid: st.session_state.get(f"ord_{sid}", 0) for sid in SUPPLIERS}
                advance_day(state, qtys)
                for sid in SUPPLIERS:
                    st.session_state[f"ord_{sid}"] = 0
                st.rerun()

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("💰 Net Profit", f"${kpis['profit']:,.0f}")
    m2.metric("💵 Cash", f"${kpis['cash']:,.0f}")
    m3.metric("📦 On-Hand Stock", f"{kpis['inventory']}")
    m4.metric("⏳ Open Sales Orders", f"{kpis['orders_pending']}")
    m5.metric("🚚 Inbound Purchase Orders", f"{kpis['incoming_qty']}")

    if state.game_over:
        student_name = st.session_state.get("student_name", "").strip() or "Unnamed Student"
        student_id = st.session_state.get("student_id", "").strip() or "unknown"
        pdf_bytes = build_pdf(state, student_name, student_id)
        st.download_button(
            "📄 Download Performance Report (PDF) — submit for grading",
            data=pdf_bytes,
            file_name=f"erp_sim_report_{student_id}.pdf",
            mime="application/pdf",
            type="primary",
            width="stretch",
        )

    st.divider()


def explainer_strip(module_name: str, body: str) -> None:
    """Small left-accent banner used at the top of each module page to name
    what real-world ERP module this screen represents and why it matters."""
    st.markdown(
        f'<div class="erp-strip"><b>{module_name}</b> — {body}</div>',
        unsafe_allow_html=True,
    )


def flow_diagram() -> None:
    """The 'what is an ERP' visual: four modules, one shared database."""
    st.markdown(
        """
        <div class="erp-flow">
            <div class="erp-flow-node">🚚<br>SRM<br><span style="font-weight:400;opacity:0.7;">Suppliers</span></div>
            <div class="erp-flow-arrow">⇄</div>
            <div class="erp-flow-node">📦<br>Inventory &amp; Ops<br><span style="font-weight:400;opacity:0.7;">Warehouse</span></div>
            <div class="erp-flow-arrow">⇄</div>
            <div class="erp-flow-node">🤝<br>CRM<br><span style="font-weight:400;opacity:0.7;">Customers</span></div>
            <div class="erp-flow-arrow">⇄</div>
            <div class="erp-flow-node">💰<br>Finance<br><span style="font-weight:400;opacity:0.7;">Ledger</span></div>
        </div>
        <div class="erp-flow-center">All four modules read and write the <b>same</b> shared data store in real time — that single source of truth is what defines an ERP, as opposed to four separate spreadsheets or standalone apps.</div>
        """,
        unsafe_allow_html=True,
    )
