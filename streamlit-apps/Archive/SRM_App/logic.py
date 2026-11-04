import random
import pandas as pd
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class Delivery:
    """Represents a completed delivery for analysis"""
    id: str
    day_arrived: int
    supplier_name: str
    qty_received: int
    qty_defective: int
    rework_cost: float
    status: str # On Time, Late
    unit_price: float
    day_placed: int # Added for Lead Time Calc
    quoted_lead_time: int

@dataclass
class Invoice:
    id: str
    po_id: str
    supplier_id: str
    amount: float
    due_day: int
    status: str = "Unpaid" # Unpaid, Paid
    
@dataclass
class PurchaseOrder:
    """A specific order placed by the student"""
    id: str
    supplier_id: str
    day_placed: int
    qty_ordered: int
    quoted_lead_time: int
    expected_arrival_day: int
    unit_price: float = 0.0 # Stored price at time of order
    status: str = "Open" # Open, Shipped, Received, Processing
    arrival_day: Optional[int] = None

@dataclass
class Supplier:
    id: str
    name: str 
    category: str
    
    # VISIBLE
    quoted_price: float
    current_price: float 
    previous_price: float # For day-to-day delta
    quoted_lead_time: int
    min_order_qty: int
    

    
    # HIDDEN
    true_reliability: float 
    true_defect_rate: float 
    true_lead_time_var: int 
    true_price_volatility: float 
    
    description: str

    # RELATIONSHIP (Moved to end to allow defaults)
    relationship_score: float = 50.0 # 0 to 100. <20 Blocked. >80 Discounts.
    is_blocked: bool = False

@dataclass
class GameState:
    current_day: int = 1
    max_days: int = 30
    cash: float = 50000.0
    
    # Sourcing
    available_suppliers: List[Supplier] = field(default_factory=list)
    active_supplier: Optional[Supplier] = None
    
    # Inventory & MRP
    inventory: int = 500 # Start with some buffer
    production_schedule: Dict[int, int] = field(default_factory=dict) # Day -> Qty Needed
    active_pos: List[PurchaseOrder] = field(default_factory=list)
    
    # Analytics
    delivery_log: List[Delivery] = field(default_factory=list)
    daily_events: List[str] = field(default_factory=list)
    
    # Financials
    total_spend: float = 0.0
    total_rework_cost: float = 0.0
    total_stockout_penalty: float = 0.0
    total_storage_cost: float = 0.0 
    
    invoices: List[Invoice] = field(default_factory=list)
    
    # Settings
    holding_cost_per_unit: float = 2.0 # $2 per unit per day
    
    game_over: bool = False

# =============================================================================
# INITIALIZATION
# =============================================================================

def init_game() -> GameState:
    state = GameState()
    
    # 1. Suppliers (Same as before but with Min Order Qty)
    # 1. Suppliers
    state.available_suppliers = [
        Supplier("V-LOW", "CutRate Sensors", "Components", 10.0, 10.0, 10.0, 5, 200, 0.70, 0.15, 4, 0.05, "Aggressive pricing, spotty quality."),
        Supplier("V-FAST", "Express Components", "Components", 25.0, 25.0, 25.0, 1, 10, 0.98, 0.01, 0, 0.05, "Overnight delivery premium. Reliable."),
        Supplier("V-MID", "Standard Supply", "Components", 14.0, 14.0, 14.0, 5, 100, 0.90, 0.03, 2, 0.10, "Balanced choice for standard needs."),
        Supplier("V-VOL", "Global Trading", "Components", 11.0, 11.0, 11.0, 8, 500, 0.85, 0.05, 5, 0.40, "High volume importer. Volatile.")
    ]
    
    # 2. Generate Production Schedule (The Demand)
    # Variable demand pattern to force planning
    for day in range(1, 32):
        # Base demand 100, spikes every 5 days
        demand = 100
        if day % 5 == 0:
            demand = 300 # Surge
        if day > 20: 
            demand += 50 # Late sim ramp up
        
        # Add some noise
        demand += random.randint(-10, 20)
        state.production_schedule[day] = demand
        
    return state

