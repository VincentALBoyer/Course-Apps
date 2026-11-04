import random
from dataclasses import dataclass, field
from typing import List, Dict, Optional

# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class SalesRep:
    name: str
    level: str  # Junior, Mid, Senior
    win_bonus: int  # Base % bonus to add to lead probability
    speed: str  # Normal, Fast
    specialty: str  # Small, Mid-market, Enterprise
    deals_closed: int = 0
    deals_lost: int = 0
    total_revenue: float = 0
    streak: int = 0  # Positive = wins, negative = losses

@dataclass
class Lead:
    id: int
    company: str
    tier: str  # Small, Mid-market, Enterprise
    stage: str  # New, Qualification, Proposal, Negotiation, Closed Won, Closed Lost
    value: float
    base_win_probability: int  # 0-100
    created_day: int
    days_in_stage: int = 0
    assigned_rep: Optional[str] = None
    
    def get_effective_probability(self, reps: Dict[str, SalesRep], workload: int = 0) -> int:
        if not self.assigned_rep or self.assigned_rep not in reps:
            return self.base_win_probability
        
        rep = reps[self.assigned_rep]
        prob = self.base_win_probability + rep.win_bonus
        
        # Match bonus: right rep for right tier
        if self.tier == rep.specialty:
            prob += 5
        
        # Streak effects
        if rep.streak >= 3:
            prob += 5
        elif rep.streak <= -3:
            prob -= 5
            
        # Rep Overload Penalty (New)
        # Thresholds: 1-2 leads: 0, 3 leads: -5%, 4 leads: -15%, 5+ leads: -30%
        if workload == 3:
            prob -= 5
        elif workload == 4:
            prob -= 15
        elif workload >= 5:
            prob -= 30
        
        return min(100, max(0, prob))

@dataclass
class Ticket:
    id: int
    customer: str
    issue: str
    severity: str  # Low, Medium, High
    created_day: int
    status: str = "Open"  # Open, Resolved
    resolved_day: Optional[int] = None

@dataclass
class Customer:
    id: int
    name: str
    tier: str  # Small, Mid-market, Enterprise
    mrr: float
    csat: int  # 0-100
    days_active: int = 0
    primary_contact: str = ""  # Which rep owns this account

@dataclass
class GameState:
    current_day: int = 1
    max_days: int = 30
    cash: float = 10000.0
    
    # Sales team
    reps: Dict[str, SalesRep] = field(default_factory=dict)
    
    # Pipeline
    leads: List[Lead] = field(default_factory=list)
    next_lead_id: int = 1
    
    # Customers
    customers: List[Customer] = field(default_factory=list)
    tickets: List[Ticket] = field(default_factory=list)
    next_customer_id: int = 1
    next_ticket_id: int = 1
    
    # Financials
    total_revenue: float = 0
    total_costs: float = 0
    
    # History
    daily_events: List[str] = field(default_factory=list)
    history: List[Dict] = field(default_factory=list)
    
    game_over: bool = False

# =============================================================================
# CONSTANTS
# =============================================================================

COMPANY_NAMES = [
    "TechStart Inc", "Global Solutions", "NextGen Systems", "AccelCorp",
    "BlueSky Ventures", "Prime Industries", "Vertex Group", "Quantum Labs",
    "Fusion Dynamics", "Apex Partners", "Stellar Enterprises", "NovaWorks",
    "Zenith Corp", "OptiMax", "CoreLogic", "Pinnacle Group"
]

ISSUES = [
    "Software integration failure",
    "Performance degradation",
    "Missing features in contract",
    "Billing discrepancy",
    "Training request",
    "Data migration issue",
    "API connectivity problems",
    "User access issues"
]

# =============================================================================
# INITIALIZATION
# =============================================================================

def init_sales_team() -> Dict[str, SalesRep]:
    return {
        "Alex Chen": SalesRep(
            "Alex Chen", "Senior", 15, "Normal", "Enterprise",
            deals_closed=24, deals_lost=6, total_revenue=620000, streak=2
        ),
        "Jordan Smith": SalesRep(
            "Jordan Smith", "Mid", 10, "Fast", "Mid-market",
            deals_closed=18, deals_lost=9, total_revenue=245000, streak=1
        ),
        "Taylor Kim": SalesRep(
            "Taylor Kim", "Junior", 5, "Normal", "Small",
            deals_closed=12, deals_lost=8, total_revenue=58000, streak=-1
        ),
        "Morgan Lee": SalesRep(
            "Morgan Lee", "Junior", 0, "Fast", "Small",
            deals_closed=8, deals_lost=12, total_revenue=42000, streak=-2
        )
    }

