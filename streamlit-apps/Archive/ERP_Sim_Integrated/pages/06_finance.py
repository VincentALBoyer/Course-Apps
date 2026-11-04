# =============================================================================
# Page 06 — Finance & Accounting
# =============================================================================
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from Archive.ERP_Sim_Integrated.engine.erp_engine import get_income_statement, get_kpis

if "sim_state" not in st.session_state:
    st.warning("Simulation state not initialized. Please go to the Home page first.")
    st.stop()

state = st.session_state.sim_state
inc = get_income_statement(state)
kpis = get_kpis(state)

st.html("""
<div class='page-header'>
    <h2>💰 Finance & Accounting</h2>
    <p>Income statement, cash flow, AR/AP aging, and balance sheet snapshot</p>
</div>
""")

tab_pl, tab_cf, tab_arap, tab_ledger = st.tabs([
    "📊 P&L Statement", "💵 Cash Flow", "📋 AR/AP Aging", "🗂️ General Ledger"
])

# ── P&L ───────────────────────────────────────────────────────────────────────
with tab_pl:
    st.html("<div class='section-title'>Income Statement (Cumulative)</div>")
    c_pl, c_chart = st.columns([1, 2])

    with c_pl:
        def pl_row(label, val, indent=0, bold=False, color=None):
            prefix = "&nbsp;" * (indent * 4)
            style = "font-weight:700;" if bold else ""
            color_style = f"color:{color};" if color else ""
            sign = "+" if val > 0 else ""
            st.markdown(f"<div style='{style}{color_style}padding:4px 0; font-size:0.92rem;'>"
                        f"{prefix}{label}: {sign}${val:,.0f}</div>", unsafe_allow_html=True)

        pl_row("Revenue", inc["revenue"], bold=True, color="#1A56DB")
        pl_row("Cost of Goods Sold (COGS)", -inc["cogs"], indent=1)
        pl_row("Gross Profit", inc["gross_profit"], bold=True,
               color="#10B981" if inc["gross_profit"] >= 0 else "#EF4444")
        st.html("<hr style='margin:4px 0;border-color:#E2E8F0;'>")
        pl_row("Operating Expenses", 0, bold=True)
        pl_row("— Overhead (rent, wages)", -inc["overhead"], indent=2)
        pl_row("— Rework (quality issues)", -inc["rework_cost"], indent=2,
               color="#EF4444" if inc["rework_cost"] > 0 else None)
        pl_row("— Storage Costs", -inc["storage_cost"], indent=2)
        if state.crm_enabled:
            pl_row("— Marketing Spend (CRM)", -inc["marketing_spend"], indent=2)
        pl_row("Total OpEx", -inc["total_opex"], indent=1, bold=True)
        st.html("<hr style='margin:4px 0;border-color:#E2E8F0;'>")
        pl_row("EBIT", inc["ebit"], bold=True,
               color="#10B981" if inc["ebit"] >= 0 else "#EF4444")
        pl_row("— Lost Sale Penalties", -inc["penalties"], indent=1,
               color="#EF4444" if inc["penalties"] > 0 else None)
        pl_row("NET INCOME", inc["net_income"], bold=True,
               color="#10B981" if inc["net_income"] >= 0 else "#EF4444")
        gross_m = f"{inc['gross_margin_pct']:.1f}%"
        net_m = f"{inc['net_margin_pct']:.1f}%"
        st.markdown(f"<div style='background:#F1F5F9; padding:8px; border-radius:6px; margin-top:8px; font-size:0.85rem;'>"
                    f"Gross Margin: <b>{gross_m}</b> | Net Margin: <b>{net_m}</b></div>",
                    unsafe_allow_html=True)

    with c_chart:
        # Waterfall
        labels = ["Revenue", "COGS", "Gross Profit", "Operating Expenses", "Penalties", "Net Income"]
        values = [inc["revenue"], -inc["cogs"], inc["gross_profit"], -inc["total_opex"], -inc["penalties"], inc["net_income"]]
        # Use more professional color palette
        colors = ["#1A56DB", "#DC2626", "#059669", "#D97706", "#EF4444",
                  "#059669" if inc["net_income"] >= 0 else "#DC2626"]
        fig = go.Figure(go.Bar(x=labels, y=values, marker_color=colors,
                                text=[f"${abs(v):,.0f}" for v in values],
                                textposition="outside"))
        fig.update_layout(
            title="P&L Waterfall", height=350,
            paper_bgcolor="white", plot_bgcolor="white",
            margin=dict(l=10, r=10, t=40, b=10),
            showlegend=False,
            yaxis=dict(gridcolor="#F1F5F9"),
        )
        st.plotly_chart(fig, use_container_width=True)