def commit_draft_orders(state: GameState):
    """Transition Draft POs to Open, deducting cash."""
    drafts = [po for po in state.active_pos if po.status == "Draft"]
    confirmed_count = 0
    
    for po in drafts:
        supp = next((s for s in state.available_suppliers if s.id == po.supplier_id), None)
        if not supp:
            # Handle deleted or changed supplier from old session state
            po.status = "Cancelled"
            continue
            
        cost = po.qty_ordered * supp.current_price
        
        # Final Budget Check (Removed - Unlimited)
        # if state.cash >= cost:
        if True:
            # MOVED CASH DEDUCTION TO INVOICE PAYMENT
            # state.cash -= cost 
            state.total_spend += cost
            po.status = "Open"
            
            # Create Invoice (Due at Delivery)
            inv = Invoice(
                id=f"INV-{po.id}",
                po_id=po.id,
                supplier_id=supp.id,
                amount=cost,
                due_day=po.expected_arrival_day
            )
            state.invoices.append(inv)
            
            state.daily_events.append(f"📝 PO Confirmed: {po.qty_ordered} from {supp.name} (Inv Due Day {inv.due_day})")
            confirmed_count += 1
        # else:
        #    ...
            
    return confirmed_count

# =============================================================================
# GAME ACTIONS
# =============================================================================

def switch_supplier(state: GameState, supplier_id: str):
    """Switch active supplier. In a complex sim, this might cost money/time."""
    supp = next((s for s in state.available_suppliers if s.id == supplier_id), None)
    if supp:
        # If switching, maybe a small admin fee?
        if state.active_supplier is not None and state.active_supplier.id != supplier_id:
             state.daily_events.append(f"🔄 Switched partner to {supp.name}")
        state.active_supplier = supp

def place_order(state: GameState, supplier_id: str, qty: int, status: str = "Open"):
    """Manual PO placement. If status='Draft', no cash deduction yet."""
    supp = next((s for s in state.available_suppliers if s.id == supplier_id), None)
    if not supp:
        return False, "Invalid Supplier"
        
    if supp.is_blocked:
        return False, "Supplier Blocked - Improve Reputation"
    
    if qty < supp.min_order_qty:
        return False, f"Below Min Order Qty ({supp.min_order_qty})"
    
    # Cost Check
    cost = qty * supp.current_price
    
    # Setup PO
    arrival_day = state.current_day + supp.quoted_lead_time
    
    po = PurchaseOrder(
        id=f"PO-{state.current_day}-{random.randint(100,999)}",
        supplier_id=supp.id,
        day_placed=state.current_day,
        qty_ordered=qty,
        quoted_lead_time=supp.quoted_lead_time,
        expected_arrival_day=arrival_day,
        unit_price=supp.current_price,
        status=status
    )
    
    if status == "Open":
        # Commit Immediately
        # MOVED CASH DEDUCTION TO INVOICE PAYMENT
        # state.cash -= cost
        state.total_spend += cost
        
        inv = Invoice(
            id=f"INV-{po.id}",
            po_id=po.id,
            supplier_id=supp.id,
            amount=cost,
            due_day=arrival_day
        )
        state.invoices.append(inv)
        
        state.daily_events.append(f"📝 PO Placed: {qty} units from {supp.name} (Inv Due Day {arrival_day})")
    elif status == "Draft":
        # Do not deduct cash yet. Do not log public event.
        pass
        
    state.active_pos.append(po)
    return True, "Order Placed"

