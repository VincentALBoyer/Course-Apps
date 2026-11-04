# =============================================================================
# Page 04 — Procurement
# ERP-only mode: Manual email-based procurement (simulated inbox + manual PO)
# SRM mode: Supplier Portal with RFQ, quote comparison, contracts, AP invoices
# =============================================================================
import streamlit as st
import pandas as pd
from Archive.ERP_Sim_Integrated.engine.erp_engine import create_manual_po, run_mrp_suggestion, request_quote_manual
from Archive.ERP_Sim_Integrated.engine.srm_engine import (
    send_rfq, award_rfq, reject_rfq, create_contract, pay_invoice, 
    get_supplier_scorecard, purchase_from_market
)

if "sim_state" not in st.session_state:
    st.warning("Simulation state not initialized. Please go to the Home page first.")
    st.stop()

state = st.session_state.sim_state

st.html("""
<div class='page-header'>
    <h2>🛒 Procurement</h2>
    <p>Source raw materials from suppliers — manual or automated depending on active modules</p>
</div>
""")

# ── MRP Recommendation Strip ───────────────────────────────────────────────────
suggestions = run_mrp_suggestion(state)
if suggestions:
    with st.expander(f"🤖 MRP has {len(suggestions)} replenishment recommendations", expanded=True):
        for s in suggestions:
            cls = "alert-red" if s["urgency"] == "High" else "alert-amber"
            st.markdown(
                f"<div class='{cls}'><b>{s['urgency']}</b> — {s['material_name']}: "
                f"Stock={s['current_stock']}, Inbound={s['inbound']}, "
                f"7-day demand={s['projected_demand_7d']} → Order ≥ <b>{s['suggested_qty']}</b></div>",
                unsafe_allow_html=True
            )

st.divider()

