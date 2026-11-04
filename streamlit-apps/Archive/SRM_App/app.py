import streamlit as st
import pandas as pd
import altair as alt
import Archive.SRM_App.logic as logic

st.set_page_config(page_title="SRM | Advanced Sourcing", page_icon="🏭", layout="wide")

# Styling
st.markdown("""
<style>
    .stApp { background-color: #f5f7f9; }
    .nav-tab { font-weight: bold; }
    .alert-box { padding: 10px; border-radius: 5px; margin-bottom: 5px; font-weight: 500;}
    .alert-red { background-color: #fadbd8; color: #922b21; border: 1px solid #922b21; }
    .alert-green { background-color: #d5f5e3; color: #1e8449; border: 1px solid #1e8449; }
    .metric-card { background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); text-align: center; }
    .metric-val { font-size: 1.6rem; font-weight: 800; color: #2c3e50; }
    .metric-lbl { font-size: 0.8rem; text-transform: uppercase; color: #7f8c8d; }
</style>
""", unsafe_allow_html=True)

if 'srm_state' not in st.session_state:
    st.session_state.srm_state = logic.init_game()
    # Default selection removed

state = st.session_state.srm_state

# =============================================================================
# SIDEBAR CONTROLS
# =============================================================================
with st.sidebar:
    st.title("🏭 SRM")
    st.caption("Advanced Procurement Sim")
    st.divider()
    
    menu = st.radio("Module", ["🚀 Procurement Cockpit", "🏭 Sourcing Master", "📅 MRP & Planning", "💰 Financials"], label_visibility="collapsed")
    
    st.divider()
    
    c1, c2 = st.columns(2)
    c1.metric("Day", f"{state.current_day} / {state.max_days}")
    
    total_cost = state.total_spend + state.total_rework_cost + state.total_stockout_penalty + state.total_storage_cost
    # help_text = f"Spend: ${state.total_spend:,.0f}\nStockout: ${state.total_stockout_penalty:,.0f}\nRework: ${state.total_rework_cost:,.0f}\nStorage: ${state.total_storage_cost:,.0f}"
    help_text = (
        f"- Spend: ${state.total_spend:,.0f}\n"
        f"- Stockout: ${state.total_stockout_penalty:,.0f}\n"
        f"- Rework: ${state.total_rework_cost:,.0f}\n"
        f"- Storage: ${state.total_storage_cost:,.0f}"
        )


    c2.metric("Total Cost", f"${total_cost:,.0f}", help=help_text)
    
    if not state.game_over:
        def on_next_day():
            # 1. Commit Validated Drafts
            logic.commit_draft_orders(state)
            
            # 2. Check for "Forgot to Validate" inputs (Auto-Draft and Commit)
            # If user entered numbers but didn't click Validate, we take them now.
            for s in state.available_suppliers:
                qty = st.session_state.get(f"qty_{s.id}", 0)
                if qty > 0:
                    if s.is_blocked:
                         st.toast(f"🚫 {s.name} is BLOCKED. Order rejected.", icon="🛑")
                         state.daily_events.append(f"⛔ Order to {s.name} REJECTED (Blocked)")
                         continue
                         
                    # Place immediately as Open (skipping draft phase for speed)
                    success, msg = logic.place_order(state, s.id, qty, status="Open")
                    if success:
                        st.session_state[f"qty_{s.id}"] = 0
                    else:
                        state.daily_events.append(f"⚠️ ORDER ERROR ({s.name}): {msg}")
                        st.toast(f"⚠️ {s.name}: {msg}", icon="🚫")

            # 3. Process Turn
            logic.process_daily_turn(state)
            
        st.button("➡️ NEXT DAY", type="primary", use_container_width=True, on_click=on_next_day)
    else:
        st.error("Simulation Ended. See Analysis below.")
        st.divider()
        st.write("### 🏁 End of Game")
        st.write(f"**Final Total Cost:** ${state.total_spend + state.total_rework_cost + state.total_stockout_penalty + state.total_storage_cost:,.2f}")
        
        # Download Real Data
        csv = logic.get_csv_export(state)
        st.download_button("📥 Download Transaction Log", csv, "srm_mrp_data.csv", type="primary", use_container_width=True)
        
        st.divider()
        st.write("#### 🎓 Training Data")
        # Generate Simulation Button
        if st.button("🔄 Gen. 100-Order History", help="Simulate a 100-order game for analysis practice", use_container_width=True):
            st.session_state['sim_csv'] = logic.generate_historical_simulation(100)
            st.success("Generated!")
        
        if 'sim_csv' in st.session_state:
            st.download_button("📥 Download 100 Sim Log", st.session_state['sim_csv'], "srm_historical_data.csv", use_container_width=True)

