# =============================================================================
# EIS Simulator — CRM Engine
# Customer Relationship Management: leads, pipeline, campaigns, service, health
# =============================================================================
import random
from typing import Tuple, List, Optional
from Archive.ERP_Sim_Integrated.engine.state import SimState, Lead, Customer, ServiceTicket, SalesOrder, ActivityLog
from Archive.ERP_Sim_Integrated.config import CUSTOMERS_CONFIG, CRM_PARAMS


# =============================================================================
# INITIALIZATION — CUSTOMERS
# =============================================================================

def init_customers(state: SimState) -> None:
    """Seed initial customer base when CRM is first enabled."""
    for i, cfg in enumerate(CUSTOMERS_CONFIG):
        cid = f"CUST-{i+1:03d}"
        state.customers[cid] = Customer(
            id=cid,
            name=cfg["name"],
            tier=cfg["tier"],
            city=cfg["city"],
            email=cfg["email"],
            mrr=cfg["mrr_base"] * random.uniform(0.9, 1.1),
            csat=random.randint(75, 95),
            lifetime_value=cfg["mrr_base"] * random.uniform(3, 8),
            is_active=True,
        )


# =============================================================================
# LEAD GENERATION
# =============================================================================

LEAD_COMPANIES = [
    ("Velo Express", "Small"), ("BikeHub Pro", "Mid-Market"), ("Speed Dynamics", "Enterprise"),
    ("UrbanWheel Co", "Small"), ("CycleStar", "Mid-Market"), ("Momentum Sports", "Enterprise"),
    ("GreenWheels", "Small"), ("EliteRide Inc", "Enterprise"), ("PedalPlus", "Mid-Market"),
    ("TrailBoss Retail", "Small"), ("OmniCycle", "Mid-Market"), ("Apex Bike Corp", "Enterprise"),
]

LEAD_CONTACTS = [
    "James Martin", "Sophie Chen", "Ahmed Hassan", "Maria Rodriguez",
    "Luke Thompson", "Priya Patel", "Carlos Mendez", "Anna Kowalski",
    "David Kim", "Emma Laurent", "Raj Sharma", "Fatima Al-Zahrawi",
]


def generate_new_leads(state: SimState, count: int = 1) -> List[Lead]:
    """System generates inbound leads each day."""
    leads = []
    for _ in range(count):
        if not LEAD_COMPANIES:
            break
        company, tier = random.choice(LEAD_COMPANIES)
        contact = random.choice(LEAD_CONTACTS)
        prod_interest = random.sample(list(state.products.keys()), k=random.randint(1, 2))
        value = {
            "Small": random.uniform(2000, 8000),
            "Mid-Market": random.uniform(8000, 30000),
            "Enterprise": random.uniform(30000, 120000),
        }[tier]

        lead = Lead(
            id=state.next_lead_id(),
            day_created=state.current_day,
            company=f"{company} #{random.randint(1,99)}",
            contact_name=contact,
            email=f"{contact.split()[0].lower()}@{company.lower().replace(' ', '')}.com",
            tier=tier,
            estimated_value=round(value, 0),
            product_interest=prod_interest,
            stage="New",
            win_probability={"Small": 35, "Mid-Market": 50, "Enterprise": 70}[tier],
            source=random.choice(["inbound", "referral", "outbound"]),
        )
        state.leads.append(lead)
        state.daily_events.append(
            f"🎯 New Lead: {lead.company} ({tier}) — Est. ${lead.estimated_value:,.0f}"
        )
        _log_crm(state, "Lead_Created", lead.id, "System",
                  f"New {tier} lead: {lead.company}", kpi_tag="crm_leads")
        leads.append(lead)
    return leads


