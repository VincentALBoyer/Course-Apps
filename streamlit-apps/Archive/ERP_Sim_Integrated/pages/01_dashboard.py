# =============================================================================
# Page 01 — Executive Dashboard
# =============================================================================
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from Archive.ERP_Sim_Integrated.engine.erp_engine import get_kpis, get_income_statement

if "sim_state" not in st.session_state:
    st.warning("Simulation state not initialized. Please go to the Home page first.")
    st.stop()

state = st.session_state.sim_state
kpis = get_kpis(state)
inc = get_income_statement(state)

st.html("""
<div class='page-header'>
    <h2>📊 Executive Dashboard</h2>
    <p>Real-time business performance overview</p>
</div>
""")

# ── Pedagogical Session Banner ────────────────────────────────────────────────
if state.crm_enabled:
    st.info("""**Session 3: Total Integration (ERP + SRM + CRM)**

Your goal is to maximize profitability using full automation. Focus on the CRM Sales Pipeline to convert leads into orders automatically, and manage Customer Service tickets to maintain high satisfaction.""", icon="🎯")
elif state.srm_enabled:
    st.info("""**Session 2: Enhancing Procurement (ERP + SRM)**

Your goal is to optimize purchasing. The SRM module gives you access to the Daily Market, Supplier Contracts, and automated AP Invoices. No more manual emails!""", icon="🎯")
else:
    st.warning("""**Session 1: Siloed Operations (ERP Only)**

Your goal is to survive manual operations. You must use the Procurement and Sales email inboxes to manually request quotes, accept orders, and convert data into the ERP system. It is slow and cumbersome by design.""", icon="🎯")


# ── Module status banner ──────────────────────────────────────────────────────
m1, m2, m3 = st.columns(3)
with m1:
    st.markdown("<span class='badge-erp'>ERP</span> **Core Active** — Inventory, Production, Finance", unsafe_allow_html=True)
with m2:
    if state.srm_enabled:
        st.markdown("<span class='badge-srm'>SRM</span> **Supplier Portal Active**", unsafe_allow_html=True)
    else:
        st.markdown("<span class='badge-off'>SRM</span> *Disabled — Manual procurement*", unsafe_allow_html=True)
with m3:
    if state.crm_enabled:
        st.markdown("<span class='badge-crm'>CRM</span> **Customer Pipeline Active**", unsafe_allow_html=True)
    else:
        st.markdown("<span class='badge-off'>CRM</span> *Disabled — Manual sales order entry*", unsafe_allow_html=True)

st.divider()

# ── Core KPIs ─────────────────────────────────────────────────────────────────
kpis = get_kpis(state)
cash_delta = state.daily_snapshots[-1]["cash"] - state.daily_snapshots[-2]["cash"] if len(state.daily_snapshots) > 1 else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Cash Balance", f"${state.cash:,.0f}", 
          delta=f"${cash_delta:,.0f}" if cash_delta != 0 else None)
c2.metric("Net Income", f"${inc['net_income']:,.0f}", 
          delta=f"{inc['net_margin_pct']:.1f}% Margin")
c3.metric("Inventory Value", f"${sum(state.stock_materials.values())*5 + sum(state.stock_finished.values())*50:,.0f}") # Approx
c4.metric("Open Orders", len([so for so in state.sales_orders if so.status == "Open"]))

st.divider()

# ── Smart Strategy Suggestion ─────────────────────────────────────────────────
low_mats = [m for m, qty in state.stock_materials.items() if qty < state.materials[m].reorder_point]
high_demand = len([so for so in state.sales_orders if so.status == "Open"])

with st.container(border=True):
    st.markdown("💡 **Instructor's Strategy Tip**")
    if not state.game_over:
        if low_mats:
            st.warning(f"⚠️ **Supply Chain Alert**: You are low on {len(low_mats)} materials ({', '.join(low_mats)}). Visit **Procurement** to replenish.")
        elif high_demand > 5:
            st.info(f"📈 **Demand is High**: You have {high_demand} open orders. Ensure **Production** is running and you have enough Finished Goods.")
        elif state.cash < 5000:
            st.error("📉 **Cash is Low**: Monitor your Operating Expenses in **Finance**. Try to fulfill open orders faster to get paid.")
        else:
            st.success("✨ **Operations Healthy**: All systems stable. Advance the day to see new market opportunities.")
    else:
        st.info("🏁 **Simulation Complete**: Review your performance report and download the event logs.")

st.divider()

# ── KPI Row 1: Financial ──────────────────────────────────────────────────────
st.html("<div class='section-title'>💰 Financial KPIs</div>")
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Cash", f"${kpis['cash']:,.0f}")
k2.metric("Revenue", f"${kpis['revenue']:,.0f}")
k3.metric("Net Income", f"${kpis['net_income']:,.0f}",
          delta=f"{inc['net_margin_pct']:.1f}% margin" if kpis['revenue'] > 0 else None)