# =============================================================================
# MAIN AREA
# =============================================================================

if menu == "🚀 Procurement Cockpit":
    st.subheader("🚀 Procurement Execution Cockpit")
    
    # 1. KPI Cards
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.markdown(f"<div class='metric-card'><div class='metric-val'>{state.inventory}</div><div class='metric-lbl'>Stock</div></div>", unsafe_allow_html=True)
    k2.markdown(f"<div class='metric-card'><div class='metric-val'>{len(state.active_pos)}</div><div class='metric-lbl'>Open POs</div></div>", unsafe_allow_html=True)
    k3.markdown(f"<div class='metric-card'><div class='metric-val'>${state.total_rework_cost:,.0f}</div><div class='metric-lbl'>Quality</div></div>", unsafe_allow_html=True)
    k4.markdown(f"<div class='metric-card'><div class='metric-val'>${state.total_stockout_penalty:,.0f}</div><div class='metric-lbl'>Stockout</div></div>", unsafe_allow_html=True)
    k5.markdown(f"<div class='metric-card'><div class='metric-val'>${state.total_storage_cost:,.0f}</div><div class='metric-lbl'>Storage</div></div>", unsafe_allow_html=True)
    
    st.divider()
    
    # 2. Daily Alerts
    c_alert, c_sched = st.columns([1, 1])
    
    with c_alert:
        st.write("##### 📢 Daily Notifications")
        with st.container(height=300):
            if state.daily_events:
                for ev in reversed(state.daily_events):
                    style = "alert-red" if "STOPPAGE" in ev or "DELAY" in ev or "Defective" in ev else "alert-green"
                    st.markdown(f"<div class='alert-box {style}'>{ev}</div>", unsafe_allow_html=True)
            else:
                st.caption("No recent events.")
                
    with c_sched:
        st.write("##### 📅 Today's Production Target")
        today_demand = state.production_schedule.get(state.current_day, 0)
        
        status_color = "green" if state.inventory >= today_demand else "red"
        st.markdown(f"""
        ### Target: **{today_demand} units**
        ### Available: <span style='color:{status_color}'>{state.inventory} units</span>
        """, unsafe_allow_html=True)
        
        if state.inventory < today_demand:
            st.warning(f"⚠️ RISK: Shortage of {today_demand - state.inventory} units! Line stop imminent.")

    # 3. Inbound Delivery Monitor
    st.write("##### 🚛 Inbound Monitor (Open POs)")
    if state.active_pos:
        po_data = []
        for po in state.active_pos:
            supp = next((s for s in state.available_suppliers if s.id == po.supplier_id), None)
            po_data.append({
                "PO #": po.id,
                "Vendor": supp.name if supp else "Unknown Vendor",
                "Qty": po.qty_ordered,
                "Est. Arrival": f"Day {po.expected_arrival_day}",
                "Status": "Pending (Draft)" if po.status == "Draft" else ("Processing" if po.status == "Processing" else ("Late" if state.current_day > po.expected_arrival_day else "In Transit"))
            })
        st.dataframe(pd.DataFrame(po_data), use_container_width=True)
    else:
        st.info("No active Purchase Orders. Check MRP to place orders.")

