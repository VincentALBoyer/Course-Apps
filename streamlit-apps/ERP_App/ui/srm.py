import pandas as pd
import streamlit as st

from game_engine import SUPPLIERS, get_supplier_scorecard
from ui.components import explainer_strip


def render() -> None:
    state = st.session_state.game_state

    explainer_strip(
        "SRM — Supplier Relationship Management",
        "manages sourcing: which vendors you buy from, at what price and lead time, "
        "and how each has performed over time. Orders placed here are queued and "
        "submitted the next time you Advance to Next Day.",
    )

    st.subheader("Supplier Market")
    suppliers = list(SUPPLIERS.values())
    cols = st.columns(4)
    for s, col in zip(suppliers, cols):
        avail = state.supplier_availability.get(s.id, {})
        is_available = avail.get("available", True)
        with col:
            with st.container(border=True):
                st.markdown(f"**{s.emoji} {s.name}**")
                st.caption(f"${s.unit_price:.2f}/unit · {s.lead_time_min}-{s.lead_time_max}d lead time")
                st.caption(f"Reliability: {s.reliability * 100:.0f}%")
                if is_available:
                    max_q = avail["max_today"]
                    st.number_input(
                        "Qty", min_value=0, max_value=max_q, step=10,
                        key=f"ord_{s.id}", label_visibility="collapsed",
                        disabled=state.game_over,
                    )
                    st.caption(f"Today's capacity: {max_q} (min order {s.min_order})")
                else:
                    st.error("Unavailable today")
    st.caption("Quantities set above are submitted automatically on the next **Advance to Next Day**.")

    st.divider()
    left, right = st.columns([1.3, 1])

    with left:
        st.subheader("Supplier Scorecard")
        scorecard = get_supplier_scorecard(state)
        sc_df = pd.DataFrame(scorecard).rename(columns={
            "supplier": "Supplier", "orders": "Orders", "units_purchased": "Units Purchased",
            "total_spend": "Total Spend ($)", "avg_lead_time_days": "Avg. Lead Time (days)",
        })
        st.dataframe(sc_df, hide_index=True, width='stretch')
        spend_df = pd.DataFrame(scorecard).set_index("supplier")[["total_spend"]]
        spend_df.columns = ["Total Spend ($)"]
        st.bar_chart(spend_df, height=220)

    with right:
        st.subheader("Inbound Purchase Orders")
        inbound = [o for o in state.supplier_orders if o.status == "in_transit"]
        if inbound:
            inbound_df = pd.DataFrame([{
                "PO #": o.id,
                "Supplier": SUPPLIERS[o.supplier_id].name,
                "Qty": o.quantity,
                "Arrives": f"Day {o.expected_arrival}",
            } for o in inbound])
            st.dataframe(inbound_df, hide_index=True, width='stretch', height=250)
        else:
            st.caption("No purchase orders in transit.")
