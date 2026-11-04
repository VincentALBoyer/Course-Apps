# =============================================================================
# EIS Simulator — ERP Core Engine
# Handles: initialization, production, purchasing, sales, daily batch
# =============================================================================
import random
import math
from typing import Tuple, List, Optional
from Archive.ERP_Sim_Integrated.engine.state import (
    SimState, Material, Product, SalesOrder, WorkOrder, PurchaseOrder,
    FinancialEntry, InventoryMovement, ActivityLog, EmailMessage, Supplier,
    CommunicationEntry, PendingRFQ, RFQ
)
from Archive.ERP_Sim_Integrated.config import (
    MATERIALS_CONFIG, PRODUCTS_CONFIG, SUPPLIERS_CONFIG, CUSTOMERS_CONFIG,
    SIMULATION_DAYS, STARTING_CASH, DAILY_CAPACITY_HOURS,
    DEMAND_PARAMS, PRODUCTION_PARAMS, FINANCIAL_PARAMS, SRM_PARAMS
)


# =============================================================================
# INITIALIZATION
# =============================================================================

def init_simulation() -> SimState:
    """Bootstrap the simulation with all master data and starting inventory."""
    state = SimState(
        current_day=1,
        max_days=SIMULATION_DAYS,
        cash=STARTING_CASH,
    )

    # Materials
    for mid, cfg in MATERIALS_CONFIG.items():
        state.materials[mid] = Material(
            id=mid, name=cfg["name"], cost=cfg["cost"],
            unit=cfg["unit"], reorder_point=cfg["reorder_point"],
            category=cfg["category"]
        )

    # Products
    for pid, cfg in PRODUCTS_CONFIG.items():
        state.products[pid] = Product(
            id=pid, name=cfg["name"], price=cfg["price"],
            bom=cfg["bom"], production_hours=cfg["production_hours"],
            category=cfg["category"], description=cfg["description"]
        )

    # Suppliers
    from Archive.ERP_Sim_Integrated.engine.srm_engine import init_suppliers
    state.suppliers = init_suppliers()

    # Starting inventory — moderate level to start
    state.stock_materials = {
        "M01": 30, "M02": 30, "M03": 15,
        "M04": 20, "M05": 10, "M06": 15,
    }
    state.stock_finished = {"P01": 5, "P02": 3, "P03": 1}

    # Record initial inventory as GR movements
    for mid, qty in state.stock_materials.items():
        _add_inv_movement(state, material_id=mid, product_id=None,
                          mvt_type="Opening_Stock", qty=qty,
                          ref_id="INIT", desc=f"Opening stock: {state.materials[mid].name}")

    # Generate first daily demand and market intro
    _generate_daily_demand(state)
    _generate_initial_comms(state)

    _log_activity(state, "System", "Simulation_Start", "INIT", "System",
                  f"VéloForge Industries — Day 1 simulation started. Cash: ${state.cash:,.0f}")
    return state


# =============================================================================
# DAILY BATCH PROCESSING
# =============================================================================

def advance_day(state: SimState) -> None:
    """Main simulation loop for end-of-day processing."""
    if state.game_over:
        return
    state.daily_events.clear()

    # 1. Apply daily overhead
    _apply_overhead(state)

    # 2. Receive inbound deliveries (purchase orders arriving)
    _receive_purchase_orders(state)

    # 3. Advance production (capacity-constrained FIFO)
    _run_production(state)

    # 4. Apply storage costs for finished goods & raw materials
    _apply_storage_costs(state)

    # 5. Check for overdue sales orders → apply late penalty or cancel
    _process_overdue_orders(state)

    # 6. Auto-pay SRM invoices if overdue AND SRM is enabled
    if state.srm_enabled:
        from Archive.ERP_Sim_Integrated.engine.srm_engine import check_invoice_overdue
        check_invoice_overdue(state)

    # 8. CRM daily pipeline advance
    if state.crm_enabled:
        from Archive.ERP_Sim_Integrated.engine.crm_engine import advance_crm_pipeline, generate_new_leads
        advance_crm_pipeline(state)
        generate_new_leads(state)

    # 9. Process pending manual RFQs (delayed replies arrive today)
    _process_pending_rfqs(state)

    # 10. Generate new daily demand
    _generate_daily_demand(state)

    # 11. MRP alerts — low stock warnings
    _run_mrp_alerts(state)

    # 12. Daily snapshot for charts
    _save_daily_snapshot(state)

    # 11. Advance day
    if state.current_day < state.max_days:
        state.current_day += 1
    else:
        # We are at or past the limit (should be handled by game_over guard but stay safe)
        state.game_over = True
    if state.current_day > state.max_days:
        state.game_over = True
        state.daily_events.append("🏁 Simulation complete. Download your activity log from Reports.")
        _log_activity(state, "System", "Simulation_End", "FINAL", "System",
                      f"Simulation ended. Final cash: ${state.cash:,.0f}")