elif menu == "📅 MRP & Planning":
    st.subheader("📅 Material Requirements Planning (MRP)")
    
    # 1. The Schedule Chart
    st.write("##### Production Demand Forecast (Next 30 Days)")
    
    sched_df = pd.DataFrame(list(state.production_schedule.items()), columns=["Day", "Demand"])
    # Filter for future only
    sched_df = sched_df[sched_df["Day"] >= state.current_day]
    
    chart = alt.Chart(sched_df).mark_bar().encode(
        x='Day:O',
        y='Demand:Q',
        color=alt.value("#3498db")
    ).properties(height=200)
    st.altair_chart(chart, use_container_width=True)
    
    st.divider()
    
    # 2. Ordering Interface
    st.write("##### 📝 Procurement Desk (Place Orders)")
    
    for supp in state.available_suppliers:
        with st.container(border=True):
            c1, c2, c3, c4, c5 = st.columns([2, 1, 1, 1, 1])
            c1.markdown(f"**{supp.name}**")
            c1.caption(supp.description)
            delta_val = None
            if state.current_day > 1:
                diff = supp.current_price - supp.previous_price
                pct = (diff / supp.previous_price) * 100
                delta_val = f"{pct:+.1f}% vs Yesterday"
            
            c2.metric("Market Price", f"${supp.current_price:.2f}", delta=delta_val, delta_color="inverse")
            if supp.is_blocked:
                c2.caption(":red[BLOCKED]")
            c3.metric("Lead Time", f"{supp.quoted_lead_time}d")
            c4.metric("Min Qty", supp.min_order_qty)
            
            # Individual Order Form -> Centralized input.
            with c5:
                # We use session state keys to track values across reruns
                key = f"qty_{supp.id}"
                if key not in st.session_state:
                    st.session_state[key] = 0
                
                # Disable input if locked (i.e. if a Draft exists for this supplier)
                is_locked = any(po.supplier_id == supp.id and po.status == "Draft" for po in state.active_pos)
                st.number_input("Qty", min_value=0, step=50, key=key, label_visibility="collapsed", disabled=is_locked)

    # Batch Actions Logic
    # No "orders_locked" state needed anymore, we use existence of Drafts in active_pos
        
    def cancel_drafts():
        # Remove all Draft orders
        state.active_pos = [po for po in state.active_pos if po.status != "Draft"]
        # Clear inputs (optional)
        for s in state.available_suppliers:
             st.session_state[f"qty_{s.id}"] = 0
            
    def validate_orders():
        # Create Draft POs
        created = 0
        
        # Clear existing drafts first? To avoid duplicates if pressed twice?
        # Yes, standard behavior: Validate = "Take current inputs as the plan"
        state.active_pos = [po for po in state.active_pos if po.status != "Draft"]
        
        for s in state.available_suppliers:
            qty = st.session_state.get(f"qty_{s.id}", 0)
            if qty > 0:
                success, msg = logic.place_order(state, s.id, qty, status="Draft")
                if success:
                    created += 1
                    st.session_state[f"qty_{s.id}"] = 0 # Clear inputs
                else:
                    st.toast(f"⚠️ {s.name}: {msg}", icon="🚫")
        
        if created > 0:
            st.toast(f"✅ {created} Orders Validated. See Inbound Monitor.", icon="📋")
        else:
            pass # Silent if nothing entered

    # Buttons State Logic
    has_drafts = any(po.status == "Draft" for po in state.active_pos)
    
    # Right-aligned, compact
    b_space, b_clear, b_val = st.columns([6, 1, 1])
    
    with b_clear:
        if has_drafts:
             # UNLOCK Button (Cancels Drafts)
             st.button("🔓 Unlock", on_click=cancel_drafts, help="Cancel drafts and edit")
        else:
             # CLEAR Button (Resets inputs)
             def clear_inputs():
                 for s in state.available_suppliers: st.session_state[f"qty_{s.id}"] = 0
             st.button("❌ Clear", on_click=clear_inputs, help="Reset inputs to 0")

    with b_val:
        # VALIDATE Button
        # Disabled if already locked (has drafts)
        st.button("🔐 Validate", type="primary", on_click=validate_orders, disabled=has_drafts, help="Lock and validate orders")
             