k4.metric("Total Penalties", f"${kpis['total_penalties']:,.0f}",
          delta="Lost sales" if kpis['total_penalties'] > 0 else None,
          delta_color="inverse")
k5.metric("Rework Cost", f"${kpis['total_rework']:,.0f}",
          delta="Quality issues" if kpis['total_rework'] > 0 else None,
          delta_color="inverse")

# ── KPI Row 2: Operations ─────────────────────────────────────────────────────
st.html("<div class='section-title'>🏗️ Operational KPIs</div>")
op1, op2, op3, op4, op5 = st.columns(5)
op1.metric("Open Orders", kpis["open_orders"])
op2.metric("Shipped", kpis["shipped_orders"])
op3.metric("OTIF %", f"{kpis['otif_pct']:.1f}%",
           delta="On-Time In-Full" if kpis["shipped_orders"] > 0 else None)
op4.metric("WIP Jobs", kpis["wip_count"])
op5.metric("Inventory (Raw)", f"${kpis['inventory_value_raw']:,.0f}")

st.divider()

# ── Charts ────────────────────────────────────────────────────────────────────
c_chart, c_log = st.columns([3, 2])

with c_chart:
    st.html("<div class='section-title'>📈 Performance Trend</div>")
    if len(state.daily_snapshots) >= 2:
        df = pd.DataFrame(state.daily_snapshots)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["day"], y=df["revenue"], name="Revenue",
                                  line=dict(color="#1A56DB", width=2.5)))
        fig.add_trace(go.Scatter(x=df["day"], y=df["costs"], name="Costs",
                                  line=dict(color="#EF4444", width=2, dash="dash")))
        fig.add_trace(go.Scatter(x=df["day"], y=df["profit"], name="Net Profit",
                                  fill="tozeroy", line=dict(color="#10B981", width=2),
                                  fillcolor="rgba(16,185,129,0.1)"))
        fig.update_layout(
            height=300, paper_bgcolor="white", plot_bgcolor="white",
            margin=dict(l=10, r=10, t=20, b=30),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis=dict(title="Day", gridcolor="#F1F5F9"),
            yaxis=dict(title="$", gridcolor="#F1F5F9"),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Advance a few days to see performance trend charts.")

with c_log:
    st.html("<div class='section-title'>📢 Today's Activity Feed</div>")
    with st.container(height=310):
        if state.daily_events:
            for ev in reversed(state.daily_events):
                if "⚠️" in ev or "❌" in ev or "🚫" in ev:
                    cls = "alert-red"
                elif "✅" in ev or "🚚" in ev or "🏆" in ev:
                    cls = "alert-green"
                elif "💸" in ev or "📋" in ev or "🔧" in ev:
                    cls = "alert-blue"
                else:
                    cls = "alert-amber"
                st.html(f"<div class='{cls}'>{ev}</div>")
        else:
            st.caption("Advance a day to see activity here.")

st.divider()

# ── Inventory Overview ────────────────────────────────────────────────────────
st.html("<div class='section-title'>📦 Inventory Snapshot</div>")
c_raw, c_fg = st.columns(2)

with c_raw:
    st.caption("🧱 **Raw Materials**")
    raw_rows = []
    for mid, mat in state.materials.items():
        qty = state.stock_materials.get(mid, 0)
        status = "🔴 LOW" if qty <= mat.reorder_point else ("🟡 OK" if qty <= mat.reorder_point * 2 else "🟢 Good")
        raw_rows.append({
            "Material": mat.name, "Qty": qty, "Unit": mat.unit,
            "Reorder Pt": mat.reorder_point, "Status": status,
            "Value": f"${qty * mat.cost:.0f}"
        })
    st.dataframe(pd.DataFrame(raw_rows), use_container_width=True, hide_index=True)

with c_fg:
    st.caption("🚲 **Finished Goods**")
    fg_rows = []
    for pid, prod in state.products.items():
        qty = state.stock_finished.get(pid, 0)
        open_demand = sum(so.qty for so in state.sales_orders
                          if so.product_id == pid and so.status == "Open")
        coverage = "✅ Covered" if qty >= open_demand else f"⚠️ Short by {open_demand - qty}"
        fg_rows.append({
            "Product": prod.name, "In Stock": qty,
            "Open Demand": open_demand, "Coverage": coverage,
            "Value": f"${qty * prod.price:.0f}"
        })
    st.dataframe(pd.DataFrame(fg_rows), use_container_width=True, hide_index=True)