def pay_invoice(state: GameState, invoice_id: str):
    """Pay an open invoice. Adjust reputation based on timeliness."""
    inv = next((i for i in state.invoices if i.id == invoice_id), None)
    if not inv or inv.status == "Paid": return
    
    supp = next((s for s in state.available_suppliers if s.id == inv.supplier_id), None)
    if not supp: return
    
    # 1. Deduct Cash
    state.cash -= inv.amount
    inv.status = "Paid"
    
    # 2. Score Logic
    # Early: > 2 days before Due Date
    # Late: > Due Date
    if state.current_day <= inv.due_day - 2:
        supp.relationship_score += 5.0 # WAS 2.0
        state.daily_events.append(f"💰 PAID EARLY: {supp.name} is impressed! Score +5.")
    elif state.current_day > inv.due_day:
        # Penalty already applied daily, but maybe a final specific hit?
        supp.relationship_score -= 10.0 # WAS 5.0
        state.daily_events.append(f"💸 PAID LATE: {supp.name} is furious. Score -10.")
    else:
        # On time (Day of or 1 day before)
        supp.relationship_score += 1.0 # WAS 0.5
        # state.daily_events.append(f"💰 Paid {supp.name} on time.")

    # Clamp Score
    supp.relationship_score = max(0.0, min(100.0, supp.relationship_score))