def run_marketing_campaign(state: SimState, campaign_type: str) -> Tuple[bool, str, List[Lead]]:
    """Student spends marketing budget to generate leads."""
    campaigns = CRM_PARAMS["marketing_campaigns"]
    if campaign_type not in campaigns:
        return False, "Unknown campaign type", []

    cfg = campaigns[campaign_type]
    cost = cfg["cost"]

    if state.cash < cost:
        return False, f"Insufficient cash: need ${cost:,.0f}, have ${state.cash:,.0f}", []

    state.cash -= cost
    state.total_crm_marketing_spend += cost

    num_leads = random.randint(cfg["leads_min"], cfg["leads_max"])
    new_leads = []

    for _ in range(num_leads):
        company, tier = random.choice(LEAD_COMPANIES)
        contact = random.choice(LEAD_CONTACTS)
        prod_interest = random.sample(list(state.products.keys()), k=random.randint(1, 2))
        win_pct = random.randint(*cfg["win_prob_range"])
        value = {
            "Small": random.uniform(3000, 10000),
            "Mid-Market": random.uniform(10000, 40000),
            "Enterprise": random.uniform(40000, 150000),
        }[tier]

        lead = Lead(
            id=state.next_lead_id(),
            day_created=state.current_day,
            company=f"{company} #{random.randint(1, 99)}",
            contact_name=contact,
            email=f"{contact.split()[0].lower()}@{company.lower().replace(' ', '')}.com",
            tier=tier,
            estimated_value=round(value, 0),
            product_interest=prod_interest,
            stage="Qualified",  # Campaign leads start at Qualified
            win_probability=win_pct,
            source=campaign_type,
        )
        state.leads.append(lead)
        new_leads.append(lead)

    campaign_labels = {
        "digital_ads": "Digital Ads",
        "outbound_calls": "Outbound Calls",
        "trade_show": "Trade Show",
    }
    state.daily_events.append(
        f"📢 Campaign ({campaign_labels.get(campaign_type, campaign_type)}): "
        f"${cost:,.0f} spent → {num_leads} qualified leads generated"
    )
    _log_crm(state, "Marketing_Campaign", campaign_type, "Student",
              f"Launched {campaign_type}: ${cost:.0f} → {num_leads} leads",
              financial_impact=-cost, kpi_tag="crm_marketing")
    return True, f"{num_leads} leads generated for ${cost:,.0f}", new_leads


# =============================================================================
# PIPELINE MANAGEMENT
# =============================================================================

STAGE_ORDER = ["New", "Qualified", "Proposal", "Negotiation", "Won", "Lost"]


def advance_lead_stage(state: SimState, lead_id: str, new_stage: str) -> Tuple[bool, str]:
    """Student manually advances a lead through the pipeline."""
    lead = _find_lead(state, lead_id)
    if not lead:
        return False, "Lead not found"
    if new_stage not in STAGE_ORDER:
        return False, "Invalid stage"

    current_idx = STAGE_ORDER.index(lead.stage)
    new_idx = STAGE_ORDER.index(new_stage)
    if new_idx <= current_idx and new_stage not in ["Lost"]:
        return False, "Can only advance forward or mark as Lost"

    old_stage = lead.stage
    lead.stage = new_stage
    lead.days_in_stage = 0

    if new_stage == "Won":
        lead.win_probability = 100
        # Auto-create a Sales Order in ERP
        _convert_lead_to_sale(state, lead)
        # Convert to customer if not already
        _convert_lead_to_customer(state, lead)
        state.daily_events.append(
            f"🏆 Opportunity WON: {lead.company} — ${lead.estimated_value:,.0f}"
        )
        _log_crm(state, "Lead_Won", lead.id, "Student",
                  f"Won: {lead.company} — ${lead.estimated_value:,.0f}",
                  financial_impact=lead.estimated_value, kpi_tag="crm_win_rate")
    elif new_stage == "Lost":
        lead.win_probability = 0
        state.daily_events.append(f"📉 Opportunity Lost: {lead.company}")
        _log_crm(state, "Lead_Lost", lead.id, "Student",
                  f"Lost: {lead.company}",
                  financial_impact=-lead.estimated_value * 0.1, kpi_tag="crm_win_rate")
    else:
        state.daily_events.append(f"➡️ Lead {lead.company}: {old_stage} → {new_stage}")
        _log_crm(state, "Lead_Stage_Advanced", lead.id, "Student",
                  f"{lead.company}: {old_stage} → {new_stage}", kpi_tag="crm_pipeline")

    return True, f"Lead moved to {new_stage}"