elif menu == "🏭 Sourcing Master":
    st.subheader("🏭 Supplier Performance Master")
    st.write("Real-time performance tracking. Monitor Actuals vs Promoted Specs.")
    
    for i, s in enumerate(state.available_suppliers):
        stats = logic.get_supplier_stats(state, s.id)
        
        with st.container(border=True):
            c_head, c_kpi = st.columns([1, 3])
            
            with c_head:
                st.markdown(f"### {s.name}")
                st.caption(s.category)
                st.write(f"_{s.description}_")
                
                st.metric("Relationship Score", f"{s.relationship_score:.1f}/100")
                if s.is_blocked: st.error("BLOCKED: Payment Issues")

            with c_kpi:
                # Comparison Grid
                k1, k2, k3, k4 = st.columns(4)
                
                # PRICE
                # Overall variation vs Start (Quoted)
                diff = s.current_price - s.quoted_price
                pct = (diff / s.quoted_price) * 100
                delta_val = f"{pct:+.1f}% vs Quote"
                
                k1.metric("Current Price", f"${s.current_price:.2f}", delta=delta_val, delta_color="inverse")
                
                # LEAD TIME
                k2.metric("Quoted Lead Time", f"{s.quoted_lead_time}d", help="Promised Delivery Speed")
                
                # DEFECTS (Actual vs Predicted)
                if stats['has_history']:
                    val = f"{stats['defect_rate']:.1f}%"
                    delta = -stats['defect_rate'] # Negative delta is bad (red) - wait, st.metric delta colors: Positive is Up (Green). 
                    # We want Low Defect = Green.
                    # If we use delta_color="inverse", positive delta is Good (Green)? No, inverse means positive is Bad (Red).
                    # Let's just use color formatting or simple metric.
                    k3.metric("Actual Defect Rate", val, delta=None) 
                else:
                    k3.metric("Defect Rate", "N/A", "No History")

                # RELIABILITY
                if stats['has_history']:
                    val = f"{stats['reliability']:.0f}%"
                    # reliability < 90 is bad. 
                    delta = stats['reliability'] - 100 # Gap to perfection
                    k4.metric("On-Time Rate", val, f"{stats['deliveries']} deliveries")
                else:
                    k4.metric("On-Time Rate", "N/A", "No History")
                
                st.divider()
                # Financial Impact
                if stats['has_history']:
                    c_fin, c_min = st.columns(2)
                    c_fin.markdown(f"**Total Rework Cost**: :red[${stats['total_rework']:,.0f}]")
                    c_min.markdown(f"Min Order Qty: **{s.min_order_qty}**")
                else:
                     st.caption("Place orders to generate performance data.")

elif menu == "💰 Financials":
    st.subheader("💰 Financials & Accounts Payable")
    st.write("Manage invoices and supplier relationships. Pay early to gain trust!")
    
    # 1. Supplier Trust Board
    st.write("##### 🤝 Supplier Relationship Score (0-100)")
    cols = st.columns(len(state.available_suppliers))
    for i, s in enumerate(state.available_suppliers):
        with cols[i]:
            val = round(s.relationship_score, 1)
            delta = None
            if val < 30: 
                color = "red" 
                status = "CRITICAL"
            elif val > 80: 
                color = "green" 
                status = "Excellent"
            else: 
                color = "off" 
                status = "Neutral"
            
            st.metric(s.name, f"{val}/100", status)
            if s.is_blocked:
                st.error("BLOCKED 🛑")

    st.divider()
    
    # 2. Invoices
    st.write("##### 🧾 Unpaid Invoices")
    
    unpaid = [i for i in state.invoices if i.status == "Unpaid"]
    
    if not unpaid:
        st.success("No pending invoices. Great job!")
    else:
        # Table with Actions
        # We'll use columns for a simple list view
        for inv in unpaid:
            supp = next((s for s in state.available_suppliers if s.id == inv.supplier_id), None)
            
            # Color code based on due date
            days_left = inv.due_day - state.current_day
            
            with st.container(border=True):
                c1, c2, c3, c4, c5 = st.columns([2, 1, 1, 1, 1])
                c1.markdown(f"**{supp.name}** (Inv #{inv.id})")
                c2.write(f"${inv.amount:,.0f}")
                
                if days_left < 0:
                    c3.markdown(f":red[Overdue {-days_left}d]")
                elif days_left == 0:
                    c3.markdown(f":orange[Due Today]")
                else:
                    c3.markdown(f":green[Due in {days_left}d]")
                
                # Pay Button
                # Key must be unique
                if c5.button("PAY 💸", key=f"pay_{inv.id}", type="primary" if days_left < 2 else "secondary"):
                    logic.pay_invoice(state, inv.id)
                    st.toast(f"Paid ${inv.amount:,.0f} to {supp.name}")
                    st.rerun()

# Footer Analysis