def create_lead(state: GameState, tier: str = None, prob_range: tuple = (30, 70)) -> Lead:
    """Generate a new lead"""
    if tier is None:
        tier = random.choices(
            ["Small", "Mid-market", "Enterprise"],
            weights=[50, 35, 15]
        )[0]
    
    # Value based on tier
    if tier == "Small":
        value = random.randint(2000, 7000)
    elif tier == "Mid-market":
        value = random.randint(8000, 20000)
    else:  # Enterprise
        value = random.randint(21000, 50000)
    
    lead = Lead(
        id=state.next_lead_id,
        company=random.choice(COMPANY_NAMES),
        tier=tier,
        stage="New",
        value=value,
        base_win_probability=random.randint(*prob_range),
        created_day=state.current_day
    )
    
    state.next_lead_id += 1
    state.leads.append(lead)
    return lead

def create_customer(state: GameState, tier: str, rep_name: str = "") -> Customer:
    """Create a new customer from a won deal"""
    if tier == "Small":
        mrr = random.randint(300, 800)
    elif tier == "Mid-market":
        mrr = random.randint(900, 2000)
    else:
        mrr = random.randint(2100, 5000)
    
    customer = Customer(
        id=state.next_customer_id,
        name=random.choice(COMPANY_NAMES),
        tier=tier,
        mrr=mrr,
        csat=random.randint(70, 90),
        primary_contact=rep_name
    )
    
    state.next_customer_id += 1
    state.customers.append(customer)
    return customer

def create_ticket(state: GameState, customer_name: str) -> Ticket:
    """Generate a support ticket"""
    severity = random.choices(
        ["Low", "Medium", "High"],
        weights=[50, 35, 15]
    )[0]
    
    ticket = Ticket(
        id=state.next_ticket_id,
        customer=customer_name,
        issue=random.choice(ISSUES),
        severity=severity,
        created_day=state.current_day
    )
    
    state.next_ticket_id += 1
    state.tickets.append(ticket)
    return ticket

# =============================================================================
# GAME LOGIC
# =============================================================================

def assign_rep_to_lead(state: GameState, lead_id: int, rep_name: str):
    """Assign a sales rep to a lead"""
    lead = next((l for l in state.leads if l.id == lead_id), None)
    if lead and lead.stage not in ["Closed Won", "Closed Lost"]:
        lead.assigned_rep = rep_name

def progress_lead(state: GameState, lead: Lead) -> List[str]:
    """Progress a lead through the pipeline"""
    events = []
    
    if lead.stage == "Negotiation":
        # Attempt to close
        workloads = get_rep_workloads(state.leads)
        workload = workloads.get(lead.assigned_rep, 0)
        eff_prob = lead.get_effective_probability(state.reps, workload)
        roll = random.randint(0, 100)
        
        if roll <= eff_prob:
            # WIN!
            lead.stage = "Closed Won"
            state.cash += lead.value
            state.total_revenue += lead.value
            
            # Update rep stats
            rep = state.reps[lead.assigned_rep]
            rep.deals_closed += 1
            rep.total_revenue += lead.value
            rep.streak = max(1, rep.streak + 1) if rep.streak >= 0 else 1
            
            # Create customer
            create_customer(state, lead.tier, lead.assigned_rep)
            
            events.append(f"🎉 WON: {lead.company} - ${lead.value:,.0f} ({lead.assigned_rep})")
            
            # Check for level up
            if rep.level == "Junior" and rep.deals_closed >= 10:
                rep.level = "Senior"
                rep.win_bonus = 15
                events.append(f"⭐ {rep.name} promoted to SENIOR!")
            elif rep.level == "Junior" and rep.deals_closed >= 5:
                rep.level = "Mid"
                rep.win_bonus = 10
                events.append(f"⭐ {rep.name} promoted to MID!")
        else:
            # Check for loss
            if random.random() < 0.20:
                lead.stage = "Closed Lost"
                rep = state.reps[lead.assigned_rep]
                rep.deals_lost += 1
                rep.streak = min(-1, rep.streak - 1) if rep.streak <= 0 else -1
                events.append(f"❌ LOST: {lead.company} chose competitor ({lead.assigned_rep})")
            else:
                events.append(f"⏳ STALLED: {lead.company} needs more time")
    else:
        # Progress to next stage
        stages = ["New", "Qualification", "Proposal", "Negotiation"]
        try:
            idx = stages.index(lead.stage)
            if idx < len(stages) - 1:
                lead.stage = stages[idx + 1]
                lead.days_in_stage = 0
                events.append(f"📈 {lead.company} → {lead.stage}")
        except:
            pass
    
    return events

def resolve_ticket(state: GameState, ticket_id: int, priority: bool = False) -> bool:
    """Resolve a support ticket"""
    ticket = next((t for t in state.tickets if t.id == ticket_id and t.status == "Open"), None)
    if not ticket:
        return False
    
    cost = 800 if priority else 300
    if state.cash < cost:
        return False
    
    state.cash -= cost
    state.total_costs += cost
    ticket.status = "Resolved"
    ticket.resolved_day = state.current_day
    
    # Update customer CSAT
    customer = next((c for c in state.customers if c.name == ticket.customer), None)
    if customer:
        csat_boost = 15 if priority else 5
        customer.csat = min(100, customer.csat + csat_boost)
    
    return True