def _apply_overhead(state: SimState) -> None:
    overhead = FINANCIAL_PARAMS["daily_overhead"]
    state.cash -= overhead
    state.total_overhead += overhead
    _add_ledger(state, "OpEx", f"OVH-{state.current_day}", f"Daily overhead (Day {state.current_day})",
                debit=overhead, credit=0)
    state.daily_events.append(f"💼 Daily overhead: -${overhead:,.0f}")


def _receive_purchase_orders(state: SimState) -> None:
    received_pos = []
    for po in state.purchase_orders:
        if po.status == "OnOrder" and state.current_day >= po.expected_arrival_day:
            # Simulate supplier reliability — may arrive late or have defects
            supplier = state.suppliers.get(po.supplier_id)

            # On-time delivery check (already handled by expected_arrival_day, but quality pass)
            defect_rate = 1 - (supplier.quality_rate if supplier else 0.97)
            defective = int(po.qty * defect_rate * random.uniform(0.5, 1.5))
            defective = min(defective, po.qty)
            good_qty = po.qty - defective

            po.status = "Received"
            po.actual_arrival_day = state.current_day
            po.qty_received = good_qty

            # Add to stock
            state.stock_materials[po.material_id] = state.stock_materials.get(po.material_id, 0) + good_qty
            _add_inv_movement(state, material_id=po.material_id, product_id=None,
                              mvt_type="GR", qty=good_qty, ref_id=po.id,
                              desc=f"Goods receipt from {supplier.name if supplier else 'Supplier'}")

            # Update supplier stats
            if supplier:
                supplier.deliveries_total += 1
                supplier.deliveries_on_time += 1
                supplier.defects_total += defective
                supplier.units_received_total += po.qty
                if defective > 0:
                    rework = defective * PRODUCTION_PARAMS["rework_cost_per_unit"]
                    state.total_rework_cost += rework
                    state.cash -= rework
                    _add_ledger(state, "OpEx", po.id, f"Rework cost: {defective} defective units from {supplier.name}",
                                debit=rework)
                    state.daily_events.append(
                        f"⚠️ {supplier.name}: {defective} defective units! Rework cost: -${rework:.0f}")

            received_pos.append(po)
            state.daily_events.append(
                f"🚛 Received PO {po.id}: {good_qty}x {state.materials[po.material_id].name} from "
                f"{supplier.name if supplier else 'Supplier'}"
            )
            _log_activity(state, "ERP", "PO_Received", po.id, "System",
                          f"Received {good_qty} units of {state.materials[po.material_id].name}",
                          financial_impact=0, kpi_tag="procurement_OTIF")

            # Create invoice if SRM enabled (3-way match)
            if state.srm_enabled:
                pass


def _run_production(state: SimState) -> None:
    available_hours = DAILY_CAPACITY_HOURS
    active_wos = [wo for wo in state.work_orders if wo.status == "InProgress"]

    for wo in active_wos:
        if available_hours <= 0:
            break
        remaining = wo.hours_required - wo.hours_completed
        work = min(available_hours, remaining)
        wo.hours_completed += work
        available_hours -= work

        if wo.hours_completed >= wo.hours_required:
            wo.status = "Completed"
            wo.completion_day = state.current_day

            # Quality check
            quality_pass = random.random() < PRODUCTION_PARAMS["quality_pass_rate"]
            prod = state.products[wo.product_id]

            if quality_pass:
                state.stock_finished[wo.product_id] = state.stock_finished.get(wo.product_id, 0) + wo.qty
                _add_inv_movement(state, material_id=None, product_id=wo.product_id,
                                  mvt_type="Production_Receipt", qty=wo.qty, ref_id=wo.id,
                                  desc=f"Production completed: {prod.name}")
                state.daily_events.append(f"✅ Production complete: {wo.qty}x {prod.name} → Finished Goods")
            else:
                # Rework scenario
                rework_qty = max(1, int(wo.qty * 0.15))
                good_qty = wo.qty - rework_qty
                rework_cost = rework_qty * PRODUCTION_PARAMS["rework_cost_per_unit"]
                wo.rework_cost = rework_cost
                state.total_rework_cost += rework_cost
                state.cash -= rework_cost
                state.stock_finished[wo.product_id] = state.stock_finished.get(wo.product_id, 0) + good_qty
                _add_ledger(state, "OpEx", wo.id, f"Production rework: {rework_qty} units", debit=rework_cost)
                state.daily_events.append(
                    f"⚠️ QC Issue: {rework_qty} units of {prod.name} reworked. Cost: -${rework_cost:.0f}")

            _log_activity(state, "ERP", "Production_Completed", wo.id, "System",
                          f"Completed {wo.qty}x {prod.name}", kpi_tag="production_OEE")


def _apply_storage_costs(state: SimState) -> None:
    cost_per_unit = FINANCIAL_PARAMS["storage_cost_per_unit_day"]
    total_units = sum(state.stock_finished.values()) + sum(state.stock_materials.values()) // 5
    if total_units > 0:
        storage_cost = total_units * cost_per_unit
        state.cash -= storage_cost
        state.total_storage_cost += storage_cost
        _add_ledger(state, "OpEx", f"STO-{state.current_day}",
                    f"Storage cost ({total_units} units)", debit=storage_cost)


