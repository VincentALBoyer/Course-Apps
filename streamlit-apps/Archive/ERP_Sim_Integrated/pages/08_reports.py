# =============================================================================
# Page 08 — Reports & KPI Downloads
# =============================================================================
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from Archive.ERP_Sim_Integrated.engine.erp_engine import export_activity_log, export_kpi_summary, get_kpis, get_income_statement

if "sim_state" not in st.session_state:
    st.warning("Simulation state not initialized. Please go to the Home page first.")
    st.stop()

state = st.session_state.sim_state
kpis = get_kpis(state)
inc = get_income_statement(state)

st.html("""
<div class='page-header'>
    <h2>📑 Reports & KPI Analysis</h2>
    <p>Download activity logs and KPI summaries for your analysis assignments</p>
</div>
""")

# ── Download Zone ─────────────────────────────────────────────────────────────
st.html("<div class='section-title'>📥 Data Exports</div>")
d1, d2, d3 = st.columns(3)

with d1:
    with st.container(border=True):
        st.markdown("#### 📋 Full Activity Log")
        st.caption("Every action, event, and financial transaction. Use for KPI analysis in Excel/Python.")
        st.caption(f"**{len(state.activity_log)} events recorded**")
        csv_log = export_activity_log(state)
        st.download_button(
            label="⬇️ Download Activity Log (CSV)",
            data=csv_log,
            file_name=f"eis_activity_log_day{state.current_day}.csv",
            mime="text/csv",
            use_container_width=True,
            type="primary",
        )

with d2:
    with st.container(border=True):
        st.markdown("#### 📊 KPI Summary")
        st.caption("Pre-computed KPIs per module. Quick-start for your performance analysis report.")
        csv_kpi = export_kpi_summary(state)
        st.download_button(
            label="⬇️ Download KPI Summary (CSV)",
            data=csv_kpi,
            file_name=f"eis_kpi_summary_day{state.current_day}.csv",
            mime="text/csv",
            use_container_width=True,
            type="primary",
        )

with d3:
    with st.container(border=True):
        st.markdown("#### 🏭 Transaction Details")
        st.caption("All Sales Orders, Work Orders, and Purchase Orders as raw tables.")
        # Build combined transactions CSV
        so_rows = [{"type": "SalesOrder", "id": so.id, "day": so.day_placed,
                    "customer": so.customer_name, "product": so.product_id,
                    "qty": so.qty, "value": so.qty * so.unit_price, "status": so.status,
                    "shipped_day": so.shipped_day} for so in state.sales_orders]
        po_rows = [{"type": "PurchaseOrder", "id": po.id, "day": po.day_placed,
                    "supplier": po.supplier_id, "material": po.material_id,
                    "qty": po.qty, "value": po.qty * po.unit_cost, "status": po.status,
                    "arrival_day": po.expected_arrival_day} for po in state.purchase_orders]
        wo_rows = [{"type": "WorkOrder", "id": wo.id, "day": wo.day_started,
                    "product": wo.product_id, "qty": wo.qty,
                    "status": wo.status, "completion_day": wo.completion_day} for wo in state.work_orders]
        combined = pd.DataFrame(so_rows + po_rows + wo_rows)
        csv_tx = combined.to_csv(index=False)
        st.download_button(
            label="⬇️ Download Transactions (CSV)",
            data=csv_tx,
            file_name=f"eis_transactions_day{state.current_day}.csv",
            mime="text/csv",
            use_container_width=True,
        )

st.divider()

# ── Simulated Data Zone ───────────────────────────────────────────────────────
st.html("<div class='section-title'>🧪 Simulated Event Logs (For Analysis)</div>")
st.caption("Use these pre-generated datasets to practice Data Science analysis without playing a full 30-day simulation manually.")

sim1, sim2 = st.columns(2)
with sim1:
    with st.container(border=True):
        st.markdown("#### ✅ Optimized Operations (High Integration)")
        st.caption("A simulated 30-day log representing a company actively using SRM and CRM modules. Features high revenue and low rework costs.")
        from Archive.ERP_Sim_Integrated.engine.erp_engine import generate_simulated_log
        csv_opt = generate_simulated_log(scenario="optimized")
        st.download_button("⬇️ Download Optimized Log (CSV)", data=csv_opt, file_name="simulated_log_optimized.csv", mime="text/csv", use_container_width=True)

