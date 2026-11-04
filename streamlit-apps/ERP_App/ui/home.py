import streamlit as st

from game_engine import get_kpis
from ui.components import flow_diagram


@st.dialog("Welcome to Global Gadgets Inc.", dismissible=False)
def _welcome_dialog():
    st.markdown(
        """
Global Gadgets Inc. distributes a single electronic component to business
customers. You run **fulfillment operations** end-to-end: buying stock from
suppliers, holding it in the warehouse, and shipping it to customers before
their due date — for **30 simulated business days**.

**Your objective:** finish Day 30 with the highest possible Net Profit.

**How the system is organized:** every screen you'll use — SRM, CRM,
Inventory, Finance — is a different *view* over the same underlying data.
Ordering stock in **SRM** immediately affects what **Inventory** shows and
what **Finance** reports; shipping an order in **CRM** does the same. That's
the core idea of an ERP system: one shared source of truth instead of
disconnected spreadsheets.

**Each day:**
1. Go to **SRM** to place purchase orders with suppliers (optional).
2. Go to **CRM** to ship any sales orders you can currently fulfill.
3. Click **Advance to Next Day** (always visible at the top of the screen).

New customer demand, incoming deliveries, holding costs and late penalties
are all applied automatically when you advance the day.
        """
    )
    st.divider()
    st.markdown("**Before you start:** enter your name and student ID — they'll be printed on the performance report you can download at Day 30 to submit for grading.")
    name = st.text_input("Full name", value=st.session_state.get("student_name", ""))
    student_id = st.text_input("Student ID", value=st.session_state.get("student_id", ""))
    ready = bool(name.strip()) and bool(student_id.strip())
    if not ready:
        st.caption("Both fields are required to start.")
    if st.button("Got it — start the simulation", type="primary", width='stretch', disabled=not ready):
        st.session_state.student_name = name.strip()
        st.session_state.student_id = student_id.strip()
        st.session_state.onboarded = True
        st.rerun()


def render() -> None:
    state = st.session_state.game_state
    kpis = get_kpis(state)
    pages = st.session_state.nav_pages

    if not st.session_state.get("onboarded"):
        _welcome_dialog()

    st.subheader("What is an ERP?")
    st.markdown(
        "An **Enterprise Resource Planning (ERP)** system integrates the core "
        "functions of a business — procurement, inventory, sales, and finance — "
        "into one shared system, so every department is working from the same "
        "live data instead of its own disconnected spreadsheet. This simulator "
        "walks through that idea with four connected modules:"
    )
    flow_diagram()

    st.write("")
    st.subheader("Modules")
    t1, t2, t3, t4 = st.columns(4)

    with t1:
        with st.container(border=True):
            st.markdown("#### 🚚 SRM")
            st.caption("Supplier Relationship Management")
            st.metric("Inbound purchase orders", kpis["incoming_qty"])
            st.page_link(pages["srm"], label="Open SRM", icon="🚚", width='stretch')

    with t2:
        with st.container(border=True):
            st.markdown("#### 🤝 CRM")
            st.caption("Customer Relationship Management")
            st.metric("Open sales orders", kpis["orders_pending"])
            st.page_link(pages["crm"], label="Open CRM", icon="🤝", width='stretch')

    with t3:
        with st.container(border=True):
            st.markdown("#### 📦 Inventory & Ops")
            st.caption("Warehouse Management")
            st.metric("Units on hand", kpis["inventory"])
            st.page_link(pages["inventory"], label="Open Inventory", icon="📦", width='stretch')

    with t4:
        with st.container(border=True):
            st.markdown("#### 💰 Finance")
            st.caption("Financial Accounting")
            st.metric("Net profit", f"${kpis['profit']:,.0f}")
            st.page_link(pages["finance"], label="Open Finance", icon="💰", width='stretch')

    st.write("")
    st.page_link(pages["learn"], label="New here? Read the ERP / CRM / SRM primer", icon="🎓")

    st.divider()
    st.subheader("Recent Activity")
    with st.container(height=280):
        if state.daily_events:
            for e in reversed(state.daily_events):
                st.text(e)
        else:
            st.caption("No events yet — advance a day to get started.")