def _process_overdue_orders(state: SimState) -> None:
    overdue = [so for so in state.sales_orders
               if so.status == "Open" and state.current_day > so.due_day + 2]
    for so in overdue:
        if not so.late_penalty_applied:
            penalty = so.qty * DEMAND_PARAMS["stockout_penalty_per_unit"]
            state.cash -= penalty
            state.total_penalties += penalty
            so.late_penalty_applied = True
            so.status = "Cancelled"
            _add_ledger(state, "Penalty", so.id, f"Lost sale penalty: {so.customer_name}", debit=penalty)
            state.daily_events.append(
                f"❌ Lost sale: {so.customer_name} cancelled Order {so.id}. Penalty: -${penalty:.0f}")
            _log_activity(state, "ERP", "Order_Lost", so.id, "System",
                          f"Lost sale to {so.customer_name}", financial_impact=-penalty, kpi_tag="sales_OTIF")


def _generate_daily_demand(state: SimState) -> None:
    """Generate new sales orders each day."""
    num_orders = random.randint(
        DEMAND_PARAMS["daily_orders_min"],
        DEMAND_PARAMS["daily_orders_max"]
    )

    from Archive.ERP_Sim_Integrated.config import CUSTOMERS_CONFIG
    customer_names = [c["name"] for c in CUSTOMERS_CONFIG]

    # CRM mode: use actual customer records
    if state.crm_enabled and state.customers:
        cust_list = list(state.customers.values())
    else:
        cust_list = None

    for _ in range(num_orders):
        prod_id = random.choice(list(state.products.keys()))
        prod = state.products[prod_id]
        qty = random.randint(1, 6)
        is_rush = random.random() < DEMAND_PARAMS["rush_order_probability"]
        due_offset = 2 if is_rush else random.randint(4, 8)

        if cust_list:
            cust = random.choice(cust_list)
            cname = cust.name
            cid = cust.id
        else:
            cname = random.choice(customer_names)
            cid = None

        due_day = state.current_day + due_offset

        if state.crm_enabled:
            # CRM: Automatic conversion to Sales Order
            so_id = state.next_so_id()
            so = SalesOrder(
                id=so_id, customer_name=cname, customer_id=cid, product_id=prod_id, qty=qty,
                unit_price=prod.price, 
                day_placed=state.current_day, due_day=due_day,
                status="Open", source="CRM_Pipeline"
            )
            state.sales_orders.append(so)
            state.daily_events.append(f"📈 CRM Lead converted: {cname} — {qty}x {prod.name}")
        else:
            # Manual Mode: Just a communication entry. Student must accept it.
            comm = CommunicationEntry(
                id=state.next_email_id(),
                day=state.current_day,
                module="Sales",
                entity_id="C01", # generic
                entity_name=cname,
                direction="Inbound",
                subject=f"Order Inquiry — {qty}x {prod.name}",
                body=(
                    f"Hello Sales,\n\nWe are interested in purchasing {qty} units of {prod.name}. "
                    f"Can you deliver by Day {due_day}? Please confirm to process the order.\n\nBest, {cname}"
                ),
                action_type="customer_order",
                action_data={
                    "customer_name": cname,
                    "customer_id": cid,
                    "product_id": prod_id,
                    "qty": qty,
                    "due_day": due_day,
                    "price": prod.price
                },
            )
            state.communication_log.append(comm)
            state.daily_events.append(f"📧 New Order Inquiry from {cname} for {prod.name}")


def process_customer_order_manual(state: SimState, comm_id: str) -> Tuple[bool, str]:
    """Student accepts a customer inquiry from the log and converts it to a Sales Order."""
    comm = next((c for c in state.communication_log if c.id == comm_id), None)
    if not comm or comm.action_type != "customer_order":
        return False, "Order inquiry not found or already processed."
    
    data = comm.action_data
    so_id = state.next_so_id()
    so = SalesOrder(
        id=so_id,
        customer_name=data["customer_name"],
        customer_id=data.get("customer_id"),
        product_id=data["product_id"],
        qty=data["qty"],
        unit_price=data["price"], # Use price from action_data
        day_placed=state.current_day,
        due_day=data["due_day"],
        status="Open",
        source="Manual_Accept"
    )
    state.sales_orders.append(so)
    
    # Mark communication as processed
    comm.status = "Accepted"
    comm.is_read = True # Mark as read
    comm.subject = f"[PROCESSED] {comm.subject}"
    
    _log_activity(state, "ERP", "Sales_Order_Manual", so_id, "Student", f"Accepted manual order from {data['customer_name']}")
    state.daily_events.append(f"✅ Accepted order inquiry {comm_id} for {data['qty']}x {state.products[data['product_id']].name} (SO {so_id})")
    return True, so_id


