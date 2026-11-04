# =============================================================================
# EIS Simulator — Unified State (All Dataclasses)
# =============================================================================
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import random


# =============================================================================
# CORE ERP ENTITIES
# =============================================================================

@dataclass
class Material:
    id: str
    name: str
    cost: float
    unit: str
    reorder_point: int
    category: str  # ABC classification


@dataclass
class Product:
    id: str
    name: str
    price: float
    bom: Dict[str, int]
    production_hours: int
    category: str
    description: str


@dataclass
class SalesOrder:
    id: str
    day_placed: int
    customer_name: str
    customer_id: Optional[str]
    product_id: str
    qty: int
    unit_price: float
    due_day: int
    source: str = "manual"          # "manual" | "crm_opportunity" | "portal"
    status: str = "Open"            # Open | Shipped | Cancelled | Late
    shipped_day: Optional[int] = None
    late_penalty_applied: bool = False
    opportunity_id: Optional[str] = None   # linked CRM opportunity


@dataclass
class WorkOrder:
    id: str
    product_id: str
    qty: int
    day_started: int
    hours_required: int
    hours_completed: int = 0
    status: str = "InProgress"      # InProgress | Completed | QC_Hold
    completion_day: int = 0
    rework_cost: float = 0.0        # Quality issues


@dataclass
class PurchaseOrder:
    id: str
    supplier_id: str
    material_id: str
    qty: int
    unit_cost: float
    day_placed: int
    lead_time: int
    expected_arrival_day: int
    status: str = "OnOrder"         # OnOrder | Received | Cancelled
    actual_arrival_day: Optional[int] = None
    qty_received: int = 0           # may be less than ordered (partial)
    is_contracted: bool = False
    rfq_id: Optional[str] = None
    invoice_id: Optional[str] = None
    po_source: str = "manual"       # "manual" | "srm_rfq" | "srm_contract"


@dataclass
class FinancialEntry:
    day: int
    entry_type: str     # Revenue | COGS | OpEx | Purchase | Payment | Penalty
    ref_id: str
    description: str
    debit: float = 0.0
    credit: float = 0.0
    module: str = "ERP"             # ERP | SRM | CRM


# =============================================================================
# INVENTORY & WAREHOUSE
# =============================================================================

@dataclass
class InventoryMovement:
    day: int
    material_id: Optional[str]
    product_id: Optional[str]
    movement_type: str      # GR | GI | Production_Consumption | Sales_Issue | Adjustment
    qty: int
    ref_id: str
    description: str


# =============================================================================
# SRM ENTITIES
# =============================================================================

@dataclass
class Supplier:
    id: str
    name: str
    category: str
    materials: List[str]
    base_price: Dict[str, float]     # material_id -> price
    current_price: Dict[str, float]  # fluctuates daily
    lead_time_days: int
    quality_rate: float              # 0-1, % defect-free
    reliability: float               # 0-1, % on-time
    min_order_qty: int
    description: str
    country: str
    relationship_score: float = 75.0 # 0–100
    is_blocked: bool = False
    deliveries_total: int = 0
    deliveries_on_time: int = 0
    defects_total: int = 0
    units_received_total: int = 0
    total_spend: float = 0.0
    contract_price: Optional[Dict[str, float]] = None  # negotiated prices


@dataclass
class RFQ:
    id: str
    day_sent: int
    material_id: str
    qty_requested: int
    status: str = "Pending"         # Pending | QuotesReceived | Awarded | Cancelled
    responses: List[dict] = field(default_factory=list)  # [{supplier_id, price, lead_time, score}]
    awarded_supplier_id: Optional[str] = None


@dataclass
class SupplierInvoice:
    id: str
    supplier_id: str
    po_id: str
    amount: float
    day_issued: int
    due_day: int
    status: str = "Unpaid"          # Unpaid | Paid | Overdue
    paid_day: Optional[int] = None
    early_payment_discount: float = 0.0


@dataclass
class EmailMessage:
    """Legacy simulated inbox message (still used for some system alerts)"""
    id: str
    day_received: int
    sender: str
    subject: str
    body: str
    category: str = "general"       # rfq_response | customer_order | alert | system
    is_read: bool = False
    action_data: Optional[dict] = None

@dataclass
class CommunicationEntry:
    """Localized communication log entry for Procurement/Sales pages"""
    id: str
    day: int
    module: str             # Procurement | Sales
    entity_id: str          # Supplier ID or Customer ID
    entity_name: str
    direction: str          # Inbound | Outbound
    subject: str
    body: str
    action_type: Optional[str] = None  # rfq_quote | customer_order
    action_data: Optional[dict] = None
    is_read: bool = False
    status: str = "Pending"  # Pending | Accepted | Rejected | Discarded

@dataclass
class PendingRFQ:
    """RFQ that is being processed for next-day reply in manual mode"""
    id: str
    day_sent: int
    material_id: str
    qty: int
    days_to_reply: int = 1


# =============================================================================
# CRM ENTITIES
# =============================================================================

@dataclass
class Customer:
    id: str
    name: str
    tier: str               # Small | Mid-Market | Enterprise
    city: str
    email: str
    mrr: float              # Monthly Recurring Revenue (once active)
    csat: int = 85          # Customer Satisfaction 0–100
    lifetime_value: float = 0.0
    days_as_customer: int = 0
    churn_risk: float = 0.0
    open_tickets: int = 0
    total_orders: int = 0
    total_revenue: float = 0.0
    is_active: bool = True


