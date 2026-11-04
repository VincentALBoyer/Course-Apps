import pandas as pd
import streamlit as st


def render() -> None:
    st.subheader("What is an ERP, and why does this simulator have four modules?")
    st.markdown(
        """
An **Enterprise Resource Planning (ERP)** system is business software that
integrates the core functions of a company — sourcing, inventory, sales, and
finance — into **one shared database**, instead of each department keeping
its own spreadsheet or standalone tool.

The value isn't any single module; it's that a transaction entered once
(e.g. "customer order shipped") is instantly visible everywhere it matters:
inventory drops, revenue is recognized, and the customer's order history
updates — with nobody re-typing the same data twice. That's the property
this simulator is built to demonstrate: every module you'll use reads and
writes the same underlying `GameState`.
        """
    )

    st.subheader("The modules covered in this simulator")
    c1, c2, c3 = st.columns(3)
    with c1:
        with st.container(border=True):
            st.markdown("#### 🚚 SRM")
            st.markdown(
                "**Supplier Relationship Management** — manages sourcing: which "
                "vendors to buy from, pricing, lead times, and supplier "
                "performance over time. In this sim: the **SRM** page."
            )
    with c2:
        with st.container(border=True):
            st.markdown("#### 🤝 CRM")
            st.markdown(
                "**Customer Relationship Management** — manages the customer "
                "side: orders, fulfillment, and account-level service quality. "
                "In this sim: the **CRM** page."
            )
    with c3:
        with st.container(border=True):
            st.markdown("#### 📦💰 ERP core")
            st.markdown(
                "**Inventory/Warehouse & Finance/Accounting** — the shared "
                "operational and financial record of the business that SRM and "
                "CRM both feed into. In this sim: the **Inventory** and "
                "**Finance** pages."
            )

    st.divider()
    st.subheader("How this maps to real-world systems")
    st.caption(
        "For classroom reference only — this simulator is an independent teaching tool "
        "and is not affiliated with or endorsed by SAP or Oracle."
    )
    mapping = pd.DataFrame([
        {"This simulator": "SRM (Suppliers)", "SAP": "MM (Materials Mgmt) / Ariba", "Oracle": "Procurement Cloud"},
        {"This simulator": "CRM (Customers)", "SAP": "SAP CRM / Sales & Distribution (SD)", "Oracle": "CX Sales / Salesforce-style CRM"},
        {"This simulator": "Inventory & Ops", "SAP": "MM / WM (Warehouse Mgmt)", "Oracle": "Inventory Management Cloud"},
        {"This simulator": "Finance", "SAP": "FI-CO (Finance & Controlling)", "Oracle": "Fusion Cloud ERP - GL"},
    ])
    st.dataframe(mapping, hide_index=True, width='stretch')

    st.divider()
    st.subheader("How to play")
    st.markdown(
        """
Global Gadgets Inc. distributes a single electronic component. Over **30
simulated business days**, your job is to maximize **Net Profit**:

1. **SRM** — place purchase orders with suppliers before you run out of stock.
   Cheaper/slower suppliers vs. pricier/faster ones is the core trade-off.
2. **CRM** — ship sales orders before their due date. Late orders (more than
   a day overdue) incur a penalty; unfulfilled demand is lost revenue.
3. **Inventory** — unsold stock costs money to hold every single day, so
   over-ordering has a real cost too.
4. **Finance** — tracks the net effect of every decision as a running P&L.
5. Click **Advance to Next Day** (top of every page) to close out the day:
   orders are placed, deliveries arrive, new demand comes in, and daily
   costs/penalties are applied automatically.

The simulation ends after Day 30 with your final Net Profit.
        """
    )