def _generate_initial_comms(state: SimState) -> None:
    """Initial communication for day 1 (manual mode)."""
    for sid, sup in state.suppliers.items():
        comm = CommunicationEntry(
            id=state.next_email_id(),
            day=state.current_day,
            module="Procurement",
            entity_id=sid,
            entity_name=sup.name,
            direction="Inbound",
            subject=f"Standard Terms & Pricing: {sup.name}",
            body=f"Welcome to Day 1. We supply {', '.join([state.materials[m].name for m in sup.materials])}. Please request a quote by email for any specific quantities.",
            action_type="general",
            is_read=True
        )
        state.communication_log.append(comm)


def _process_pending_rfqs(state: SimState) -> None:
    """Manual mode logic: process RFQs sent yesterday so they appear as replies today."""
    remaining = []
    for pr in state.pending_rfqs:
        pr.days_to_reply -= 1
        if pr.days_to_reply <= 0:
            # Reply arrives today!
            mat = state.materials.get(pr.material_id)
            # Find eligible suppliers
            best_sup = None
            for sid, sup in state.suppliers.items():
                if pr.material_id in sup.materials and not sup.is_blocked:
                    # In manual mode, we just get ONE reply (the best one normally) or multiple?
                    # Let's give them a single focused reply for simplicity in the log.
                    price = sup.current_price.get(pr.material_id, mat.cost)
                    comm = CommunicationEntry(
                        id=state.next_email_id(),
                        day=state.current_day,
                        module="Procurement",
                        entity_id=sid,
                        entity_name=sup.name,
                        direction="Inbound",
                        subject=f"RE: Quote Request — {pr.qty}x {mat.name}",
                        body=(
                            f"Hello VéloForge team,\n\nFurther to your request, we can provide {pr.qty} units of {mat.name} "
                            f"at a price of ${price:.2f} each. Estimated lead time is {sup.lead_time_days} days.\n\n"
                            f"Please click 'Accept' to convert this to a Purchase Order."
                        ),
                        action_type="rfq_quote",
                        action_data={
                            "supplier_id": sid,
                            "material_id": pr.material_id,
                            "qty": pr.qty,
                            "price": price,
                            "lead_time": sup.lead_time_days
                        },
                    )
                    state.communication_log.append(comm)
                    state.daily_events.append(f"📧 New Quote received from {sup.name} for {mat.name}")
            
            # If no replies were generated, notify the user
            replies_found = any(c.subject.startswith(f"RE: Quote Request — {pr.qty}x {mat.name}") 
                               for c in state.communication_log if c.day == state.current_day)
            if not replies_found:
                comm = CommunicationEntry(
                    id=state.next_email_id(),
                    day=state.current_day,
                    module="Procurement",
                    entity_id="SYSTEM",
                    entity_name="Procurement System",
                    direction="Inbound",
                    subject=f"⚠️ No Suppliers Found: {mat.name}",
                    body=f"We contacted all known suppliers for {pr.qty}x {mat.name}, but none are currently able to fulfill this request.",
                    action_type="general",
                    status="Discarded"
                )
                state.communication_log.append(comm)
                state.daily_events.append(f"⚠️ No suppliers found to quote {mat.name}")
        else:
            remaining.append(pr)
    state.pending_rfqs = remaining


def request_quote_manual(state: SimState, material_id: str, qty: int) -> Tuple[bool, str]:
    """Student requests a quote in manual mode. Reply arrives next day."""
    if state.srm_enabled:
        return False, "SRM is active. Use the Daily Market for instant ordering."
    
    mat = state.materials.get(material_id)
    if not mat: return False, "Material not found"
    
    rfq_id = state.next_rfq_id()
    pending = PendingRFQ(id=rfq_id, day_sent=state.current_day, material_id=material_id, qty=qty)
    state.pending_rfqs.append(pending)
    
    # Add outbound log
    comm = CommunicationEntry(
        id=state.next_email_id(),
        day=state.current_day,
        module="Procurement",
        entity_id="ALL",
        entity_name="Global Suppliers",
        direction="Outbound",
        subject=f"Quote Request: {qty}x {mat.name}",
        body=f"To all suppliers: Please provide your best quote for {qty} units of {mat.name}.",
        is_read=True
    )
    state.communication_log.append(comm)
    _log_activity(state, "ERP", "RFQ_Sent_Manual", rfq_id, "Student", f"Requested quote for {qty}x {mat.name}")
    return True, f"Request sent. Check the Communication Log Day {state.current_day + 1} for replies."


def _run_mrp_alerts(state: SimState) -> None:
    """Check reorder points and generate alerts."""
    for mid, mat in state.materials.items():
        qty = state.stock_materials.get(mid, 0)
        if qty <= mat.reorder_point:
            state.daily_events.append(
                f"⚠️ LOW STOCK: {mat.name} = {qty} units (Reorder point: {mat.reorder_point})"
            )