def advance_crm_pipeline(state: SimState) -> None:
    """Daily automatic pipeline advancement for unattended leads."""
    for lead in state.leads:
        if lead.stage in ("Won", "Lost"):
            continue
        lead.days_in_stage += 1

        # Old leads eventually go cold (auto-Lost after 10 days with no progress)
        if lead.days_in_stage > 10 and lead.stage == "New":
            lead.stage = "Lost"
            lead.win_probability = 0
            state.daily_events.append(f"📉 Lead went cold (no follow-up): {lead.company}")

        # Small chance of natural progression each day
        if lead.stage in ("Qualified", "Proposal") and random.random() < 0.15:
            idx = STAGE_ORDER.index(lead.stage)
            lead.stage = STAGE_ORDER[idx + 1]
            lead.days_in_stage = 0


def _convert_lead_to_sale(state: SimState, lead: Lead) -> None:
    """Auto-create ERP Sales Order when lead is Won."""
    if not lead.product_interest:
        return
    prod_id = lead.product_interest[0]
    prod = state.products.get(prod_id)
    if not prod:
        return

    # Estimate qty from deal value
    qty = max(1, int(lead.estimated_value / prod.price))

    # Find matching customer id
    cust_id = next((c.id for c in state.customers.values() if c.name == lead.company), None)

    so = SalesOrder(
        id=state.next_so_id(),
        day_placed=state.current_day,
        customer_name=lead.company,
        customer_id=cust_id,
        product_id=prod_id,
        qty=qty,
        unit_price=prod.price,
        due_day=state.current_day + 7,
        source="crm_opportunity",
        opportunity_id=lead.id,
    )
    state.sales_orders.append(so)
    state.daily_events.append(
        f"📋 ERP Sales Order {so.id} auto-created from CRM win: {qty}x {prod.name}"
    )


def _convert_lead_to_customer(state: SimState, lead: Lead) -> None:
    """Add lead's company as an active customer if not already there."""
    existing = next((c for c in state.customers.values() if c.name == lead.company), None)
    if not existing:
        cid = f"CUST-{len(state.customers) + 1:03d}"
        mrr = lead.estimated_value / 12
        state.customers[cid] = Customer(
            id=cid,
            name=lead.company,
            tier=lead.tier,
            city="",
            email=lead.email,
            mrr=mrr,
            csat=80,
            lifetime_value=lead.estimated_value,
            is_active=True,
        )


# =============================================================================
# SERVICE TICKETS
# =============================================================================

def create_service_ticket(state: SimState, customer_id: str, issue: str,
                           severity: str) -> Tuple[bool, str]:
    cust = state.customers.get(customer_id)
    if not cust:
        return False, "Customer not found"

    ticket = ServiceTicket(
        id=state.next_ticket_id(),
        customer_id=customer_id,
        customer_name=cust.name,
        day_opened=state.current_day,
        issue=issue,
        severity=severity,
    )
    state.service_tickets.append(ticket)
    cust.open_tickets += 1

    state.daily_events.append(
        f"🎫 Service Ticket {ticket.id}: {cust.name} — [{severity}] {issue}"
    )
    _log_crm(state, "Ticket_Created", ticket.id, "System",
              f"{cust.name}: {severity} — {issue}", kpi_tag="crm_service")
    return True, ticket.id


