# =============================================================================
# Page 02 — Production (Factory Floor)
# =============================================================================
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from Archive.ERP_Sim_Integrated.engine.erp_engine import create_work_order

if "sim_state" not in st.session_state:
    st.warning("Simulation state not initialized. Please go to the Home page first.")
    st.stop()

state = st.session_state.sim_state

st.html("""
<div class='page-header'>
    <h2>🏗️ Production Management</h2>
    <p>Factory floor — schedule production runs, monitor capacity & work-in-progress</p>
</div>
""")

# ── Capacity KPIs ─────────────────────────────────────────────────────────────
from Archive.ERP_Sim_Integrated.config import DAILY_CAPACITY_HOURS
active_wos = [wo for wo in state.work_orders if wo.status == "InProgress"]
backlog_hours = sum(wo.hours_required - wo.hours_completed for wo in active_wos)
completed_today = [wo for wo in state.work_orders if wo.status == "Completed" and wo.completion_day == state.current_day - 1]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Daily Capacity", f"{DAILY_CAPACITY_HOURS} hrs")
c2.metric("Active Work Orders", len(active_wos))
c3.metric("Backlog Hours", backlog_hours,
          delta=f"≈ {backlog_hours // DAILY_CAPACITY_HOURS} days" if backlog_hours > 0 else None,
          delta_color="inverse" if backlog_hours > DAILY_CAPACITY_HOURS * 2 else "normal")
c4.metric("FG in Stock", sum(state.stock_finished.values()))

st.divider()

# ── Schedule New Production ────────────────────────────────────────────────────
st.html("<div class='section-title'>🔨 Schedule New Production Run</div>")

col_form, col_check = st.columns([1, 1])

with col_form:
    prod_id = st.selectbox("Select Product", list(state.products.keys()),
                            format_func=lambda x: f"{state.products[x].name} ({state.products[x].category})")
    qty = st.number_input("Quantity", min_value=1, max_value=200, value=10, step=5)
    prod = state.products[prod_id]
    st.caption(f"💰 Selling price: **${prod.price:.2f}** | ⏱️ Production time: **{prod.production_hours * qty} hrs**")
    start_btn = st.button("▶️ Start Production", type="primary", use_container_width=True)

with col_check:
    st.caption("📋 **Bill of Materials Check**")
    can_produce = True
    bom_rows = []
    for mid, per_unit in prod.bom.items():
        mat = state.materials[mid]
        total_needed = per_unit * qty
        avail = state.stock_materials.get(mid, 0)
        ok = avail >= total_needed
        if not ok:
            can_produce = False
        bom_rows.append({
            "Material": mat.name,
            "Required": total_needed,
            "Available": avail,
            "Status": "✅ OK" if ok else f"❌ Short {total_needed - avail}",
        })
    st.dataframe(pd.DataFrame(bom_rows), use_container_width=True, hide_index=True)
    if can_produce:
        st.success("✅ All materials available — ready to produce!")
    else:
        st.error("⚠️ Insufficient materials. Go to Procurement to buy.")

if start_btn:
    if not can_produce:
        st.error("Cannot start — material shortage. Check Procurement.")
    else:
        ok, msg = create_work_order(state, prod_id, qty)
        if ok:
            st.success(f"✅ Work Order started: {qty}x {prod.name} (ID: {msg})")
            st.rerun()
        else:
            st.error(msg)

st.divider()

# ── Work In Progress ──────────────────────────────────────────────────────────
st.html("<div class='section-title'>⚙️ Work In Progress</div>")

if not active_wos:
    st.info("🏖️ Factory floor is idle — schedule production above.")
else:
    # Capacity load bar
    capacity_used = min(backlog_hours, DAILY_CAPACITY_HOURS)
    load_pct = capacity_used / DAILY_CAPACITY_HOURS
    bar_color = "green" if load_pct < 0.7 else ("orange" if load_pct < 1.0 else "red")
    st.progress(min(1.0, load_pct),
                text=f"Capacity Load: {capacity_used}/{DAILY_CAPACITY_HOURS} hrs today ({load_pct*100:.0f}%)")

    # WIP Chart
    st.markdown("📊 **Production Timeline**")
    wip_data = []
    for wo in active_wos:
        prod = state.products[wo.product_id]
        pct = (wo.hours_completed / wo.hours_required) * 100
        wip_data.append({"WO": wo.id, "Product": prod.name, "Progress (%)": pct, "Qty": wo.qty})
    
    if wip_data:
        df_wip = pd.DataFrame(wip_data)
        fig_wip = px.bar(df_wip, x="Progress (%)", y="WO", orientation='h',
                         hover_data=["Product", "Qty"],
                         color="Progress (%)", color_continuous_scale="RdYlGn",
                         range_x=[0, 100],
                         title="Active Jobs Completion Status")
        fig_wip.update_layout(height=max(200, len(wip_data)*40), margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig_wip, use_container_width=True)

    for wo in active_wos:
        prod = state.products[wo.product_id]
        pct = wo.hours_completed / wo.hours_required
        days_est = max(0, (wo.hours_required - wo.hours_completed) // DAILY_CAPACITY_HOURS)

        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([2, 1, 1, 2])
            c1.markdown(f"**{wo.id}** — {wo.qty}x {prod.name}")
            c1.caption(f"Started Day {wo.day_started}")
            c2.metric("Progress", f"{int(pct*100)}%")
            c3.metric("Est. Days Left", days_est)
            c4.progress(pct, text=f"{wo.hours_completed}/{wo.hours_required} hrs")

st.divider()

# ── Completed Work Orders ──────────────────────────────────────────────────────
st.html("<div class='section-title'>✅ Completed (Last 10)</div>")
done_wos = [wo for wo in state.work_orders if wo.status == "Completed"]
if done_wos:
    done_wos_sorted = sorted(done_wos, key=lambda x: x.completion_day, reverse=True)[:10]
    rows = []
    for wo in done_wos_sorted:
        prod = state.products[wo.product_id]
        rows.append({
            "WO ID": wo.id, "Product": prod.name, "Qty": wo.qty,
            "Started": f"Day {wo.day_started}", "Completed": f"Day {wo.completion_day}",
            "Lead Time (days)": wo.completion_day - wo.day_started,
            "Rework Cost": f"${wo.rework_cost:.0f}" if wo.rework_cost > 0 else "—",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
else:
    st.caption("No completed work orders yet.")

st.divider()

# ── MRP Suggestions ────────────────────────────────────────────────────────────
from Archive.ERP_Sim_Integrated.engine.erp_engine import run_mrp_suggestion
st.html("<div class='section-title'>🤖 MRP — Replenishment Suggestions</div>")
suggestions = run_mrp_suggestion(state)
if suggestions:
    for s in suggestions:
        urgency_cls = "alert-red" if s["urgency"] == "High" else "alert-amber"
        st.markdown(
            f"<div class='{urgency_cls}'>"
            f"<b>{s['urgency']} Priority</b> — {s['material_name']}: "
            f"Stock={s['current_stock']}, Inbound={s['inbound']}, "
            f"7-Day Demand={s['projected_demand_7d']} → "
            f"<b>Order ≥ {s['suggested_qty']} units</b>"
            f"</div>",
            unsafe_allow_html=True
        )
else:
    st.html("<div class='alert-green'>✅ Inventory looks adequate for the next 7 days based on demand trends.</div>")
