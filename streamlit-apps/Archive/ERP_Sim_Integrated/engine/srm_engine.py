# =============================================================================
# EIS Simulator — SRM Engine
# Supplier Relationship Management: RFQ, quotes, contracts, scorecards, invoicing
# =============================================================================
import random
from typing import Tuple, List, Dict, Optional
from Archive.ERP_Sim_Integrated.engine.state import SimState, Supplier, RFQ, SupplierInvoice, PurchaseOrder, ActivityLog
from Archive.ERP_Sim_Integrated.config import SUPPLIERS_CONFIG, SRM_PARAMS, FINANCIAL_PARAMS


# =============================================================================
# INITIALIZATION
# =============================================================================

def init_suppliers() -> Dict[str, Supplier]:
    suppliers = {}
    for sid, cfg in SUPPLIERS_CONFIG.items():
        base_prices = cfg["base_price"].copy()
        current_prices = {mid: p * random.uniform(0.98, 1.02) for mid, p in base_prices.items()}
        suppliers[sid] = Supplier(
            id=sid,
            name=cfg["name"],
            category=cfg["category"],
            materials=cfg["materials"],
            base_price=base_prices,
            current_price=current_prices,
            lead_time_days=cfg["lead_time_days"],
            quality_rate=cfg["quality_rate"],
            reliability=cfg["reliability"],
            min_order_qty=cfg["min_order_qty"],
            description=cfg["description"],
            country=cfg["country"],
            relationship_score=75.0,
        )
    return suppliers


# =============================================================================
# PRICE FLUCTUATION (daily market simulation)
# =============================================================================

def update_supplier_prices(state: SimState) -> None:
    """Simulate daily market price changes (+/- 3% per day)."""
    for sup in state.suppliers.values():
        for mid in sup.materials:
            base = sup.base_price.get(mid, 10.0)
            change_pct = random.uniform(-0.03, 0.04)  # Slight upward bias
            new_price = sup.current_price.get(mid, base) * (1 + change_pct)
            # Clamp to ±20% of base
            new_price = max(base * 0.80, min(base * 1.20, new_price))
            sup.current_price[mid] = round(new_price, 2)


# =============================================================================
# RFQ WORKFLOW
# =============================================================================

def send_rfq(state: SimState, material_id: str, qty: int) -> Tuple[bool, str, RFQ]:
    """Student sends an RFQ — all eligible suppliers respond immediately (SRM portal)."""
    if qty <= 0:
        return False, "Quantity must be > 0", None

    mat = state.materials.get(material_id)
    if not mat:
        return False, "Material not found", None

    rfq = RFQ(
        id=state.next_rfq_id(),
        day_sent=state.current_day,
        material_id=material_id,
        qty_requested=qty,
        status="QuotesReceived",
    )

    # All eligible (non-blocked) suppliers respond
    responded = 0
    for sup in state.suppliers.values():
        if material_id not in sup.materials:
            continue
        if sup.is_blocked:
            continue
        if qty < sup.min_order_qty:
            continue

        # Compute the price (contracted or market)
        if sup.contract_price and material_id in sup.contract_price:
            price = sup.contract_price[material_id]
            is_contracted = True
        else:
            price = sup.current_price.get(material_id, mat.cost)
            is_contracted = False

        # Lead time varies slightly based on current load
        lead_variance = random.randint(-1, 1)
        quoted_lead = max(1, sup.lead_time_days + lead_variance)

        # Supplier score for comparison (weighted: price lowest = best, quality/reliability highest = best)
        # Normalize price (lower = better score)
        weights = SRM_PARAMS["supplier_score_weights"]
        # We'll compute a composite score out of 100
        price_score = max(0, 100 - ((price / mat.cost) - 1) * 300)  # pricier → lower score
        quality_score = sup.quality_rate * 100
        delivery_score = sup.reliability * 100
        composite = (
            weights["price"] * price_score +
            weights["quality"] * quality_score +
            weights["delivery"] * delivery_score
        )

        rfq.responses.append({
            "supplier_id": sup.id,
            "supplier_name": sup.name,
            "price": round(price, 2),
            "total_cost": round(price * qty, 2),
            "lead_time": quoted_lead,
            "quality_rate": sup.quality_rate,
            "reliability": sup.reliability,
            "relationship_score": sup.relationship_score,
            "is_contracted": is_contracted,
            "composite_score": round(composite, 1),
        })
        responded += 1

    if responded == 0:
        return False, "No eligible suppliers for this material/quantity", None

    # Sort by composite score (best first)
    rfq.responses.sort(key=lambda x: x["composite_score"], reverse=True)
    state.rfqs.append(rfq)

    state.daily_events.append(
        f"📋 RFQ {rfq.id} sent for {qty}x {mat.name} — {responded} quotes received"
    )
    _log_srm(state, "RFQ_Sent", rfq.id, "Student",
             f"RFQ for {qty}x {mat.name}", kpi_tag="srm_rfq")
    return True, f"{responded} quotes received", rfq