with sim2:
    with st.container(border=True):
        st.markdown("#### ❌ Siloed Operations (No Integration)")
        st.caption("A simulated 30-day log representing a company doing manual emails. Features lower order volume, higher material spend, and quality issues.")
        csv_unopt = generate_simulated_log(scenario="unoptimized")
        st.download_button("⬇️ Download Siloed Log (CSV)", data=csv_unopt, file_name="simulated_log_siloed.csv", mime="text/csv", use_container_width=True)

st.divider()

# ── Live KPI Dashboard ────────────────────────────────────────────────────────
st.html("<div class='section-title'>📈 Live KPI Dashboard</div>")

tab_erp, tab_srm, tab_crm = st.tabs(["🏭 ERP KPIs", "🔗 SRM KPIs", "📊 CRM KPIs"])

with tab_erp:
    erp_kpis = [
        ("Revenue", f"${inc['revenue']:,.0f}", "Total income from shipped orders"),
        ("Cost of Goods Sold", f"${inc['cogs']:,.0f}", "Material cost of shipped products"),
        ("Gross Profit", f"${inc['gross_profit']:,.0f}", f"Margin: {inc['gross_margin_pct']:.1f}%"),
        ("Net Income", f"${inc['net_income']:,.0f}", f"Net margin: {inc['net_margin_pct']:.1f}%"),
        ("Cash Balance", f"${state.cash:,.0f}", "Current liquid assets"),
        ("OTIF %", f"{kpis['otif_pct']:.1f}%", "On-Time In-Full delivery rate"),
        ("Orders Shipped", kpis["shipped_orders"], "Successfully fulfilled orders"),
        ("Lost/Cancelled", kpis["cancelled_orders"], "Orders lost due to stockouts or delays"),
        ("Rework Cost", f"${kpis['total_rework']:,.0f}", "Quality failures in production & supply"),
        ("Stockout Penalties", f"${kpis['total_penalties']:,.0f}", "Revenue lost from unfilled orders"),
        ("Inventory (Raw)", f"${kpis['inventory_value_raw']:,.0f}", "Raw material stock value"),
        ("Inventory (FG)", f"${kpis['inventory_value_fg']:,.0f}", "Finished goods stock value"),
    ]
    c1, c2, c3, c4 = st.columns(4)
    for i, (name, val, help) in enumerate(erp_kpis):
        [c1, c2, c3, c4][i % 4].metric(name, val, help=help)

    if len(state.daily_snapshots) >= 2:
        st.divider()
        df_snap = pd.DataFrame(state.daily_snapshots)
        fig = px.line(df_snap, x="day",
                      y=["open_orders", "stock_raw", "stock_fg", "wip"],
                      title="Operational Trend",
                      labels={"value": "Units", "day": "Day", "variable": "Metric"},
                      color_discrete_sequence=["#1A56DB", "#EF4444", "#10B981", "#F59E0B"])
        fig.update_layout(height=280, paper_bgcolor="white", plot_bgcolor="white",
                          margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig, use_container_width=True)