def resolve_ticket(state: SimState, ticket_id: str, priority: bool = False) -> Tuple[bool, str]:
    ticket = next((t for t in state.service_tickets if t.id == ticket_id), None)
    if not ticket:
        return False, "Ticket not found"
    if ticket.status in ("Resolved",):
        return False, "Already resolved"

    cost = 800 if priority else 300
    csat_gain = 10 if priority else 5

    if state.cash < cost:
        return False, f"Insufficient cash: ${cost}"

    state.cash -= cost
    ticket.status = "Resolved"
    ticket.resolved_day = state.current_day
    ticket.resolution_cost = cost

    cust = state.customers.get(ticket.customer_id)
    if cust:
        cust.csat = min(100, cust.csat + csat_gain)
        cust.open_tickets = max(0, cust.open_tickets - 1)

    state.daily_events.append(
        f"✅ Ticket {ticket_id} resolved ({'Priority' if priority else 'Standard'}): "
        f"${cost} — CSAT +{csat_gain}"
    )
    _log_crm(state, "Ticket_Resolved", ticket_id, "Student",
              f"Resolved {ticket.severity} ticket for {ticket.customer_name}",
              financial_impact=-cost, kpi_tag="crm_service")
    return True, "Resolved"


def _auto_generate_tickets(state: SimState) -> None:
    """Random ticket generation from active customers."""
    for cust in state.customers.values():
        if not cust.is_active:
            continue
        if cust.csat < 70 and random.random() < 0.3:
            issues = ["Delivery delay", "Product defect", "Billing error", "Wrong model shipped"]
            severity = "High" if cust.csat < 50 else "Medium"
            create_service_ticket(state, cust.id, random.choice(issues), severity)


# =============================================================================
# CUSTOMER HEALTH & CHURN
# =============================================================================

def compute_customer_health(cust: Customer) -> str:
    if cust.csat >= 80:
        return "Healthy"
    elif cust.csat >= 60:
        return "At Risk"
    else:
        return "Critical"


def get_crm_kpis(state: SimState) -> dict:
    leads = state.leads
    won = [l for l in leads if l.stage == "Won"]
    lost = [l for l in leads if l.stage == "Lost"]
    total_closed = len(won) + len(lost)
    win_rate = (len(won) / max(1, total_closed)) * 100 if total_closed > 0 else 0.0
    pipeline_value = sum(l.estimated_value for l in leads if l.stage not in ("Won", "Lost"))
    active_customers = len([c for c in state.customers.values() if c.is_active])
    avg_csat = (sum(c.csat for c in state.customers.values()) / max(1, len(state.customers))
                if state.customers else 0)
    open_tickets = len([t for t in state.service_tickets if t.status == "Open"])
    resolved_tickets = len([t for t in state.service_tickets if t.status == "Resolved"])
    revenue_from_crm = sum(
        so.qty * so.unit_price for so in state.sales_orders
        if so.source == "crm_opportunity" and so.status == "Shipped"
    )
    return {
        "Total Leads": len(leads),
        "Leads Won": len(won),
        "Leads Lost": len(lost),
        "Win Rate %": f"{win_rate:.1f}%",
        "Pipeline Value": f"${pipeline_value:,.0f}",
        "Active Customers": active_customers,
        "Average CSAT": f"{avg_csat:.0f}%",
        "Open Tickets": open_tickets,
        "Resolved Tickets": resolved_tickets,
        "Revenue from CRM Deals": f"${revenue_from_crm:,.0f}",
        "Marketing Spend": f"${state.total_crm_marketing_spend:,.0f}",
        "CAC (Cost per Lead Won)": f"${(state.total_crm_marketing_spend / max(1, len(won))):,.0f}",
    }


# =============================================================================
# HELPERS
# =============================================================================

def _find_lead(state: SimState, lead_id: str) -> Optional[Lead]:
    return next((l for l in state.leads if l.id == lead_id), None)


def _log_crm(state: SimState, event_type: str, ref_id: str, actor: str,
             desc: str, financial_impact: float = 0, kpi_tag: str = ""):
    state.activity_log.append(ActivityLog(
        day=state.current_day,
        timestamp_sim=f"Day {state.current_day}",
        module="CRM",
        event_type=event_type,
        ref_id=ref_id,
        actor=actor,
        description=desc,
        financial_impact=financial_impact,
        kpi_tag=kpi_tag,
    ))