def award_rfq(state: SimState, rfq_id: str, supplier_id: str) -> Tuple[bool, str]:
    """Student awards the RFQ to a supplier — creates PO automatically."""
    rfq = next((r for r in state.rfqs if r.id == rfq_id), None)
    if not rfq:
        return False, "RFQ not found"
    if rfq.status != "QuotesReceived":
        return False, f"RFQ already in status: {rfq.status}"

    response = next((r for r in rfq.responses if r["supplier_id"] == supplier_id), None)
    if not response:
        return False, "Supplier not in RFQ responses"

    sup = state.suppliers[supplier_id]
    mat = state.materials[rfq.material_id]
    price = response["price"]
    qty = rfq.qty_requested
    cost = price * qty

    if state.cash < cost:
        return False, f"Insufficient cash: need ${cost:,.0f}, have ${state.cash:,.0f}"

    # Create PO
    state.cash -= cost
    state.total_purchase_spend += cost
    sup.total_spend += cost

    arrival_day = state.current_day + response["lead_time"]
    po = PurchaseOrder(
        id=state.next_po_id(),
        supplier_id=supplier_id,
        material_id=rfq.material_id,
        qty=qty,
        unit_cost=price,
        day_placed=state.current_day,
        lead_time=response["lead_time"],
        expected_arrival_day=arrival_day,
        is_contracted=(response.get("is_contracted", False)),
        rfq_id=rfq_id,
        po_source="srm_rfq",
    )
    state.purchase_orders.append(po)

    rfq.status = "Awarded"
    rfq.awarded_supplier_id = supplier_id

    # Create Invoice immediately upon PO creation (with 2 day validity as requested)
    create_invoice_for_po(state, po, validity_days=2)

    state.daily_events.append(
        f"✅ PO {po.id} created via RFQ {rfq.id}: {qty}x {mat.name} from {sup.name} @ ${price:.2f} (Arrival: Day {arrival_day})"
    )
    _log_srm(state, "RFQ_Awarded", rfq.id, "Student",
             f"Awarded to {sup.name}: {qty}x {mat.name} @ ${price:.2f}",
             financial_impact=-cost, kpi_tag="srm_rfq")
    return True, po.id
def reject_rfq(state: SimState, rfq_id: str) -> Tuple[bool, str]:
    """Student rejects the RFQ responses."""
    rfq = next((r for r in state.rfqs if r.id == rfq_id), None)
    if not rfq:
        return False, "RFQ not found"
    if rfq.status != "QuotesReceived":
        return False, f"RFQ already in status: {rfq.status}"
    
    rfq.status = "Rejected"
    state.daily_events.append(f"❌ RFQ {rfq.id} quotes rejected by user.")
    return True, "RFQ quotes rejected"

def purchase_from_market(state: SimState, supplier_id: str, material_id: str, qty: int) -> Tuple[bool, str]:
    """Direct purchase from SRM daily market (no RFQ needed)."""
    sup = state.suppliers.get(supplier_id)
    if not sup: return False, "Supplier not found"
    
    mat = state.materials.get(material_id)
    if not mat: return False, "Material not found"
    
    price = sup.contract_price.get(material_id) if sup.contract_price and material_id in sup.contract_price else sup.current_price.get(material_id, mat.cost)
    cost = price * qty
    
    if state.cash < cost:
        return False, f"Insufficient cash: need ${cost:,.0f}"
    
    # Create PO
    state.cash -= cost
    state.total_purchase_spend += cost
    sup.total_spend += cost
    
    arrival_day = state.current_day + sup.lead_time_days
    po = PurchaseOrder(
        id=state.next_po_id(),
        supplier_id=supplier_id,
        material_id=material_id,
        qty=qty,
        unit_cost=price,
        day_placed=state.current_day,
        lead_time=sup.lead_time_days,
        expected_arrival_day=arrival_day,
        is_contracted=bool(sup.contract_price and material_id in sup.contract_price),
        po_source="market_direct",
    )
    state.purchase_orders.append(po)
    
    # Create Invoice
    create_invoice_for_po(state, po, validity_days=2)
    
    state.daily_events.append(f"🛒 Direct Purchase: {qty}x {mat.name} from {sup.name} @ ${price:.2f}")
    _log_srm(state, "Market_Purchase", po.id, "Student", f"Direct purchase: {qty}x {mat.name} from {sup.name}")
    return True, po.id


