import pandas as pd
import streamlit as st

from game_engine import get_kpis
from ui.components import explainer_strip


def render() -> None:
    state = st.session_state.game_state
    kpis = get_kpis(state)

    explainer_strip(
        "Inventory & Operations — Warehouse Management",
        "the single physical stock record that SRM restocks and CRM draws down from. "
        "Every module sees the same on-hand quantity, in real time.",
    )

    f1, f2, f3, f4 = st.columns(4)
    f1.metric("🚚 Inbound (from SRM)", kpis["incoming_qty"], help="Units purchased and in transit from suppliers")
    f2.metric("📦 On-Hand Stock", kpis["inventory"], help="Units physically in the warehouse right now")
    f3.metric("🛍️ Outstanding Demand (from CRM)", kpis["pending_demand"], help="Units customers are still waiting on")
    f4.metric(
        "💸 Holding Cost Rate", f"${state.holding_cost_per_unit:.2f}/unit/day",
        help="Charged automatically on whatever is on-hand at the end of every day",
    )

    st.caption(
        f"Every unit sitting in the warehouse costs **${state.holding_cost_per_unit:.2f} per day** "
        f"— charged automatically when you Advance to Next Day, regardless of whether that stock "
        f"is needed soon. **${state.total_holding_cost:,.0f}** has accrued so far this run. "
        "This is exactly the kind of cost a real Inventory/Warehouse module tracks and Finance reports on — "
        "it's the reason over-ordering in SRM isn't free, even when cash allows it."
    )

    st.divider()
    st.subheader("Inventory Trend")
    if state.history:
        hist_df = pd.DataFrame(state.history)
        st.line_chart(hist_df.set_index("day")[["inventory"]], height=280)
    else:
        st.info("Advance a few days to build up trend data.")