def _save_daily_snapshot(state: SimState) -> None:
    cash_out = state.total_overhead + state.total_purchase_spend + state.total_penalties + state.total_rework_cost
    state.daily_snapshots.append({
        "day": state.current_day,
        "cash": round(state.cash, 2),
        "revenue": round(state.total_revenue, 2),
        "costs": round(cash_out, 2),
        "profit": round(state.total_revenue - cash_out, 2),
        "open_orders": len([so for so in state.sales_orders if so.status == "Open"]),
        "stock_raw": sum(state.stock_materials.values()),
        "stock_fg": sum(state.stock_finished.values()),
        "wip": len([wo for wo in state.work_orders if wo.status == "InProgress"]),
    })


# =============================================================================
# ACTION: SHIP SALES ORDER
# =============================================================================

def ship_sales_order(state: SimState, so_id: str) -> Tuple[bool, str]:
    so = next((o for o in state.sales_orders if o.id == so_id), None)
    if not so:
        return False, "Order not found"
    if so.status != "Open":
        return False, f"Order status is '{so.status}', not Open"

    available = state.stock_finished.get(so.product_id, 0)
    if available < so.qty:
        return False, f"Insufficient stock: need {so.qty}, have {available}"

    # Ship
    state.stock_finished[so.product_id] -= so.qty
    so.status = "Shipped"
    so.shipped_day = state.current_day

    # Late delivery discount
    revenue = so.qty * so.unit_price
    if state.current_day > so.due_day:
        discount = revenue * FINANCIAL_PARAMS.get("late_shipment_penalty_pct", 0.05)
        revenue -= discount
        state.daily_events.append(f"⚠️ Late shipment penalty: -${discount:.0f} (Order {so.id})")

    state.cash += revenue
    state.total_revenue += revenue

    # COGS
    prod = state.products[so.product_id]
    cogs = sum(state.materials[m].cost * q for m, q in prod.bom.items()) * so.qty
    state.total_cogs += cogs

    _add_ledger(state, "Revenue", so.id, f"Sale to {so.customer_name}: {so.qty}x {prod.name}",
                credit=revenue)
    _add_ledger(state, "COGS", so.id, f"COGS for {so.id}", debit=cogs)
    _add_inv_movement(state, material_id=None, product_id=so.product_id,
                      mvt_type="Sales_Issue", qty=so.qty, ref_id=so.id,
                      desc=f"Shipped to {so.customer_name}")

    # Update customer stats if CRM
    if state.crm_enabled and so.customer_id and so.customer_id in state.customers:
        cust = state.customers[so.customer_id]
        cust.total_orders += 1
        cust.total_revenue += revenue

    state.daily_events.append(f"🚚 Shipped {so.id}: {so.qty}x {prod.name} to {so.customer_name} → +${revenue:,.0f}")
    _log_activity(state, "ERP", "Order_Shipped", so.id, "Student",
                  f"Shipped {so.qty}x {prod.name} to {so.customer_name}",
                  financial_impact=revenue, kpi_tag="sales_revenue")
    return True, "Order shipped successfully"


# =============================================================================
# ACTION: CREATE WORK ORDER (START PRODUCTION)
# =============================================================================

def create_work_order(state: SimState, product_id: str, qty: int) -> Tuple[bool, str]:
    if qty <= 0:
        return False, "Quantity must be > 0"

    prod = state.products.get(product_id)
    if not prod:
        return False, "Product not found"

    # Validate BOM
    shortage = []
    for mat_id, needed_per_unit in prod.bom.items():
        total_needed = needed_per_unit * qty
        avail = state.stock_materials.get(mat_id, 0)
        if avail < total_needed:
            mat = state.materials[mat_id]
            shortage.append(f"{mat.name}: need {total_needed}, have {avail}")

    if shortage:
        return False, "Material shortage: " + "; ".join(shortage)

    # Consume materials (Goods Issue)
    for mat_id, needed_per_unit in prod.bom.items():
        total_needed = needed_per_unit * qty
        state.stock_materials[mat_id] -= total_needed
        mat = state.materials[mat_id]
        _add_inv_movement(state, material_id=mat_id, product_id=None,
                          mvt_type="GI_Production", qty=total_needed, ref_id="",
                          desc=f"Consumed for {prod.name} production")
        cost = total_needed * mat.cost
        _add_ledger(state, "COGS", "", f"Material consumed: {mat.name}×{total_needed}", debit=cost)

    total_hours = prod.production_hours * qty
    wo = WorkOrder(
        id=state.next_wo_id(),
        product_id=product_id,
        qty=qty,
        day_started=state.current_day,
        hours_required=total_hours,
    )
    state.work_orders.append(wo)
    state.daily_events.append(
        f"🔧 Work Order {wo.id}: {qty}x {prod.name} started ({total_hours} hrs required)"
    )
    _log_activity(state, "ERP", "WorkOrder_Created", wo.id, "Student",
                  f"Started production of {qty}x {prod.name}", kpi_tag="production_schedule")
    return True, wo.id


# =============================================================================
# ACTION: MANUAL PURCHASE ORDER (ERP-only mode)
# =============================================================================

