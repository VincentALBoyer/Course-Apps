# =============================================================================
# Page 05 — Sales
# ERP-only: manual order inbox + ship button
# CRM enabled: full pipeline kanban, campaigns, customer 360, service tickets
# =============================================================================
import streamlit as st
import pandas as pd
from Archive.ERP_Sim_Integrated.engine.erp_engine import ship_sales_order, process_customer_order_manual
from Archive.ERP_Sim_Integrated.engine.crm_engine import (advance_lead_stage, run_marketing_campaign,
                                 create_service_ticket, resolve_ticket,
                                 compute_customer_health, get_crm_kpis, STAGE_ORDER)

if "sim_state" not in st.session_state:
    st.warning("Simulation state not initialized. Please go to the Home page first.")
    st.stop()

state = st.session_state.sim_state

st.html("""
<div class='page-header'>
    <h2>📈 Sales</h2>
    <p>Manage customer orders — manual entry or full CRM pipeline</p>
</div>
""")

# =============================================================================
# ===  ERP-ONLY MANUAL SALES MODE  ===========================================
# =============================================================================
# ── Pedagogical Context ───────────────────────────────────────────────────────
if not state.crm_enabled:
    with st.expander("📖 Why is this page so manual?"):
        st.info("""
        **Session 1: The Customer Communication Silo**
        Without a CRM, customer orders arrive as unstructured 'emails' or 'calls'. 
        You have no single source of truth for customer history or lead tracking.
        
        *   **Step 1**: Check the 'Inbox' for incoming inquiries.
        *   **Step 2**: Manually verify if you can fulfill the order and 'Enter' it into the ERP.
        *   **Step 3**: Keep track of fulfillment manually.
        
        Later, when CRM is active, this process will be automated and visual!
        """, icon="🎓")

    st.html("""
    <div class='alert-amber'>
    <b>📭 Siloed Operations (ERP Only)</b><br>
    CRM is disabled. Customer orders arrive as unstructured emails/calls. 
    Review the 3-step process below to fulfill demand.
    </div>
    """)
    st.markdown("")

    tab_manual_log, tab_manual_fg, tab_manual_ship = st.tabs([
        "📥 Step 1 & 2: Inbox", "🚲 Finished Goods", "🚀 Step 3: Pending Shipment"
    ])

    with tab_manual_log:
        st.html("<div class='section-title'>📥 Sales Inbox</div>")
        sales_comms = [c for c in state.communication_log if c.module == "Sales"]
        if not sales_comms:
            st.info("No sales inquiries yet.")
        else:
            for comm in reversed(sales_comms):
                # Status prefix for header
                status_icon = "🟡" if comm.status == "Pending" else ("✅" if comm.status == "Accepted" else "❌")
                status_label = f"[{comm.status.upper()}]" if comm.status != "Pending" else ""

                with st.expander(f"{status_icon} {status_label} {comm.subject} — Day {comm.day}", expanded=(comm.status == "Pending")):
                    c1, c2 = st.columns([4, 1.5])
                    c1.caption(f"From: {comm.entity_name} ({comm.direction})")
                    c1.markdown(f"*{comm.body}*")
                    
                    if comm.action_type == "customer_order" and comm.direction == "Inbound":
                        if comm.status == "Pending":
                            btn_acc = c2.button("✅ Accept", key=f"acc_s_{comm.id}", use_container_width=True)
                            btn_rej = c2.button("❌ Reject", key=f"rej_s_{comm.id}", use_container_width=True)
                            
                            if btn_acc:
                                from Archive.ERP_Sim_Integrated.engine.erp_engine import process_customer_order_manual
                                ok, msg = process_customer_order_manual(state, comm.id)
                                if ok:
                                    # comm.status is updated inside the engine function
                                    st.toast(f"Order Accepted: {msg}")
                                    st.rerun()
                                else:
                                    st.error(msg)
                            
                            if btn_rej:
                                comm.status = "Rejected"
                                st.toast(f"Order inquiry from {comm.entity_name} rejected.")
                                st.rerun()
                        else:
                            c2.info(f"Status: {comm.status}")

    with tab_manual_fg:
        st.html("<div class='section-title'>🚲 Finished Goods Inventory</div>")
        cols = st.columns(len(state.products))
        for i, (pid, prod) in enumerate(state.products.items()):
            qty = state.stock_finished.get(pid, 0)
            demand = sum(so.qty for so in state.sales_orders if so.product_id == pid and so.status == "Open")
            cols[i].metric(prod.name, f"{qty} units", delta=f"{demand} Required" if demand > 0 else None, delta_color="inverse")

    with tab_manual_ship:
        st.html("<div class='section-title'>📋 Open Orders — Ready to Ship</div>")
        open_orders = sorted([so for so in state.sales_orders if so.status == "Open"], key=lambda x: x.due_day)
        if not open_orders:
            st.success("✅ No open orders.")
        else:
            for so in open_orders:
                prod = state.products[so.product_id]
                in_stock = state.stock_finished.get(so.product_id, 0)
                can_ship = in_stock >= so.qty
                with st.container(border=True):
                    c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
                    c1.markdown(f"**{so.customer_name}** | {so.qty}x {prod.name}")
                    c1.caption(f"SO: {so.id} | Due D{so.due_day}")
                    c2.metric("Stock", in_stock)
                    if can_ship:
                        if c4.button("🚀 SHIP", key=f"ship_m_{so.id}", type="primary"):
                            ok, msg = ship_sales_order(state, so.id)
                            if ok: st.rerun()
                            else: st.error(msg)
                    else:
                        c4.button("Waiting", disabled=True, key=f"wait_m_{so.id}")