# =============================================================================
# ===  ERP-ONLY MANUAL PROCUREMENT MODE  =====================================
# =============================================================================
if not state.srm_enabled:
    st.html(f"""
    <div class='alert-amber'>
    <b>📭 Siloed Operations (ERP Only)</b><br>
    SRM is disabled. Ordering requires manual communication and lacks integrated supplier data.<br>
    <ul>
        <li><b>Step 1:</b> Compose a Quote Request email to suppliers.</li>
        <li><b>Step 2:</b> Advance the day to wait for a reply.</li>
        <li><b>Step 3:</b> Open the <b>Inbox</b> to accept the quote and manually create a PO.</li>
    </ul>
    </div>
    """)
    st.markdown("")

    # -- Pedagogical Context --
    with st.expander("📖 Why is this page so manual?"):
        st.info("""
        **Session 1: The ERP Silo Challenge**
        In this phase, the SRM (Supplier Relationship Management) module is disabled. This simulates a common 
        real-world problem where the ERP system is 'siloed' from suppliers. 
        
        *   **Step 1**: You must manually send inquiries for pricing (Inquiry).
        *   **Step 2**: You must wait for a manual response (Simulates human/email delay).
        *   **Step 3**: You must manually enter the data back into the ERP to create a PO.
        
        Notice how much time and potential for error this creates!
        """, icon="🎓")
    
    tab_manual_req, tab_manual_log, tab_manual_pos = st.tabs([
        "📧 Step 1: Send Request", "📥 Step 3: Inbox", "📦 Open POs"
    ])

    with tab_manual_req:
        st.html("<div class='section-title'>📩 Send Manual Email Inquiries</div>")
        st.caption("One-click to send a formal inquiry to the preferred supplier. Replies arrive in 1-2 days.")
        
        # Grid of materials for quick inquiries
        mat_ids = list(state.materials.keys())
        for i in range(0, len(mat_ids), 3):
            cols = st.columns(3)
            for j in range(3):
                if i + j < len(mat_ids):
                    mid = mat_ids[i + j]
                    mat = state.materials[mid]
                    with cols[j]:
                        with st.container(border=True):
                            st.markdown(f"**{mat.name}**")
                            qty_inq = st.number_input("Qty", min_value=1, max_value=1000, value=100, step=10, key=f"qty_inq_{mid}")
                            
                            # Logic: Disable if inquiry sent today or pending
                            already_sent = any(pr.material_id == mid and pr.day_sent == state.current_day for pr in state.pending_rfqs)
                            
                            if st.button("📧 Send Inquiry", key=f"btn_inq_{mid}", use_container_width=True, disabled=already_sent):
                                from Archive.ERP_Sim_Integrated.engine.erp_engine import request_quote_manual
                                ok, msg = request_quote_manual(state, mid, qty_inq)
                                if ok:
                                    st.toast(f"Inquiry sent for {mat.name}", icon="✉️")
                                    st.rerun()
                                else:
                                    st.error(msg)
                            
                            if already_sent:
                                st.caption("🕒 Inquiry in flight...")
        
        # Pending requests
        if state.pending_rfqs:
            st.divider()
            st.markdown("**⏳ Awaiting Replies:**")
            for pr in state.pending_rfqs:
                mat = state.materials[pr.material_id]
                st.caption(f"• Request for {pr.qty}x {mat.name} sent Day {pr.day_sent}. Expected reply: Day {pr.day_sent + 1}.")

    with tab_manual_log:
        st.html("<div class='section-title'>📥 Procurement Inbox</div>")
        proc_comms = [c for c in state.communication_log if c.module == "Procurement"]
        if not proc_comms:
            st.info("No communications logged yet.")
        else:
            for comm in reversed(proc_comms):
                # Status prefix for header
                status_icon = "🟡" if comm.status == "Pending" else ("✅" if comm.status == "Accepted" else "❌")
                status_label = f"[{comm.status.upper()}]" if comm.status != "Pending" else ""
                
                # Collapsible Email Wrapper
                with st.expander(f"{status_icon} {status_label} {comm.subject} — Day {comm.day}", expanded=(comm.status == "Pending")):
                    c1, c2 = st.columns([4, 1.5])
                    c1.caption(f"From: {comm.entity_name} ({comm.direction})")
                    c1.markdown(f"*{comm.body}*")
                    
                    if comm.action_type == "rfq_quote" and comm.direction == "Inbound":
                        data = comm.action_data
                        if comm.status == "Pending":
                            btn_acc = c2.button("✅ Accept", key=f"acc_{comm.id}", use_container_width=True)
                            btn_rej = c2.button("❌ Reject", key=f"rej_{comm.id}", use_container_width=True)
                            
                            if btn_acc:
                                from Archive.ERP_Sim_Integrated.engine.erp_engine import create_manual_po
                                ok, msg = create_manual_po(state, data["supplier_id"], data["material_id"], 
                                                         data["qty"], data["price"], data["lead_time"])
                                if ok:
                                    comm.status = "Accepted"
                                    st.toast(f"PO Created: {msg}")
                                    st.rerun()
                                else:
                                    st.error(msg)
                            
                            if btn_rej:
                                comm.status = "Rejected"
                                st.toast(f"Quote from {comm.entity_name} rejected.")
                                st.rerun()
                        else:
                            c2.info(f"Status: {comm.status}")

    with tab_manual_pos:
        st.html("<div class='section-title'>📦 Inbound Monitor (Open POs)</div>")
        open_pos = [po for po in state.purchase_orders if po.status == "OnOrder"]
        if open_pos:
            rows = []
            for po in sorted(open_pos, key=lambda x: x.expected_arrival_day):
                sup = state.suppliers.get(po.supplier_id)
                mat = state.materials.get(po.material_id)
                days_left = po.expected_arrival_day - state.current_day
                rows.append({
                    "PO #": po.id, "Supplier": sup.name if sup else "?",
                    "Material": mat.name if mat else "?", "Qty": po.qty,
                    "Arrival": f"Day {po.expected_arrival_day}",
                    "Days Left": days_left,
                    "Status": "🔴 Late" if days_left < 0 else ("🟡 Today" if days_left == 0 else "🟢 Transit"),
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.caption("No open purchase orders.")


# =============================================================================
# ===  SRM MODULE — SUPPLIER PORTAL  =========================================
# =============================================================================
else:
    st.html("<div class='alert-blue'><b>🔗 SRM Module Active</b> — Real-time integrated supplier portal.</div>")
    st.markdown("")

    tab_market, tab_rfq, tab_contracts, tab_invoices, tab_scorecards = st.tabs([
        "📊 Daily Market", "🏆 Bulk RFQ", "📝 Contracts", "🧾 AP Invoices", "🏅 Supplier Scorecards"
    ])

    # ── Daily Market Tab ───────────────────────────────────────────────────────
    with tab_market:
        st.html("<div class='section-title'>📊 Real-Time Market (1-Click Buy)</div>")
        st.info(f"Live integrated supplier pricing for Day {state.current_day}. Immediate ordering—no emails needed.")
        
        m_filter = st.selectbox("Filter Material", ["All"] + list(state.materials.keys()),
                                format_func=lambda x: state.materials[x].name if x != "All" else "All Materials")
        
        market_rows = []
        for sid, sup in state.suppliers.items():
            if sup.is_blocked: continue
            for mid in sup.materials:
                if m_filter != "All" and mid != m_filter: continue
                mat = state.materials.get(mid)
                price = sup.contract_price.get(mid) if sup.contract_price and mid in sup.contract_price else sup.current_price.get(mid, mat.cost)
                is_contracted = bool(sup.contract_price and mid in sup.contract_price)
                
                market_rows.append({
                    "Material": mat.name, "Supplier": sup.name, "Unit Price": round(price, 2),
                    "Contract": "✅" if is_contracted else "—", "Lead Time": f"{sup.lead_time_days}d",
                    "sid": sid, "mid": mid, "price": price
                })
        
        if market_rows:
            for row in market_rows:
                with st.container(border=True):
                    c1, c2, c3, c4 = st.columns([1.5, 1, 1.2, 1])
                    c1.markdown(f"**{row['Supplier']}**")
                    c1.caption(f"{row['Material']} | LT: {row['Lead Time']}")
                    c2.metric("Price", f"${row['Unit Price']:.2f}", delta="Locked" if row['Contract'] == "✅" else None)
                    
                    buy_qty = c3.number_input("Qty", min_value=10, max_value=1000, value=100, step=10, key=f"qty_m_{row['sid']}_{row['mid']}")
                    if c4.button("💳 Purchase", key=f"buy_m_{row['sid']}_{row['mid']}", type="primary", use_container_width=True):
                        ok, msg = purchase_from_market(state, row['sid'], row['mid'], buy_qty)
                        if ok:
                            st.success(f"✅ PO {msg} Created!")
                            st.rerun()
                        else:
                            st.error(msg)
        else:
            st.warning("No suppliers available currently.")

    # ── RFQ Tab (Bulk / Automated) ─────────────────────────────────────────────
    with tab_rfq:
        st.html("<div class='section-title'>🏆 Bulk RFQ & Auto-Comparison</div>")
        st.caption("Use this to query ALL suppliers at once and compare the best composite scores.")

        with st.form("bulk_rfq_srm"):
            mat_rfq = st.selectbox("Material for Bulk RFQ", list(state.materials.keys()),
                                    format_func=lambda x: state.materials[x].name)
            qty_rfq = st.number_input("Total Quantity Needed", min_value=10, max_value=2000, value=200, step=10)
            if st.form_submit_button("🚀 Run Auto-Comparison", type="primary"):
                ok, msg, rfq = send_rfq(state, mat_rfq, qty_rfq)
                if ok:
                    st.success(f"✅ {msg}")
                    st.rerun()
                else:
                    st.error(msg)
        
        st.divider()

        open_rfqs = [r for r in state.rfqs if r.status == "QuotesReceived"]
        for rfq in open_rfqs:
            mat = state.materials.get(rfq.material_id)
            st.html(f"<div class='section-title'>🏁 RFQ Result: {rfq.id} — {rfq.qty_requested}x {mat.name if mat else '?'}</div>")
            
            for r in rfq.responses:
                with st.container(border=True):
                    cols = st.columns([2, 1, 1, 1])
                    cols[0].markdown(f"**{r['supplier_name']}**\nScore: {r['composite_score']}")
                    cols[1].metric("Price", f"${r['price']:.2f}")
                    cols[2].caption(f"LT: {r['lead_time']}d")
                    if cols[3].button("Award PO", key=f"aw_rfq_{rfq.id}_{r['supplier_id']}", type="primary"):
                        ok, msg = award_rfq(state, rfq.id, r['supplier_id'])
                        if ok: st.success("Awarded!"); st.rerun()
                        else: st.error(msg)
            
            if st.button("Reject All Quotes", key=f"rej_rfq_{rfq.id}"):
                reject_rfq(state, rfq.id)
                st.rerun()

    # ── Contracts Tab ─────────────────────────────────────────────────────────
    with tab_contracts:
        st.html("<div class='section-title'>📝 Create / Manage Contracts</div>")
        st.info("Lock in a preferred supplier price for a material.")

        with st.form("contract_form"):
            c1, c2 = st.columns(2)
            with c1:
                contract_mat = st.selectbox("Material", list(state.materials.keys()),
                                             format_func=lambda x: state.materials[x].name)
                valid_supps = [sid for sid, sup in state.suppliers.items() if contract_mat in sup.materials and not sup.is_blocked]
                contract_sup = st.selectbox("Supplier", valid_supps, format_func=lambda x: state.suppliers[x].name) if valid_supps else None
            with c2:
                market_p = state.suppliers[contract_sup].current_price.get(contract_mat, 0) if contract_sup else 0
                neg_price = st.number_input("Negotiated Price $", min_value=0.1, value=round(market_p * 0.96, 2), step=0.1)
                volume = st.number_input("Volume Commitment", min_value=50, value=200, step=50)

            if st.form_submit_button("📝 Establish Contract", type="primary"):
                if contract_sup:
                    ok, msg = create_contract(state, contract_sup, contract_mat, neg_price, volume)
                    if ok: st.success(msg); st.rerun()
                    else: st.error(msg)

        contracts = [(sid, sup) for sid, sup in state.suppliers.items() if sup.contract_price]
        if contracts:
            st.markdown("**Active Contracts:**")
            for sid, sup in contracts:
                for mid, price in sup.contract_price.items():
                    mat = state.materials.get(mid)
                    st.success(f"📝 {sup.name} → {mat.name}: ${price:.2f} (Market: ${sup.current_price.get(mid, 0):.2f})")

    # ── AP Invoices Tab ───────────────────────────────────────────────────────
    with tab_invoices:
        st.html("<div class='section-title'>🧾 Accounts Payable — Supplier Invoices</div>")
        unpaid = [i for i in state.supplier_invoices if i.status in ("Unpaid", "Overdue")]
        if not unpaid:
            st.success("✅ All invoices paid!")
        else:
            for inv in unpaid:
                sup = state.suppliers.get(inv.supplier_id)
                with st.container(border=True):
                    c1, c2, c3 = st.columns([2, 1, 1])
                    c1.markdown(f"**{sup.name if sup else 'Supplier'}**\nDue Day {inv.due_day}")
                    c2.metric("Amount", f"${inv.amount:,.0f}")
                    if c3.button("Pay Invoice", key=f"pay_srm_{inv.id}", type="primary"):
                        ok, msg = pay_invoice(state, inv.id)
                        if ok: st.rerun()
                        else: st.error(msg)

    # ── Supplier Scorecard Tab ─────────────────────────────────────────────────
    with tab_scorecards:
        st.html("<div class='section-title'>🏅 Supplier Performance</div>")
        for sid, sup in state.suppliers.items():
            sc = get_supplier_scorecard(state, sid)
            with st.container(border=True):
                st.markdown(f"**{sup.name}** | Relationship: {sup.relationship_score:.0f}/100")
                k1, k2, k3 = st.columns(3)
                k1.metric("On-Time %", f"{sc.get('on_time_rate', 0):.0f}%")
                k2.metric("Defects PPM", sc.get("defect_ppm", 0))
                k3.metric("Total Spend", f"${sc.get('total_spend', 0):,.0f}")