def create_manual_po(state: SimState, supplier_id: str, material_id: str,
                     qty: int, quoted_price: float, quoted_lead_time: int) -> Tuple[bool, str]:
    """Place a manual PO (student typed in price/lead time from email)."""
    if qty <= 0:
        return False, "Quantity must be > 0"

    supplier = state.suppliers.get(supplier_id)
    if not supplier:
        return False, "Supplier not found"

    if supplier.is_blocked:
        return False, f"{supplier.name} is blocked due to payment issues"

    if qty < supplier.min_order_qty:
        return False, f"Minimum order: {supplier.min_order_qty} units"

    cost = quoted_price * qty
    # Check cash
    if state.cash < cost:
        return False, f"Insufficient cash: need ${cost:,.0f}, have ${state.cash:,.0f}"

    # Deduct on placement (simplified — AP would be better, but simpler for class)
    state.cash -= cost
    state.total_purchase_spend += cost
    supplier.total_spend += cost

    arrival_day = state.current_day + quoted_lead_time

    po = PurchaseOrder(
        id=state.next_po_id(),
        supplier_id=supplier_id,
        material_id=material_id,
        qty=qty,
        unit_cost=quoted_price,
        day_placed=state.current_day,
        lead_time=quoted_lead_time,
        expected_arrival_day=arrival_day,
        po_source="manual",
    )
    state.purchase_orders.append(po)

    mat = state.materials[material_id]
    _add_ledger(state, "Purchase", po.id,
                f"Manual PO: {qty}x {mat.name} from {supplier.name} @ ${quoted_price:.2f}",
                debit=cost)

    state.daily_events.append(
        f"📋 Manual PO {po.id}: {qty}x {mat.name} from {supplier.name} @ ${quoted_price:.2f} "
        f"(Expected: Day {arrival_day})"
    )
    _log_activity(state, "ERP", "PO_Created_Manual", po.id, "Student",
                  f"Manual PO: {qty}x {mat.name} from {supplier.name}",
                  financial_impact=-cost, kpi_tag="procurement_spend")
    return True, po.id


# =============================================================================
# FINANCE HELPERS
# =============================================================================

def get_income_statement(state: SimState) -> dict:
    cogs_estimate = state.total_cogs
    gross_profit = state.total_revenue - cogs_estimate
    total_opex = state.total_overhead + state.total_rework_cost + state.total_storage_cost + state.total_crm_marketing_spend
    ebit = gross_profit - total_opex
    total_penalties = state.total_penalties
    net_income = ebit - total_penalties
    return {
        "revenue": state.total_revenue,
        "cogs": cogs_estimate,
        "gross_profit": gross_profit,
        "gross_margin_pct": (gross_profit / state.total_revenue * 100) if state.total_revenue > 0 else 0,
        "overhead": state.total_overhead,
        "rework_cost": state.total_rework_cost,
        "storage_cost": state.total_storage_cost,
        "marketing_spend": state.total_crm_marketing_spend,
        "total_opex": total_opex,
        "ebit": ebit,
        "penalties": total_penalties,
        "net_income": net_income,
        "net_margin_pct": (net_income / state.total_revenue * 100) if state.total_revenue > 0 else 0,
    }


def get_kpis(state: SimState) -> dict:
    open_orders = [so for so in state.sales_orders if so.status == "Open"]
    shipped = [so for so in state.sales_orders if so.status == "Shipped"]
    cancelled = [so for so in state.sales_orders if so.status == "Cancelled"]
    total_closed = len(shipped) + len(cancelled)
    otif = (len(shipped) / total_closed * 100) if total_closed > 0 else 100.0
    # On-time: shipped_day <= due_day
    on_time = [s for s in shipped if s.shipped_day and s.shipped_day <= s.due_day]
    otif_exact = (len(on_time) / len(shipped) * 100) if shipped else 100.0

    inv_turnover = (state.total_cogs / max(1, sum(state.stock_materials.values()) * 10)) if state.total_cogs > 0 else 0

    return {
        "cash": state.cash,
        "revenue": state.total_revenue,
        "net_income": get_income_statement(state)["net_income"],
        "open_orders": len(open_orders),
        "shipped_orders": len(shipped),
        "cancelled_orders": len(cancelled),
        "otif_pct": round(otif_exact, 1),
        "inventory_value_raw": sum(state.stock_materials.get(m, 0) * mat.cost
                                   for m, mat in state.materials.items()),
        "inventory_value_fg": sum(state.stock_finished.get(p, 0) * prod.price
                                  for p, prod in state.products.items()),
        "wip_count": len([wo for wo in state.work_orders if wo.status == "InProgress"]),
        "total_penalties": state.total_penalties,
        "total_rework": state.total_rework_cost,
        "days_elapsed": state.current_day - 1,
    }