# =============================================================================
# CONTRACT MANAGEMENT
# =============================================================================

def create_contract(state: SimState, supplier_id: str, material_id: str,
                    negotiated_price: float, volume_commitment: int) -> Tuple[bool, str]:
    """Lock in a preferred supplier price. Appears in RFQ responses as contracted."""
    sup = state.suppliers.get(supplier_id)
    if not sup:
        return False, "Supplier not found"
    if material_id not in sup.materials:
        return False, f"{sup.name} does not supply {material_id}"

    mat = state.materials[material_id]
    market_price = sup.current_price.get(material_id, mat.cost)
    if negotiated_price >= market_price:
        # Still allow but warn
        pass

    if sup.contract_price is None:
        sup.contract_price = {}
    sup.contract_price[material_id] = negotiated_price

    state.daily_events.append(
        f"📝 CONTRACT: {sup.name} locked at ${negotiated_price:.2f}/{mat.unit} for {mat.name} "
        f"(Market: ${market_price:.2f}, Volume: {volume_commitment} units)"
    )
    _log_srm(state, "Contract_Created", supplier_id, "Student",
             f"Contract: {mat.name} at ${negotiated_price:.2f} (market was ${market_price:.2f})",
             kpi_tag="srm_contract")
    return True, "Contract established"


# =============================================================================
# INVOICE & AP MANAGEMENT
# =============================================================================

def create_invoice_for_po(state: SimState, po: PurchaseOrder, validity_days: int = None) -> None:
    """Create AP invoice (now done at PO creation with specific validity)."""
    sup = state.suppliers.get(po.supplier_id)
    amount = po.qty * po.unit_cost
    
    if validity_days is None:
        validity_days = FINANCIAL_PARAMS["ap_payment_days"]
        
    due_day = state.current_day + validity_days

    # Early payment discount (pay within 10 days → 2% off)
    early_discount = amount * 0.02

    inv = SupplierInvoice(
        id=state.next_inv_id(),
        supplier_id=po.supplier_id,
        po_id=po.id,
        amount=amount,
        day_issued=state.current_day,
        due_day=due_day,
        early_payment_discount=early_discount,
    )
    state.supplier_invoices.append(inv)
    po.invoice_id = inv.id

    state.daily_events.append(
        f"🧾 Invoice {inv.id}: ${amount:,.0f} from {sup.name if sup else 'Supplier'} "
        f"(Due Day {due_day}, Early discount: ${early_discount:.0f})"
    )


def pay_invoice(state: SimState, invoice_id: str, early: bool = False) -> Tuple[bool, str]:
    """Student pays a supplier invoice. Early payment → relationship bonus."""
    inv = next((i for i in state.supplier_invoices if i.id == invoice_id), None)
    if not inv:
        return False, "Invoice not found"
    if inv.status != "Unpaid":
        return False, f"Invoice status: {inv.status}"

    amount = inv.amount
    if early and state.current_day <= inv.day_issued + 10:
        amount -= inv.early_payment_discount
        bonus = 5
    else:
        bonus = 2

    if state.cash < amount:
        return False, f"Insufficient cash: need ${amount:,.0f}, have ${state.cash:,.0f}"

    state.cash -= amount
    inv.status = "Paid"
    inv.paid_day = state.current_day

    # Relationship score boost
    sup = state.suppliers.get(inv.supplier_id)
    if sup:
        sup.relationship_score = min(100, sup.relationship_score + bonus)

    state.daily_events.append(
        f"💸 Paid Invoice {inv.id}: ${amount:,.0f} to {sup.name if sup else 'Supplier'}"
        + (f" (Early payment discount applied: -${inv.early_payment_discount:.0f})" if early else "")
    )
    _log_srm(state, "Invoice_Paid", inv.id, "Student",
             f"Paid ${amount:,.0f} to {sup.name if sup else 'Supplier'}",
             financial_impact=-amount, kpi_tag="srm_ap")
    return True, "Invoice paid"