def generate_marketing_leads(state: GameState, campaign_type: str) -> List[Lead]:
    """Generate leads from marketing campaign"""
    leads = []
    
    if campaign_type == "digital":
        cost = 500
        count = random.randint(1, 2)
        prob_range = (30, 50)
    elif campaign_type == "outbound":
        cost = 1500
        count = random.randint(3, 4)
        prob_range = (40, 60)
    else:  # premium
        cost = 3000
        count = random.randint(2, 3)
        prob_range = (60, 80)
    
    if state.cash < cost:
        return []
    
    state.cash -= cost
    state.total_costs += cost
    
    for _ in range(count):
        tier = "Enterprise" if campaign_type == "premium" else random.choice(["Small", "Mid-market", "Enterprise"])
        lead = create_lead(state, tier, prob_range)
        leads.append(lead)
    
    return leads

def get_rep_workloads(leads: List[Lead]) -> Dict[str, int]:
    """Calculate current workload for each rep"""
    workloads = {}
    for lead in leads:
        if lead.assigned_rep and lead.stage not in ["Closed Won", "Closed Lost"]:
            workloads[lead.assigned_rep] = workloads.get(lead.assigned_rep, 0) + 1
    return workloads

def process_daily_batch(state: GameState):
    """Main daily turn processing"""
    state.daily_events = []
    
    # 1. Progress assigned leads
    workloads = get_rep_workloads(state.leads)
    for lead in state.leads:
        if lead.assigned_rep and lead.stage not in ["Closed Won", "Closed Lost"]:
            events = progress_lead(state, lead)
            state.daily_events.extend(events)
            lead.days_in_stage += 1
    
    
    # 2. Generate organic leads (1-3 per day)
    num_leads = random.randint(1, 3)
    for _ in range(num_leads):
        create_lead(state)
    
    # 4. Customer MRR collection
    mrr_collected = sum(c.mrr for c in state.customers)
    if mrr_collected > 0:
        state.cash += mrr_collected
        state.total_revenue += mrr_collected
        state.daily_events.append(f"💰 MRR Collected: ${mrr_collected:,.0f}")
    
    # 5. Random ticket generation (10% chance per customer)
    for customer in state.customers:
        if random.random() < 0.10:
            create_ticket(state, customer.name)
    
    # 6. Churn checks
    churned = []
    for customer in state.customers:
        customer.days_active += 1
        
        # Degrade CSAT if tickets unresolved
        open_tickets = [t for t in state.tickets if t.customer == customer.name and t.status == "Open"]
        if len(open_tickets) > 0:
            customer.csat = max(0, customer.csat - 3)
        
        # Churn risk
        churn_chance = 0
        if customer.csat < 30:
            churn_chance = 0.60
        elif customer.csat < 50:
            churn_chance = 0.30
        
        if random.random() < churn_chance:
            churned.append(customer)
            state.daily_events.append(f"💔 CHURN: {customer.name} cancelled (CSAT: {customer.csat})")
    
    for c in churned:
        state.customers.remove(c)
    
    # 7. Daily costs
    daily_cost = 400  # Team salary
    pipeline_leads = [l for l in state.leads if l.stage not in ["Closed Won", "Closed Lost"]]
    nurture_cost = len(pipeline_leads) * 50
    total_daily = daily_cost + nurture_cost
    
    state.cash -= total_daily
    state.total_costs += total_daily
    
    # 8. Advance day
    state.current_day += 1
    
    # 9. Check game over
    if state.current_day > state.max_days:
        state.game_over = True
    elif state.cash < 0:
        state.game_over = True
        state.daily_events.append("💀 BANKRUPTCY: Game Over")
    elif len(state.customers) == 0 and len(pipeline_leads) == 0:
        state.game_over = True
        state.daily_events.append("💀 BUSINESS COLLAPSE: No customers or leads")

def get_kpis(state: GameState) -> Dict:
    """Calculate key performance indicators"""
    active_leads = [l for l in state.leads if l.stage not in ["Closed Won", "Closed Lost"]]
    won_leads = [l for l in state.leads if l.stage == "Closed Won"]
    lost_leads = [l for l in state.leads if l.stage == "Closed Lost"]
    
    total_closed = len(won_leads) + len(lost_leads)
    win_rate = (len(won_leads) / total_closed * 100) if total_closed > 0 else 0
    
    pipeline_value = sum(l.value for l in active_leads)
    avg_csat = sum(c.csat for c in state.customers) / len(state.customers) if state.customers else 0
    
    profit = state.total_revenue - state.total_costs
    
    return {
        "day": state.current_day,
        "cash": state.cash,
        "profit": profit,
        "revenue": state.total_revenue,
        "costs": state.total_costs,
        "pipeline_value": pipeline_value,
        "active_leads": len(active_leads),
        "customers": len(state.customers),
        "avg_csat": avg_csat,
        "win_rate": win_rate,
        "deals_won": len(won_leads),
        "deals_lost": len(lost_leads)
    }

def save_snapshot(state: GameState):
    """Save daily snapshot"""
    kpis = get_kpis(state)
    state.history.append(kpis)
