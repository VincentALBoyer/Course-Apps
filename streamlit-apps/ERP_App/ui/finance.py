import pandas as pd
import streamlit as st

from game_engine import get_pnl_statement
from ui.components import explainer_strip


def render() -> None:
    state = st.session_state.game_state

    explainer_strip(
        "Finance — Financial Accounting & Controlling",
        "consolidates the financial effect of every transaction posted in SRM and CRM "
        "into a single statement, the way a General Ledger (SAP FI-CO, Oracle GL) would.",
    )

    st.subheader("Profit & Loss Statement")
    pnl = get_pnl_statement(state)
    rows = [
        ("Revenue (sales delivered)", pnl["revenue"]),
        ("Cost of Goods Sold (purchases)", -pnl["cogs"]),
        ("Gross Margin", pnl["gross_margin"]),
        ("Holding Costs (inventory carrying cost)", -pnl["holding_costs"]),
        ("Late Delivery Penalties", -pnl["penalties"]),
        ("Net Profit", pnl["net_profit"]),
    ]
    pnl_df = pd.DataFrame(rows, columns=["Line Item", "Amount ($)"])
    st.dataframe(
        pnl_df.style.format({"Amount ($)": "{:,.0f}"}),
        hide_index=True, width='stretch',
    )
    st.caption(
        f"Pricing assumptions behind this statement: sales price **${state.selling_price:.2f}/unit** "
        f"(set in CRM), holding cost **${state.holding_cost_per_unit:.2f}/unit/day** (set in Inventory), "
        f"late penalty **${state.delay_penalty:.2f}/order/day** past the grace period, "
        "and each supplier's own unit price (set in SRM)."
    )

    st.divider()
    st.subheader("Cash & Profit Trend")
    if state.history:
        hist_df = pd.DataFrame(state.history)
        st.line_chart(hist_df.set_index("day")[["cash", "profit"]], height=280)
    else:
        st.info("Advance a few days to build up trend data.")