def run_mrp_suggestion(state: SimState) -> List[dict]:
    """MRP engine: compute what to order to cover next 7 days of demand."""
    suggestions = []

    # Project demand for next 7 days (simple average × 7)
    day_range = 7
    avg_daily = {}
    for prod in state.products.values():
        recent_sos = [so for so in state.sales_orders
                      if so.product_id == prod.id and so.day_placed >= state.current_day - 7]
        avg_qty = sum(so.qty for so in recent_sos) / max(7, state.current_day - 1)
        for mat_id, per_unit in prod.bom.items():
            avg_daily[mat_id] = avg_daily.get(mat_id, 0) + avg_qty * per_unit

    for mid, mat in state.materials.items():
        current = state.stock_materials.get(mid, 0)
        inbound = sum(po.qty for po in state.purchase_orders
                      if po.material_id == mid and po.status == "OnOrder")
        projected_demand_7d = round(avg_daily.get(mid, 0) * day_range)
        net_available = current + inbound - projected_demand_7d
        if net_available < mat.reorder_point:
            needed = max(mat.reorder_point * 2, projected_demand_7d) - current - inbound
            if needed > 0:
                suggestions.append({
                    "material_id": mid,
                    "material_name": mat.name,
                    "current_stock": current,
                    "inbound": inbound,
                    "projected_demand_7d": projected_demand_7d,
                    "suggested_qty": max(needed, state.materials[mid].reorder_point),
                    "urgency": "High" if current < mat.reorder_point // 2 else "Medium",
                })
    return suggestions


# =============================================================================
# KPI EXPORT
# =============================================================================

def export_activity_log(state: SimState) -> str:
    """Full CSV activity log for student KPI analysis."""
    import pandas as pd
    rows = []
    for al in state.activity_log:
        rows.append({
            "Day": al.day,
            "Module": al.module,
            "Event_Type": al.event_type,
            "Ref_ID": al.ref_id,
            "Actor": al.actor,
            "Description": al.description,
            "Financial_Impact": al.financial_impact,
            "KPI_Tag": al.kpi_tag,
        })
    # Also include all sales, POs, WOs
    for so in state.sales_orders:
        prod = state.products.get(so.product_id)
        rows.append({
            "Day": so.day_placed, "Module": "ERP", "Event_Type": "SalesOrder_Created",
            "Ref_ID": so.id, "Actor": "System",
            "Description": f"{so.customer_name}: {so.qty}x {prod.name if prod else so.product_id}. Status={so.status}",
            "Financial_Impact": so.qty * so.unit_price if so.status == "Shipped" else 0,
            "KPI_Tag": "sales",
        })
    df = pd.DataFrame(rows).sort_values(["Day", "Module"])
    return df.to_csv(index=False)


def export_kpi_summary(state: SimState) -> str:
    """Pre-computed KPI table for student analysis."""
    import pandas as pd
    inc = get_income_statement(state)
    kpis = get_kpis(state)
    rows = [
        {"KPI": "Total Revenue", "Value": f"${inc['revenue']:,.0f}", "Module": "ERP", "Category": "Finance"},
        {"KPI": "Total COGS", "Value": f"${inc['cogs']:,.0f}", "Module": "ERP", "Category": "Finance"},
        {"KPI": "Gross Profit", "Value": f"${inc['gross_profit']:,.0f}", "Module": "ERP", "Category": "Finance"},
        {"KPI": "Gross Margin %", "Value": f"{inc['gross_margin_pct']:.1f}%", "Module": "ERP", "Category": "Finance"},
        {"KPI": "Net Income", "Value": f"${inc['net_income']:,.0f}", "Module": "ERP", "Category": "Finance"},
        {"KPI": "Net Margin %", "Value": f"{inc['net_margin_pct']:.1f}%", "Module": "ERP", "Category": "Finance"},
        {"KPI": "Cash Balance", "Value": f"${kpis['cash']:,.0f}", "Module": "ERP", "Category": "Finance"},
        {"KPI": "Orders Shipped", "Value": kpis["shipped_orders"], "Module": "ERP", "Category": "Sales"},
        {"KPI": "Orders Cancelled/Lost", "Value": kpis["cancelled_orders"], "Module": "ERP", "Category": "Sales"},
        {"KPI": "On-Time In-Full %", "Value": f"{kpis['otif_pct']:.1f}%", "Module": "ERP", "Category": "Sales"},
        {"KPI": "Total Stockout Penalties", "Value": f"${kpis['total_penalties']:,.0f}", "Module": "ERP", "Category": "Sales"},
        {"KPI": "Total Rework Cost", "Value": f"${kpis['total_rework']:,.0f}", "Module": "ERP", "Category": "Production"},
        {"KPI": "Storage Costs", "Value": f"${state.total_storage_cost:,.0f}", "Module": "ERP", "Category": "Warehouse"},
        {"KPI": "SRM Enabled", "Value": "Yes" if state.srm_enabled else "No", "Module": "Config", "Category": "System"},
        {"KPI": "CRM Enabled", "Value": "Yes" if state.crm_enabled else "No", "Module": "Config", "Category": "System"},
        {"KPI": "Simulation Days Elapsed", "Value": kpis["days_elapsed"], "Module": "Config", "Category": "System"},
    ]
    if state.srm_enabled:
        from Archive.ERP_Sim_Integrated.engine.srm_engine import get_srm_kpis
        srm = get_srm_kpis(state)
        for k, v in srm.items():
            rows.append({"KPI": k, "Value": v, "Module": "SRM", "Category": "Procurement"})
    if state.crm_enabled:
        from Archive.ERP_Sim_Integrated.engine.crm_engine import get_crm_kpis
        crm = get_crm_kpis(state)
        for k, v in crm.items():
            rows.append({"KPI": k, "Value": v, "Module": "CRM", "Category": "Sales"})

    return pd.DataFrame(rows).to_csv(index=False)