# ── Cash Flow ─────────────────────────────────────────────────────────────────
with tab_cf:
    st.html("<div class='section-title'>Cash Balance Trend</div>")
    if state.daily_snapshots:
        df_cf = pd.DataFrame(state.daily_snapshots)
        fig_cf = go.Figure()
        fig_cf.add_trace(go.Scatter(
            x=df_cf["day"], y=df_cf["cash"], name="Cash Balance",
            fill="tozeroy", line=dict(color="#1A56DB", width=2.5),
            fillcolor="rgba(26,86,219,0.08)"
        ))
        fig_cf.add_hline(y=0, line_dash="dash", line_color="#EF4444", annotation_text="Zero")
        fig_cf.update_layout(
            height=320, paper_bgcolor="white", plot_bgcolor="white",
            margin=dict(l=10, r=10, t=20, b=30),
            xaxis=dict(title="Day", gridcolor="#F1F5F9"),
            yaxis=dict(title="Cash ($)", gridcolor="#F1F5F9"),
        )
        st.plotly_chart(fig_cf, use_container_width=True)
    else:
        st.info("Cash flow chart will appear after the first day is advanced.")

    # Cash breakdown table
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Current Cash", f"${state.cash:,.0f}")
    k2.metric("Total Revenue In", f"${state.total_revenue:,.0f}")
    k3.metric("Total Procurement Out", f"${state.total_purchase_spend:,.0f}")
    k4.metric("Total Overhead Out", f"${state.total_overhead:,.0f}")

# ── AR / AP Aging ─────────────────────────────────────────────────────────────
with tab_arap:
    c_ar, c_ap = st.columns(2)

    with c_ar:
        st.html("<div class='section-title'>Accounts Receivable (AR)</div>")
        shipped_unpaid = [so for so in state.sales_orders
                          if so.status == "Shipped" and so.shipped_day]
        from Archive.ERP_Sim_Integrated.config import FINANCIAL_PARAMS
        ar_rows = []
        total_ar = 0
        for so in shipped_unpaid:
            ar_val = so.qty * so.unit_price
            due_day = so.shipped_day + FINANCIAL_PARAMS["ar_payment_days"]
            days_past = state.current_day - due_day
            aging = "Current" if days_past <= 0 else (
                "1–7d" if days_past <= 7 else (
                "8–14d" if days_past <= 14 else "15d+"))
            total_ar += ar_val
            ar_rows.append({
                "Order": so.id, "Customer": so.customer_name,
                "Amount": f"${ar_val:,.0f}", "Due Day": due_day, "Aging": aging,
            })

        if ar_rows:
            st.dataframe(pd.DataFrame(ar_rows[-20:]), use_container_width=True, hide_index=True)
            st.metric("Total AR Outstanding (Est.)", f"${total_ar:,.0f}")
        else:
            st.caption("No receivables yet.")

    with c_ap:
        st.html("<div class='section-title'>Accounts Payable (AP)</div>")
        if state.srm_enabled:
            unpaid_inv = [i for i in state.supplier_invoices if i.status in ("Unpaid", "Overdue")]
            if unpaid_inv:
                ap_rows = []
                for inv in sorted(unpaid_inv, key=lambda x: x.due_day):
                    sup = state.suppliers.get(inv.supplier_id)
                    days_left = inv.due_day - state.current_day
                    ap_rows.append({
                        "Invoice": inv.id,
                        "Supplier": sup.name if sup else "?",
                        "Amount": f"${inv.amount:,.0f}",
                        "Due Day": inv.due_day,
                        "Days Left": days_left,
                        "Status": "🔴 Overdue" if inv.status == "Overdue" else (
                            "🟠 Due Soon" if days_left <= 5 else "🟢 Current"),
                    })
                st.dataframe(pd.DataFrame(ap_rows), use_container_width=True, hide_index=True)
            else:
                st.success("✅ All invoices paid!")
        else:
            st.info("AP invoice tracking is enabled with SRM module. "
                    "In manual mode, cash is deducted on PO placement.")
            open_pos = [po for po in state.purchase_orders if po.status == "OnOrder"]
            if open_pos:
                po_rows = [{"PO": po.id,
                            "Supplier": state.suppliers[po.supplier_id].name if po.supplier_id in state.suppliers else "?",
                            "Amount": f"${po.qty * po.unit_cost:,.0f}",
                            "Arrival Day": po.expected_arrival_day}
                           for po in open_pos]
                st.dataframe(pd.DataFrame(po_rows), use_container_width=True, hide_index=True)

# ── General Ledger ─────────────────────────────────────────────────────────────
with tab_ledger:
    st.html("<div class='section-title'>General Ledger — Last 50 Entries</div>")
    if state.financial_ledger:
        ledger_data = []
        balance = 0
        for entry in state.financial_ledger:
            balance += entry.credit - entry.debit
            ledger_data.append({
                "Day": entry.day, "Module": entry.module,
                "Type": entry.entry_type, "Ref": entry.ref_id,
                "Description": entry.description,
                "Debit": f"${entry.debit:,.0f}" if entry.debit else "—",
                "Credit": f"${entry.credit:,.0f}" if entry.credit else "—",
                "Running Balance": f"${balance:,.0f}",
            })
        st.dataframe(pd.DataFrame(ledger_data[-50:]), use_container_width=True, hide_index=True)
    else:
        st.caption("No ledger entries yet.")