@dataclass
class Lead:
    id: str
    day_created: int
    company: str
    contact_name: str
    email: str
    tier: str               # Small | Mid-Market | Enterprise
    estimated_value: float
    product_interest: List[str]
    stage: str = "New"      # New | Qualified | Proposal | Negotiation | Won | Lost
    win_probability: int = 25
    assigned_rep: Optional[str] = None
    source: str = "inbound" # inbound | outbound | referral | trade_show
    notes: str = ""
    days_in_stage: int = 0
    expected_close_day: Optional[int] = None


@dataclass
class ServiceTicket:
    id: str
    customer_id: str
    customer_name: str
    day_opened: int
    issue: str
    severity: str           # Low | Medium | High | Critical
    status: str = "Open"    # Open | In Progress | Resolved | Escalated
    resolution_cost: float = 0.0
    resolved_day: Optional[int] = None
    csat_impact: int = -5   # CSAT change on resolution


# =============================================================================
# ACTIVITY LOG (for student KPI download)
# =============================================================================

@dataclass
class ActivityLog:
    day: int
    timestamp_sim: str      # "Day X, HH:MM"
    module: str             # ERP | SRM | CRM | System
    event_type: str
    ref_id: str
    actor: str              # "Student" | "System"
    description: str
    financial_impact: float = 0.0
    kpi_tag: str = ""       # Tag for KPI analysis


# =============================================================================
# MASTER SIMULATION STATE
# =============================================================================

@dataclass
class SimState:
    # Simulation control
    current_day: int = 1
    max_days: int = 30
    cash: float = 50_000.0
    game_over: bool = False

    # Module flags (instructor-controlled)
    srm_enabled: bool = False
    crm_enabled: bool = False

    # Master data
    materials: Dict[str, Material] = field(default_factory=dict)
    products: Dict[str, Product] = field(default_factory=dict)
    suppliers: Dict[str, Supplier] = field(default_factory=dict)
    customers: Dict[str, Customer] = field(default_factory=dict)

    # Inventory
    stock_materials: Dict[str, int] = field(default_factory=dict)
    stock_finished: Dict[str, int] = field(default_factory=dict)

    # ERP Transactions
    sales_orders: List[SalesOrder] = field(default_factory=list)
    work_orders: List[WorkOrder] = field(default_factory=list)
    purchase_orders: List[PurchaseOrder] = field(default_factory=list)
    inventory_movements: List[InventoryMovement] = field(default_factory=list)
    financial_ledger: List[FinancialEntry] = field(default_factory=list)

    # SRM
    rfqs: List[RFQ] = field(default_factory=list)
    pending_rfqs: List[PendingRFQ] = field(default_factory=list)
    supplier_invoices: List[SupplierInvoice] = field(default_factory=list)

    # CRM
    leads: List[Lead] = field(default_factory=list)
    service_tickets: List[ServiceTicket] = field(default_factory=list)

    # Communications (Localized Logs)
    inbox: List[EmailMessage] = field(default_factory=list)
    communication_log: List[CommunicationEntry] = field(default_factory=list)

    # Activity & financials
    activity_log: List[ActivityLog] = field(default_factory=list)
    daily_events: List[str] = field(default_factory=list)   # Today's feed

    # Cumulative financials
    total_revenue: float = 0.0
    total_cogs: float = 0.0
    total_overhead: float = 0.0
    total_purchase_spend: float = 0.0
    total_penalties: float = 0.0
    total_rework_cost: float = 0.0
    total_storage_cost: float = 0.0
    total_crm_marketing_spend: float = 0.0

    # Historical snapshots for charting
    daily_snapshots: List[dict] = field(default_factory=list)

    # ID counters
    _so_counter: int = 1
    _wo_counter: int = 1
    _po_counter: int = 1
    _rfq_counter: int = 1
    _inv_counter: int = 1
    _ticket_counter: int = 1
    _lead_counter: int = 1
    _email_counter: int = 1
    _fe_counter: int = 1

    def next_so_id(self) -> str:
        self._so_counter += 1
        return f"SO-{self.current_day:02d}-{self._so_counter:04d}"

    def next_wo_id(self) -> str:
        self._wo_counter += 1
        return f"WO-{self.current_day:02d}-{self._wo_counter:04d}"

    def next_po_id(self) -> str:
        self._po_counter += 1
        return f"PO-{self.current_day:02d}-{self._po_counter:04d}"

    def next_rfq_id(self) -> str:
        self._rfq_counter += 1
        return f"RFQ-{self.current_day:02d}-{self._rfq_counter:04d}"

    def next_inv_id(self) -> str:
        self._inv_counter += 1
        return f"INV-{self.current_day:02d}-{self._inv_counter:04d}"

    def next_ticket_id(self) -> str:
        self._ticket_counter += 1
        return f"TKT-{self.current_day:02d}-{self._ticket_counter:04d}"

    def next_lead_id(self) -> str:
        self._lead_counter += 1
        return f"LEAD-{self.current_day:02d}-{self._lead_counter:04d}"

    def next_email_id(self) -> str:
        self._email_counter += 1
        return f"MSG-{self.current_day:02d}-{self._email_counter:04d}"