def process_daily_turn(state: GameState):
    state.daily_events = []
    
    # 0. MARKET FLUCTUATIONS (Update Spot Prices)
    for s in state.available_suppliers:
        # Save previous
        s.previous_price = s.current_price
        
        # 0.a Reputation Check & Blocking Logic
        # Rules: Blocked if Score < 20 OR Any invoice > 5 days late
        has_serious_overdue = any(
            (i.supplier_id == s.id and i.status == "Unpaid" and (state.current_day - i.due_day > 5))
            for i in state.invoices
        )
        
        if s.relationship_score < 20.0:
            s.is_blocked = True
        elif has_serious_overdue:
            s.is_blocked = True
            # Log once?
            # state.daily_events.append(f"⛔ {s.name} HALTED SUPPLY: Unpaid invoices > 5 days late.")
        else:
            s.is_blocked = False
            
        # 0.b Reputation Price Modifier
        # Score 50 = 1.0x (Neutral)
        # Score 100 = 0.95x (Discount)
        # Score 0 = 1.10x (Premium)
        # Linear interp: Factor = 1.10 - (Score/100 * 0.15)? 
        # 0 -> 1.10. 100 -> 0.95.
        rep_factor = 1.10 - (s.relationship_score / 100.0) * 0.15
        
        # Volatility check
        base_price = s.quoted_price * rep_factor
        
        if s.true_price_volatility > 0:
            change = random.uniform(-s.true_price_volatility, s.true_price_volatility)
            s.current_price = base_price * (1.0 + change)
            
            # Big Spike Event
            if random.random() < 0.05: # 5% chance of surgy
                s.current_price *= 1.5
                state.daily_events.append(f"📈 PRICE SURGE: {s.name} spot price jump to ${s.current_price:.2f}")
        else:
            s.current_price = base_price
            
    # 0.c Invoice Aging (Penalty for unpaid overdue)
    for inv in state.invoices:
        if inv.status == "Unpaid" and state.current_day > inv.due_day:
            supp = next((s for s in state.available_suppliers if s.id == inv.supplier_id), None)
            if supp:
                supp.relationship_score -= 2.0 # WAS 1.0 - Accelerated decay
                # Log only periodically?
                if random.random() < 0.2:
                     state.daily_events.append(f"⚠️ OVERDUE: Invoice {inv.id} for {supp.name}. Relationship plummeting (-2).")
    
    # 1. RECEIVING LOGIC (Check for arrivals)
    # We iterate a copy to modify the list safely if we were removing (though we keep POs for history? No, move to delivery log)
    arrived_pos = []


    
    # 1. PREDICTIVE ALERTS (Day Before)
    for po in state.active_pos:
        if po.status != "Open": continue
        if state.current_day == po.expected_arrival_day - 1:
             is_late = random.random() > next((s.true_reliability for s in state.available_suppliers if s.id == po.supplier_id), 0.9)
             if is_late:
                 supp = next((s for s in state.available_suppliers if s.id == po.supplier_id), None)
                 if supp:
                     # Fix: Ensure max is at least 1 to avoid ValueError if variance is 0
                     var_days = max(1, supp.true_lead_time_var)
                     days_late = random.randint(1, var_days)
                     po.expected_arrival_day += days_late
                     state.daily_events.append(f"⚠️ NOTICE: PO {po.id} delayed by carrier. New Arrival: Day {po.expected_arrival_day}")

    # 2. PRODUCTION RUN (Consumption - Using Start-of-Day Stock)
    demand = state.production_schedule.get(state.current_day, 0)
    
    if state.inventory >= demand:
        state.inventory -= demand
    else:
        # STOCKOUT
        shortfall = demand - state.inventory
        penalty = shortfall * 20.0 
        state.total_stockout_penalty += penalty
        state.inventory = 0
        state.cash -= penalty
        state.daily_events.append(f"🛑 LINE STOPPAGE! Missing {shortfall} units. Penalty: ${penalty:,.0f}")

    # 2.B STORAGE COSTS
    # Apply cost to remaining inventory
    daily_storage = state.inventory * state.holding_cost_per_unit
    state.total_storage_cost += daily_storage
    state.cash -= daily_storage
    # Optional event log to remind them? Maybe only if it's high.
    # state.daily_events.append(f"Storage Cost: ${daily_storage:,.0f}")

    # 3. END-OF-DAY LOGISTICS (Arrivals & Stocking)
    
    # Step A: Upgrade "Processing" to "Received" (Stock becomes available)
    # This happens for goods that arrived YESTERDAY (Day X-1), so they are ready for Day X.
    for po in state.active_pos:
        if po.status == "Processing":
            # Add to Inventory
            supp = next((s for s in state.available_suppliers if s.id == po.supplier_id), None)
            if not supp:
                po.status = "Received"
                continue
            
            # Defects logic
            defect_rate = supp.true_defect_rate
            if random.random() < 0.2: defect_rate *= 2.0 
            qty_bad = int(po.qty_ordered * defect_rate)
            qty_good = po.qty_ordered - qty_bad
            
            rework = qty_bad * 50.0
            state.total_rework_cost += rework
            state.cash -= rework
            state.inventory += qty_good
            
            # KPI Log
            promised_day = po.day_placed + po.quoted_lead_time
            status_kpi = "On Time"
            if state.current_day > promised_day:
                 status_kpi = f"Late ({state.current_day - promised_day}d)"
            
            po.status = "Received"
            # We don't need to keep it in active_pos for UI if we don't want to.
            # User will see Inventory jump.
            # Maybe keep event?
            
            deliv = Delivery(
                id=f"DEL-{po.id}",
                day_arrived=state.current_day,
                supplier_name=supp.name,
                qty_received=qty_good,
                qty_defective=qty_bad,
                rework_cost=rework,
                status=status_kpi,
                unit_price=po.unit_price, # Use stored Price from PO
                day_placed=po.day_placed,
                quoted_lead_time=po.quoted_lead_time
            )
            state.delivery_log.append(deliv)
            
            msg = f"✅ STOCK AVAILABLE: {qty_good} units from {supp.name}."
            if qty_bad > 0: msg += f" ({qty_bad} Defective!)"
            state.daily_events.append(msg)
    
    # Step B: Check for NEW Arrivals (Open -> Processing)
    # We check if they arrive *Tomorrow*? No, we want them to appear as "Processing" on Tomorrow's screen.
    # So we check if current_day + 1 >= expected.
    for po in state.active_pos:
        if po.status == "Open":
            if state.current_day + 1 >= po.expected_arrival_day:
                po.status = "Processing"
                state.daily_events.append(f"🚛 ARRIVAL: PO {po.id} at dock. Processing (Available +24h).")

    # Clean up PO list (Remove completely processed ones)
    state.active_pos = [po for po in state.active_pos if po.status != "Received"]
        
    # 3. ADVANCE
    state.current_day += 1
    if state.current_day > state.max_days:
        state.game_over = True

