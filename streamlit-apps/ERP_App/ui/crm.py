import pandas as pd
import streamlit as st

from game_engine import ship_specific_order, get_customer_scorecard
from ui.components import explainer_strip
from ui.theme import badge


def render() -> None:
    state = st.session_state.game_state

    explainer_strip(
        "CRM — Customer Relationship Management",
        "manages the customer side of the business: open sales orders, shipping, "
        "and how reliably each customer account is being served.",
    )

    st.metric(
        "💵 Selling Price", f"${state.selling_price:.2f}/unit",
        help="Revenue is recognized when a shipped order is delivered to the customer, "
             "not at the moment you click Ship.",
    )
    st.caption(
        "This is the price Finance uses to recognize revenue once an order is delivered — "
        "shipping alone doesn't book revenue, delivery does."
    )

    if "action_ship" in st.session_state:
        oid = st.session_state.action_ship
        if ship_specific_order(state, oid):
            st.toast(f"✅ Sales Order #{oid} shipped!", icon="🚚")
        else:
            st.toast("❌ Shipping failed (check stock)", icon="🚫")
        del st.session_state.action_ship

    c1, c2 = st.columns([3, 1])
    c1.subheader("Open Sales Orders")
    pending_orders = [o for o in state.customer_orders if o.status == "pending"]

    if c2.button("🚀 Ship All Available", disabled=len(pending_orders) == 0 or state.game_over, type="primary"):
        shipped_count = 0
        pending_orders.sort(key=lambda x: x.due_date)
        for o in pending_orders:
            if state.inventory >= o.quantity:
                state.inventory -= o.quantity
                o.quantity_fulfilled = o.quantity
                o.status = "in_transit"
                o.day_shipped = state.current_day
                o.expected_delivery = state.current_day + o.delivery_time
                shipped_count += 1
        if shipped_count > 0:
            st.toast(f"✅ Batch shipped {shipped_count} sales orders!", icon="🚀")
            st.rerun()
        else:
            st.toast("❌ Not enough stock for any order!", icon="🚫")

    if pending_orders:
        pending_orders.sort(key=lambda x: x.due_date)
        for o in pending_orders:
            due_in = o.due_date - state.current_day
            color = "red" if due_in < 1 else "amber" if due_in < 3 else "green"
            with st.container(border=True):
                oc1, oc2, oc3, oc4, oc5 = st.columns([0.5, 2, 1, 1.5, 1])
                oc1.write(f"#{o.id}")
                oc2.write(f"**{o.customer.emoji} {o.customer.name}**")
                oc3.write(f"**{o.quantity}** units (${o.quantity * state.selling_price:,.0f})")
                oc4.markdown(f"Due Day {o.due_date} &nbsp; {badge(f'{due_in}d left', color)}", unsafe_allow_html=True)
                can_ship = state.inventory >= o.quantity
                if oc5.button("Ship", key=f"ship_{o.id}", disabled=not can_ship or state.game_over):
                    st.session_state.action_ship = o.id
                    st.rerun()
    else:
        st.success("✅ All sales orders shipped.")

    st.divider()
    st.subheader("Customer Scorecard")
    scorecard = get_customer_scorecard(state)
    sc_df = pd.DataFrame(scorecard).rename(columns={
        "customer": "Customer", "orders": "Orders", "units_ordered": "Units Ordered",
        "revenue": "Revenue ($)", "on_time_pct": "On-Time Delivery (%)",
    })
    st.dataframe(sc_df, hide_index=True, width='stretch')
    orders_df = pd.DataFrame(scorecard).set_index("customer")[["orders"]]
    orders_df.columns = ["Orders"]
    st.bar_chart(orders_df, height=220)
