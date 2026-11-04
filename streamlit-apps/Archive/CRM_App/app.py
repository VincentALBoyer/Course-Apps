import streamlit as st
import pandas as pd
import Archive.CRM_App.logic as logic

# =============================================================================
# PAGE CONFIGURATION
# =============================================================================
st.set_page_config(
    page_title="Salesforce CRM Simulation | Sales Console",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Theme-Agnostic High-Contrast Styling
st.markdown("""
<style>
    /* === TOTAL REFINEMENT === */
    .stApp {
        background-color: #f7f9fc !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }
    
    /* Header - Modern Salesforce-like Blue */
    .crm-header { 
        background: linear-gradient(135deg, #1589ee 0%, #0070d2 100%) !important; 
        padding: 1.5rem 2.5rem; 
        border-radius: 12px;
        box-shadow: 0 8px 16px rgba(0,112,210,0.15);
        margin-bottom: 2.5rem;
    }
    .crm-header h2 { 
        color: #ffffff !important; 
        margin: 0 !important; 
        font-weight: 700 !important;
        font-size: 1.8rem !important;
    }
    
    /* Metrics - Balanced Width */
    [data-testid="stMetric"] {
        background-color: #ffffff !important;
        padding: 0.8rem !important;
        border-radius: 10px !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05) !important;
        border: 1px solid #e0e6ed !important;
        min-width: 150px !important;
    }
    [data-testid="stMetricValue"] { 
        color: #1a1a1a !important; 
        font-weight: 800 !important; 
        font-size: 1.5rem !important;
        white-space: nowrap !important;
        overflow: visible !important;
    }
    
    /* Target specific metric parts to prevent truncation */
    [data-testid="stMetricValue"] > div {
        overflow: visible !important;
        width: auto !important;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# SESSION STATE INITIALIZATION
# =============================================================================
if 'crm_state' not in st.session_state:
    st.session_state.crm_state = logic.GameState()
    state = st.session_state.crm_state
    state.reps = logic.init_sales_team()
    
    # Create initial leads
    for _ in range(5):
        logic.create_lead(state)
    
    # Create initial customers
    for _ in range(3):
        tier = ["Small", "Mid-market", "Enterprise"][_ % 3]
        logic.create_customer(state, tier, list(state.reps.keys())[_ % 4])
    
    logic.save_snapshot(state)

state = st.session_state.crm_state

# =============================================================================
# CALLBACKS
# =============================================================================
def handle_next_day():
    logic.process_daily_batch(state)
    logic.save_snapshot(state)

def handle_marketing(campaign_type):
    leads = logic.generate_marketing_leads(state, campaign_type)
    if leads:
        st.toast(f"✅ Generated {len(leads)} leads from {campaign_type} campaign!", icon="📢")
    else:
        st.error("Insufficient cash for this campaign.")

def handle_resolve_ticket(ticket_id, priority=False):
    if logic.resolve_ticket(state, ticket_id, priority):
        level = "Priority" if priority else "Standard"
        st.toast(f"✅ Ticket #{ticket_id} resolved ({level})", icon="🎫")
    else:
        st.error("Insufficient cash to resolve ticket.")

# =============================================================================
# SIDEBAR
# =============================================================================
with st.sidebar:
    st.markdown("### 📊 SALESFORCE CRM")
    st.divider()
    menu = st.radio("Sales Modules", [
        "📈 Executive Dashboard",
        "🎯 Sales Pipeline",
        "📢 Marketing Center",
        "🎫 Service Desk",
        "👥 Team Performance",
        "📑 Reports"
    ])
    
    st.divider()
    st.subheader("Business Period")
    st.metric("Day", f"{state.current_day} / {state.max_days}")
    st.metric("Cash Balance", f"${state.cash:,.0f}")
    
    if not state.game_over:
        st.button("➡️ RUN DAILY BATCH", type="primary", use_container_width=True, on_click=handle_next_day)
    else:
        st.error("Month Complete (30 Days)")
        if st.button("🔄 Reset Simulation", use_container_width=True):
            del st.session_state.crm_state
            st.rerun()

# =============================================================================
# MAIN DASHBOARD
# =============================================================================
kpis = logic.get_kpis(state)

if menu == "📈 Executive Dashboard":
    st.markdown("<div class='crm-header'><h2>Executive Dashboard</h2></div>", unsafe_allow_html=True)
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Profit", f"${kpis['profit']:,.0f}")
    c2.metric("Pipeline Value", f"${kpis['pipeline_value']:,.0f}")
    c3.metric("Active Customers", kpis['customers'])
    c4.metric("Win Rate", f"{kpis['win_rate']:.1f}%")
    
    st.divider()
    
    col_chart, col_log = st.columns([2, 1])
    with col_chart:
        st.markdown("### 📊 Financial Performance")
        if state.history:
            df = pd.DataFrame(state.history)
            st.line_chart(df.set_index("day")[["revenue", "costs", "profit"]], height=300)
    
    with col_log:
        st.markdown("### 📜 Recent Activity")
        with st.container(height=300):
            if state.daily_events:
                for e in reversed(state.daily_events):
                    st.write(e)
            else:
                st.caption("Awaiting first batch...")

elif menu == "🎯 Sales Pipeline":
    st.markdown("<div class='crm-header'><h2>Sales Pipeline Management</h2></div>", unsafe_allow_html=True)
    
    # Calculate workloads once for the whole module
    workloads = logic.get_rep_workloads(state.leads)
    st.markdown("### 👤 Daily Rep Assignments (Max 4)")
    st.info("Assign reps to leads. Matching rep specialty to lead tier gives +5% win bonus!")
    
    active_leads = [l for l in state.leads if l.stage not in ["Closed Won", "Closed Lost"]]
    
    if not active_leads:
        st.warning("No active leads in pipeline. Use Marketing Center to generate leads!")
    else:
        # Group by stage
        stages = ["New", "Qualification", "Proposal", "Negotiation"]
        
        for stage in stages:
            stage_leads = [l for l in active_leads if l.stage == stage]
            if stage_leads:
                st.markdown(f"#### {stage} ({len(stage_leads)})")
                
                for lead in stage_leads:
                    with st.container(border=True):
                        c1, c2, c3, c4 = st.columns([1.2, 0.6, 0.6, 1.3])
                        
                        with c1:
                            st.markdown(f"**{lead.company}**")
                            st.caption(f"ID: {lead.id} • {lead.tier}")
                        
                        with c2:
                            st.metric("Value", f"${lead.value:,.0f}")
                        
                        with c3:
                            st.metric("Win Prob", f"{lead.base_win_probability}%")
                        
                        # Rep selector with specialty match indicators and efficiency
                        rep_options = ["Unassigned"]
                        rep_display_map = {"Unassigned": "Unassigned"}
                        
                        for rep_name, rep in state.reps.items():
                            load = workloads.get(rep_name, 0)
                            # Calculate effective probability with overload penalty
                            eff_prob = lead.get_effective_probability(state.reps, load)
                            
                            # Check if specialty matches this lead's tier
                            is_match = lead.tier == rep.specialty
                            match_icon = "🎯" if is_match else "⚡"
                            
                            # Overload indicator
                            load_icon = "🔴" if load >= 3 else "🟢"
                            
                            # Build display name with efficiency, specialty and LOAD
                            display_name = f"{rep_name} {match_icon} {eff_prob}% (Load: {load}) {load_icon}"
                            rep_options.append(display_name)
                            rep_display_map[display_name] = rep_name
                        
                        # Find current selection
                        current_assignment = lead.assigned_rep if lead.assigned_rep else "Unassigned"
                        if current_assignment != "Unassigned":
                            # Find the display name for current assignment
                            for display, actual in rep_display_map.items():
                                if actual == current_assignment:
                                    current_assignment = display
                                    break
                        
                        selected_display = c4.selectbox(
                            f"Assign Rep",
                            rep_options,
                            index=rep_options.index(current_assignment) if current_assignment in rep_options else 0,
                            key=f"rep_{lead.id}",
                            label_visibility="collapsed"
                        )
                        
                        # Get actual rep name from selection
                        rep_name = rep_display_map.get(selected_display, "Unassigned")
                        
                        # Always assign the selection (even if it's the same)
                        if rep_name != "Unassigned":
                            logic.assign_rep_to_lead(state, lead.id, rep_name)
                            rep = state.reps[rep_name]
                            load = workloads.get(rep_name, 0)
                            eff_prob = lead.get_effective_probability(state.reps, load)
                            
                            # Specialty match indicator
                            specialty_match = lead.tier == rep.specialty
                            specialty_icon = "🎯" if specialty_match else "⚡"
                            specialty_text = "Match +5%" if specialty_match else "No bonus"
                            
                            # Quality indicator based on effective probability
                            if eff_prob >= 70:
                                quality_icon = "✅"
                                quality_text = "Strong"
                            elif eff_prob >= 50:
                                quality_icon = "⚠️"
                                quality_text = "OK"
                            else:
                                quality_icon = "❌"
                                quality_text = "Weak"
                            
                            c4.caption(f"{specialty_icon} {specialty_text}")
                            c4.caption(f"{quality_icon} {quality_text}: {eff_prob}%")
                        else:
                            # Clear assignment if Unassigned is selected
                            lead.assigned_rep = None
    
    st.divider()
    st.markdown("### 📋 Closed Deals (Last 10)")
    closed = [l for l in state.leads if l.stage in ["Closed Won", "Closed Lost"]]
    if closed:
        # Sort by most recent first
        closed.sort(key=lambda x: x.created_day, reverse=True)
        closed_data = [{
            "ID": l.id,
            "Company": l.company,
            "Tier": l.tier,
            "Result": "Won" if l.stage == "Closed Won" else "Lost",
            "Value": f"${l.value:,.0f}",
            "Day": l.created_day
        } for l in closed[-10:]]
        st.dataframe(pd.DataFrame(closed_data), use_container_width=True, hide_index=True)
    else:
        st.info("No closed deals yet. Advance through the pipeline to see results!")

elif menu == "📢 Marketing Center":
    st.markdown("<div class='crm-header'><h2>Marketing Campaign Center</h2></div>", unsafe_allow_html=True)
    
    st.markdown("### Launch Campaigns to Generate Leads")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        with st.container(border=True):
            st.markdown("#### 💻 Digital Ads")
            st.metric("Cost", "$500")
            st.write("- **1-2 leads**")
            st.write("- **30-50% win probability**")
            st.write("- Quick turnaround")
            st.button("🚀 Launch Digital", key="digital", 
                     on_click=lambda: handle_marketing("digital"),
                     use_container_width=True)
    
    with col2:
        with st.container(border=True):
            st.markdown("#### 📞 Outbound Campaign")
            st.metric("Cost", "$1,500")
            st.write("- **3-4 leads**")
            st.write("- **40-60% win probability**")
            st.write("- Balanced approach")
            st.button("🚀 Launch Outbound", key="outbound",
                     on_click=lambda: handle_marketing("outbound"),
                     use_container_width=True)
    
    with col3:
        with st.container(border=True):
            st.markdown("#### ⭐ Premium Events")
            st.metric("Cost", "$3,000")
            st.write("- **2-3 high-value leads**")
            st.write("- **60-80% win probability**")
            st.write("- Enterprise tier")
            st.button("🚀 Launch Premium", key="premium",
                     on_click=lambda: handle_marketing("premium"),
                     use_container_width=True)

elif menu == "🎫 Service Desk":
    st.markdown("<div class='crm-header'><h2>Customer Service Desk</h2></div>", unsafe_allow_html=True)
    
    open_tickets = [t for t in state.tickets if t.status == "Open"]
    
    if not open_tickets:
        st.success("No open support tickets!")
    else:
        st.warning(f"{len(open_tickets)} tickets require attention")
        
        for ticket in open_tickets:
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([1.5, 0.6, 0.6, 1.5])
                
                with c1:
                    st.write(f"**{ticket.customer}**")
                    st.caption(f"Ticket #{ticket.id} • {ticket.issue}")
                
                with c2:
                    severity_color = {"Low": "#2e7d32", "Medium": "#ed6c02", "High": "#d32f2f"}[ticket.severity]
                    st.markdown(f"<p style='margin-bottom:0; font-size:0.8rem; color:#54698d'>SEVERITY</p><span style='color:{severity_color}; font-weight:700'>{ticket.severity}</span>", unsafe_allow_html=True)
                
                with c3:
                    st.markdown(f"<p style='margin-bottom:0; font-size:0.8rem; color:#54698d'>OPEN SINCE</p><span style='font-weight:600'>Day {ticket.created_day}</span>", unsafe_allow_html=True)
                
                with c4:
                    col_btns = st.columns(2)
                    if col_btns[0].button("Standard ($300)", key=f"std_{ticket.id}", use_container_width=True):
                        handle_resolve_ticket(ticket.id, False)
                        st.rerun()
                    
                    if col_btns[1].button("Priority ($800)", key=f"pri_{ticket.id}", use_container_width=True):
                        handle_resolve_ticket(ticket.id, True)
                        st.rerun()
    
    st.divider()
    st.markdown("### 📊 Customer Health")
    if state.customers:
        health_data = [{
            "Customer": c.name,
            "Tier": c.tier,
            "MRR": f"${c.mrr:,.0f}",
            "CSAT": f"{c.csat}%",
            "Status": "🟢 Healthy" if c.csat >= 70 else "🟡 At Risk" if c.csat >= 50 else "🔴 Critical"
        } for c in state.customers]
        st.dataframe(pd.DataFrame(health_data), use_container_width=True, hide_index=True)

elif menu == "👥 Team Performance":
    st.markdown("<div class='crm-header'><h2>Sales Team Performance</h2></div>", unsafe_allow_html=True)
    
    workloads = logic.get_rep_workloads(state.leads)
    
    for rep_name, rep in state.reps.items():
        with st.container(border=True):
            st.markdown(f"#### 👤 {rep.name}")
            
            c1, c2, c3, c4, c5, c6 = st.columns(6)
            c1.metric("Level", rep.level)
            c2.metric("Closed", rep.deals_closed)
            c3.metric("Revenue", f"${rep.total_revenue:,.0f}")
            
            total_deals = rep.deals_closed + rep.deals_lost
            win_rate = (rep.deals_closed / total_deals * 100) if total_deals > 0 else 0
            c4.metric("Win Rate", f"{win_rate:.1f}%")
            
            load = workloads.get(rep_name, 0)
            load_status = "🟢 Low" if load <= 2 else "🟡 Medium" if load <= 4 else "🔴 OVERLOAD"
            c5.metric("Current Load", f"{load} Deals", delta=load_status, delta_color="normal")
            
            if rep.streak > 0:
                streak_text = f"🔥 {rep.streak} wins"
            elif rep.streak < 0:
                streak_text = f"❄️ {abs(rep.streak)} losses"
            else:
                streak_text = "Neutral"
            c6.metric("Streak", streak_text)
            
            st.caption(f"**Specialty**: {rep.specialty} | **Bonus**: +{rep.win_bonus}%")

elif menu == "📑 Reports":
    st.markdown("<div class='crm-header'><h2>Business Intelligence Reports</h2></div>", unsafe_allow_html=True)
    
    st.markdown("### Export Data")
    c1, c2 = st.columns(2)
    
    with c1:
        if state.leads:
            leads_df = pd.DataFrame([{
                "ID": l.id, "Company": l.company, "Tier": l.tier,
                "Stage": l.stage, "Value": l.value, "Win%": l.base_win_probability
            } for l in state.leads])
            csv = leads_df.to_csv(index=False)
            st.download_button("📥 Export Pipeline", csv, "pipeline.csv")
    
    with c2:
        if state.customers:
            customers_df = pd.DataFrame([{
                "ID": c.id, "Name": c.name, "Tier": c.tier,
                "MRR": c.mrr, "CSAT": c.csat, "Days": c.days_active
            } for c in state.customers])
            csv = customers_df.to_csv(index=False)
            st.download_button("📥 Export Customers", csv, "customers.csv")
    
    st.divider()
    st.markdown("### Performance History")
    if state.history:
        st.dataframe(pd.DataFrame(state.history), use_container_width=True, hide_index=True)