# =============================================================================
# ===  CRM MODULE — FULL PIPELINE  ===========================================
# =============================================================================
else:
    crm_kpis = get_crm_kpis(state)
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Pipeline Value", crm_kpis["Pipeline Value"])
    k2.metric("Win Rate", crm_kpis["Win Rate %"])
    k3.metric("Active Customers", crm_kpis["Active Customers"])
    k4.metric("Avg CSAT", crm_kpis["Average CSAT"])
    k5.metric("Open Tickets", crm_kpis["Open Tickets"])

    tab_pipeline, tab_orders, tab_campaigns, tab_customers, tab_service = st.tabs([
        "🎯 Pipeline", "📦 Sales Orders", "📢 Campaigns", "👥 Customers", "🎫 Service"
    ])

    # ── Pipeline Kanban ───────────────────────────────────────────────────────
    with tab_pipeline:
        st.html("<div class='section-title'>Sales Pipeline</div>")
        active_leads = [l for l in state.leads if l.stage not in ("Won", "Lost")]
        if not active_leads:
            st.warning("No active leads. Launch a campaign!")
        else:
            pipeline_stages = ["New", "Qualified", "Proposal", "Negotiation"]
            stage_cols = st.columns(len(pipeline_stages))
            for i, stage in enumerate(pipeline_stages):
                with stage_cols[i]:
                    st.markdown(f"**{stage}**")
                    for lead in [l for l in active_leads if l.stage == stage]:
                        with st.container(border=True):
                            st.markdown(f"**{lead.company}**")
                            st.caption(f"${lead.estimated_value:,.0f} | {lead.win_probability}%")
                            if st.button("Advance", key=f"adv_{lead.id}"):
                                nx = STAGE_ORDER[STAGE_ORDER.index(stage)+1]
                                advance_lead_stage(state, lead.id, nx)
                                st.rerun()

    # ── Sales Orders ──────────────────────────────────────────────────────────
    with tab_orders:
        st.html("<div class='section-title'>ERP Orders (CRM Integrated)</div>")
        st.caption("Sales orders are now automatically created in the ERP when a CRM deal is won. No manual entry needed.")
        open_orders = sorted([so for so in state.sales_orders if so.status == "Open"], key=lambda x: x.due_day)
        for so in open_orders:
            prod = state.products[so.product_id]
            in_stock = state.stock_finished.get(so.product_id, 0)
            with st.container(border=True):
                c1, c2, c3 = st.columns([3, 1, 1])
                c1.markdown(f"**{so.customer_name}** — {so.qty}x {prod.name}")
                c2.metric("Stock", in_stock)
                if in_stock >= so.qty:
                    if c3.button("🚀 SHIP", key=f"ship_crm_{so.id}", type="primary"):
                        ship_sales_order(state, so.id)
                        st.rerun()

    # ── Campaigns ─────────────────────────────────────────────────────────────
    with tab_campaigns:
        st.html("<div class='section-title'>Marketing</div>")
        ctabs = st.columns(3)
        for i, ckey in enumerate(["digital_ads", "outbound_calls", "trade_show"]):
            with ctabs[i]:
                if st.button(f"Launch {ckey}", use_container_width=True):
                    run_marketing_campaign(state, ckey)
                    st.rerun()

    # ── Service Desk ──────────────────────────────────────────────────────────
    with tab_service:
        st.html("<div class='section-title'>Service Tickets</div>")
        open_tickets = [t for t in state.service_tickets if t.status != "Resolved"]
        for t in open_tickets:
            with st.container(border=True):
                c1, c2 = st.columns([4, 1])
                c1.markdown(f"**{t.customer_name}**: {t.issue}")
                if c2.button("Resolve", key=f"res_{t.id}"):
                    resolve_ticket(state, t.id)
                    st.rerun()