def check_invoice_overdue(state: SimState) -> None:
    """Auto-flag overdue invoices and penalize supplier relationship."""
    for inv in state.supplier_invoices:
        if inv.status == "Unpaid" and state.current_day > inv.due_day:
            inv.status = "Overdue"
            sup = state.suppliers.get(inv.supplier_id)
            if sup:
                sup.relationship_score = max(0, sup.relationship_score - 10)
                if sup.relationship_score < 20:
                    sup.is_blocked = True
                    state.daily_events.append(
                        f"🚫 {sup.name} BLOCKED: repeated late payments! Score: {sup.relationship_score:.0f}/100"
                    )
                else:
                    state.daily_events.append(
                        f"⚠️ Invoice {inv.id} OVERDUE! ${inv.amount:,.0f} to {sup.name}. "
                        f"Relationship: {sup.relationship_score:.0f}/100"
                    )


# =============================================================================
# SUPPLIER SCORECARD
# =============================================================================

def get_supplier_scorecard(state: SimState, supplier_id: str) -> dict:
    sup = state.suppliers.get(supplier_id)
    if not sup:
        return {}

    supplier_pos = [po for po in state.purchase_orders
                    if po.supplier_id == supplier_id and po.status == "Received"]
    deliveries = len(supplier_pos)
    on_time = sum(1 for po in supplier_pos
                  if po.actual_arrival_day and po.actual_arrival_day <= po.expected_arrival_day)
    total_spend = sum(po.qty_received * po.unit_cost for po in supplier_pos)
    defect_ppm = int((sup.defects_total / max(1, sup.units_received_total)) * 1_000_000)
    savings_vs_market = sum(
        (sup.base_price.get(po.material_id, po.unit_cost) - po.unit_cost) * po.qty
        for po in supplier_pos
    )

    return {
        "deliveries": deliveries,
        "on_time": on_time,
        "on_time_rate": round((on_time / max(1, deliveries)) * 100, 1),
        "total_spend": round(total_spend, 2),
        "defect_ppm": defect_ppm,
        "relationship_score": round(sup.relationship_score, 1),
        "is_blocked": sup.is_blocked,
        "savings_vs_market": round(savings_vs_market, 2),
        "is_contracted": bool(sup.contract_price),
    }


def get_srm_kpis(state: SimState) -> dict:
    all_pos = [po for po in state.purchase_orders if po.status == "Received"]
    rfqs_sent = len(state.rfqs)
    rfqs_awarded = len([r for r in state.rfqs if r.status == "Awarded"])
    active_contracts = sum(1 for s in state.suppliers.values() if s.contract_price)
    total_spend = sum(po.qty_received * po.unit_cost for po in all_pos)
    total_invoices = len(state.supplier_invoices)
    paid_on_time = len([i for i in state.supplier_invoices
                        if i.status == "Paid" and i.paid_day and i.paid_day <= i.due_day])
    return {
        "RFQs Sent": rfqs_sent,
        "RFQs Awarded": rfqs_awarded,
        "Active Contracts": active_contracts,
        "Total Procurement Spend": f"${total_spend:,.0f}",
        "Invoices Paid On-Time %": f"{(paid_on_time / max(1, total_invoices)) * 100:.1f}%",
        "Total Rework Cost (Supplier Quality)": f"${state.total_rework_cost:,.0f}",
    }


# =============================================================================
# HELPERS
# =============================================================================

def _log_srm(state: SimState, event_type: str, ref_id: str, actor: str,
             desc: str, financial_impact: float = 0, kpi_tag: str = ""):
    state.activity_log.append(ActivityLog(
        day=state.current_day,
        timestamp_sim=f"Day {state.current_day}",
        module="SRM",
        event_type=event_type,
        ref_id=ref_id,
        actor=actor,
        description=desc,
        financial_impact=financial_impact,
        kpi_tag=kpi_tag,
    ))