with tab_srm:
    if not state.srm_enabled:
        st.info("SRM module is not enabled. Enable it from the Instructor Settings in the sidebar to see SRM KPIs.")
        st.markdown("**What you're missing without SRM:**")
        col1, col2 = st.columns(2)
        col1.markdown("""
        - ❌ No RFQ automation — manual email requests with 1-day delay
        - ❌ No supplier comparison matrix
        - ❌ No contract management
        - ❌ No automated 3-way match
        - ❌ No supplier scorecards
        - ❌ Higher procurement costs (no negotiation leverage)
        """)
        col2.markdown("""
        **With SRM enabled:**
        - ✅ Instant multi-supplier quotes
        - ✅ Data-driven supplier selection
        - ✅ Contract pricing for volume commitments
        - ✅ AP invoice tracking with early payment discounts
        - ✅ Supplier performance scorecards
        - ✅ Automated discrepancy alerts
        """)
    else:
        from Archive.ERP_Sim_Integrated.engine.srm_engine import get_srm_kpis
        srm_kpis_data = get_srm_kpis(state)
        kpi_cols = st.columns(3)
        for i, (name, val) in enumerate(srm_kpis_data.items()):
            kpi_cols[i % 3].metric(name, val)

        # Supplier comparison chart
        if state.suppliers:
            sup_data = []
            for sid, sup in state.suppliers.items():
                sup_data.append({
                    "Supplier": sup.name, "Relationship Score": sup.relationship_score,
                    "Quality Rate": sup.quality_rate * 100, "Reliability": sup.reliability * 100,
                })
            df_sup = pd.DataFrame(sup_data)
            fig_sup = px.bar(df_sup.melt(id_vars="Supplier",
                                          value_vars=["Relationship Score", "Quality Rate", "Reliability"]),
                              x="Supplier", y="value", color="variable", barmode="group",
                              title="Supplier Performance Comparison",
                              color_discrete_sequence=["#7E3AF2", "#10B981", "#1A56DB"])
            fig_sup.update_layout(height=300, paper_bgcolor="white", plot_bgcolor="white",
                                   margin=dict(l=0, r=0, t=40, b=0))
            st.plotly_chart(fig_sup, use_container_width=True)

with tab_crm:
    if not state.crm_enabled:
        st.info("CRM module is not enabled. Enable it from the Instructor Settings in the sidebar to see CRM KPIs.")
        st.markdown("**What you're missing without CRM:**")
        col1, col2 = st.columns(2)
        col1.markdown("""
        - ❌ No lead qualification pipeline
        - ❌ No win rate tracking
        - ❌ Customer orders arrive anonymously by email
        - ❌ No customer health scores
        - ❌ No marketing campaign ROI tracking
        - ❌ No service desk integration
        """)
        col2.markdown("""
        **With CRM enabled:**
        - ✅ Full Kanban sales pipeline
        - ✅ Campaign → Lead → Opportunity → Sale flow
        - ✅ Customer 360° view (CSAT, LTV, churn risk)
        - ✅ Automatic ERP order creation from Won deals
        - ✅ Service ticket management
        - ✅ Win rate and CAC analytics
        """)
    else:
        from Archive.ERP_Sim_Integrated.engine.crm_engine import get_crm_kpis
        crm_kpis_data = get_crm_kpis(state)
        kpi_cols = st.columns(3)
        for i, (name, val) in enumerate(crm_kpis_data.items()):
            kpi_cols[i % 3].metric(name, val)

        # Pipeline stage distribution
        from Archive.ERP_Sim_Integrated.engine.crm_engine import STAGE_ORDER
        stage_counts = {s: 0 for s in STAGE_ORDER}
        for l in state.leads:
            stage_counts[l.stage] = stage_counts.get(l.stage, 0) + 1
        stage_df = pd.DataFrame({"Stage": list(stage_counts.keys()), "Count": list(stage_counts.values())})
        fig_pipe = px.funnel(stage_df, x="Count", y="Stage",
                              title="Sales Pipeline Funnel",
                              color_discrete_sequence=["#0E9F6E"])
        fig_pipe.update_layout(height=300, paper_bgcolor="white",
                                margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig_pipe, use_container_width=True)

st.divider()

# ── Class Activity Summary ─────────────────────────────────────────────────────
st.html("<div class='section-title'>🎓 Simulation Summary</div>")
summary_data = {
    "Simulation Day": state.current_day,
    "ERP Enabled": "✅ Always",
    "SRM Module": "✅ Active" if state.srm_enabled else "❌ Disabled",
    "CRM Module": "✅ Active" if state.crm_enabled else "❌ Disabled",
    "Total Transactions": len(state.sales_orders) + len(state.purchase_orders) + len(state.work_orders),
    "Activity Log Events": len(state.activity_log),
    "Net Income": f"${inc['net_income']:,.0f}",
    "Final Cash": f"${state.cash:,.0f}",
}
for k, v in summary_data.items():
    st.write(f"**{k}:** {v}")