# =============================================================================
# EXPORT
# =============================================================================
def get_csv_export(state: GameState) -> str:
    cols = ["Day_Placed", "Day_Arrived", "Supplier", "Qty_Total", "Qty_Good", "Qty_Defect", "Unit_Price", "Rework_Cost", "Status", "Lead_Time_Quoted", "Lead_Time_Actual"]
    data = []
    for d in state.delivery_log:
        total_qty = d.qty_received + d.qty_defective
        data.append({
            "Day_Placed": d.day_placed,
            "Day_Arrived": d.day_arrived,
            "Supplier": d.supplier_name,
            "Qty_Total": total_qty,
            "Qty_Good": d.qty_received,
            "Qty_Defect": d.qty_defective,
            "Unit_Price": d.unit_price,
            "Rework_Cost": d.rework_cost,
            "Status": d.status,
            "Lead_Time_Quoted": d.quoted_lead_time,
            "Lead_Time_Actual": d.day_arrived - d.day_placed
        })
    return pd.DataFrame(data, columns=cols).to_csv(index=False)

def get_supplier_stats(state: GameState, supplier_id: str) -> Dict:
    """Calculate real-time performance stats for a supplier"""
    supp = next((s for s in state.available_suppliers if s.id == supplier_id), None)
    if not supp: return {}
    
    # Filter deliveries
    deliveries = [d for d in state.delivery_log if d.supplier_name == supp.name]
    total_deliv = len(deliveries)
    
    if total_deliv == 0:
        return {
            "deliveries": 0,
            "defect_rate": 0.0,
            "reliability": 100.0, # Benefit of the doubt
            "total_rework": 0.0,
            "has_history": False
        }
        
    total_items = sum(d.qty_received + d.qty_defective for d in deliveries)
    total_defects = sum(d.qty_defective for d in deliveries)
    
    defect_rate = (total_defects / total_items * 100) if total_items > 0 else 0.0
    
    on_time = sum(1 for d in deliveries if d.status == "On Time")
    reliability = (on_time / total_deliv * 100)
    
    return {
        "deliveries": total_deliv,
        "defect_rate": defect_rate,
        "reliability": reliability,
        "total_rework": sum(d.rework_cost for d in deliveries),
        "has_history": True
    }

def generate_historical_simulation(num_orders=100) -> str:
    """Simulates a parallel game with random orders to generate a rich dataset for analysis."""
    # Create a dummy state
    sim_state = init_game()
    sim_state.max_days = 9999 
    
    # We want 100 *Completed Deliveries* for the CSV
    while len(sim_state.delivery_log) < num_orders:
        # Random Supplier
        supp = random.choice(sim_state.available_suppliers)
        
        # CHEAT: Reset reputation/blocking to ensure we can actually place orders
        # The goal is data generation (Lead Time/defects), not testing player skill.
        supp.is_blocked = False
        supp.relationship_score = 50.0 
        
        # CHEAT: Inject Price Variance so history looks real
        if supp.true_price_volatility > 0:
            # Fluctuate +/- 2x variance to make it visible
            vol = supp.true_price_volatility * 2.0 
            change = random.uniform(-vol, vol)
            supp.current_price = round(supp.quoted_price * (1.0 + change), 2)
        
        # Random Qty
        qty = random.choice([100, 200, 500, 1000])
        
        # Place Order
        success, msg = place_order(sim_state, supp.id, qty, status="Open")
        
        if success:
            # Advance 1-3 days randomly to spread them out
            days_skip = random.randint(1, 3)
            for _ in range(days_skip):
                process_daily_turn(sim_state)
                # Auto-pay invoices to prevent massive debt accumulation/re-blocking
                for inv in sim_state.invoices:
                    if inv.status == "Unpaid":
                         inv.status = "Paid" 
        else:
             # If failed (e.g. random constraint), just advance 1 day and try again
             process_daily_turn(sim_state)

        # Safety break
        if sim_state.current_day > 3000: break
            
    # Process remaining until all received or we have enough
    while len(sim_state.active_pos) > 0 and len(sim_state.delivery_log) < num_orders + 10:
        process_daily_turn(sim_state)
        if sim_state.current_day > 3500: break 
        
    return get_csv_export(sim_state)