def evaluate_performance(state: SimState) -> dict:
    inc = get_income_statement(state)
    kpis = get_kpis(state)
    
    base_score = 40
    profit_bonus = min(35, max(0, inc["net_income"] / 2000)) 
    otif_bonus = (kpis["otif_pct"] / 100) * 15 
    penalty_deduction = min(20, kpis["total_penalties"] / 500) 
    
    srm_bonus = 5 if state.srm_enabled else 0
    crm_bonus = 5 if state.crm_enabled else 0
    
    total_score = max(0, min(100, base_score + profit_bonus + otif_bonus - penalty_deduction + srm_bonus + crm_bonus))
    
    grade = "A+" if total_score >= 95 else "A" if total_score >= 90 else "B" if total_score >= 80 else "C" if total_score >= 70 else "D"
    
    if total_score > 85:
        summary = "Excellent operations management! Your integration of systems led to high profitability and customer satisfaction."
    elif total_score > 70:
        summary = "Good effort. Enhancing your use of SRM for better supplier pricing or CRM for automated sales could boost your profitability."
    else:
        summary = "Operations struggled. Review your stockout penalties and ensure you are utilizing module data to make timely decisions."

    return {
        "score": round(total_score, 1),
        "grade": grade,
        "profit_bonus": round(profit_bonus, 1),
        "otif_bonus": round(otif_bonus, 1),
        "module_bonus": srm_bonus + crm_bonus,
        "penalties": round(-penalty_deduction, 1),
        "summary": summary,
    }


def generate_simulated_log(scenario: str = "optimized") -> str:
    """Generates a dummy activity log for students to practice past simulation analysis."""
    import pandas as pd
    import random
    rows = []
    cash = 50000
    for day in range(1, 31):
        if scenario == "optimized":
            orders = random.randint(4, 7)
            spend_mult = 0.8
            rework_cost = random.choice([0, 0, 0, 500])
        else:
            orders = random.randint(1, 4)
            spend_mult = 1.2
            rework_cost = random.choice([0, 500, 1000])

        for _ in range(orders):
            rev = random.uniform(800, 2500)
            rows.append({"Day": day, "Module": "ERP", "Event_Type": "SalesOrder_Shipped", "Actor": "Student", "Description": "Shipped Order", "Financial_Impact": rev, "KPI_Tag": "sales_revenue"})
            cash += rev
            
        if day % 6 == 0:
            spend = random.uniform(3000, 6000) * spend_mult
            rows.append({"Day": day, "Module": "ERP", "Event_Type": "PO_Created", "Actor": "Student", "Description": "Purchased Materials", "Financial_Impact": -spend, "KPI_Tag": "procurement_spend"})
            cash -= spend
            
        if rework_cost > 0:
            rows.append({"Day": day, "Module": "Production", "Event_Type": "Quality_Issue", "Actor": "System", "Description": "Rework Required", "Financial_Impact": -rework_cost, "KPI_Tag": "production_quality"})
            cash -= rework_cost
            
    return pd.DataFrame(rows).to_csv(index=False)


# =============================================================================
# HELPERS
# =============================================================================

def _add_ledger(state: SimState, entry_type: str, ref_id: str, desc: str,
                debit: float = 0, credit: float = 0, module: str = "ERP"):
    state._fe_counter += 1
    state.financial_ledger.append(FinancialEntry(
        day=state.current_day, entry_type=entry_type, ref_id=ref_id,
        description=desc, debit=debit, credit=credit, module=module
    ))


def _add_inv_movement(state: SimState, material_id, product_id, mvt_type, qty, ref_id, desc):
    state.inventory_movements.append(InventoryMovement(
        day=state.current_day, material_id=material_id, product_id=product_id,
        movement_type=mvt_type, qty=qty, ref_id=ref_id, description=desc
    ))


def _log_activity(state: SimState, module: str, event_type: str, ref_id: str,
                  actor: str, description: str, financial_impact: float = 0, kpi_tag: str = ""):
    state.activity_log.append(ActivityLog(
        day=state.current_day,
        timestamp_sim=f"Day {state.current_day}",
        module=module,
        event_type=event_type,
        ref_id=ref_id,
        actor=actor,
        description=description,
        financial_impact=financial_impact,
        kpi_tag=kpi_tag,
    ))
