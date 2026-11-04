# =============================================================================
# EIS Simulator — Configuration & Constants
# Enterprise Information System Simulator (ERP + SRM + CRM)
# =============================================================================

COMPANY_NAME = "VéloForge Industries"
SIMULATION_DAYS = 30
STARTING_CASH = 50_000.0
DAILY_CAPACITY_HOURS = 80  # 10 workers × 8 hours

# =============================================================================
# MASTER DATA — MATERIALS
# =============================================================================
MATERIALS_CONFIG = {
    "M01": {"name": "Steel Frame Tube",   "cost": 18.0,  "unit": "pcs", "reorder_point": 20, "category": "A"},
    "M02": {"name": "Rubber Tire",         "cost": 9.50,  "unit": "pcs", "reorder_point": 30, "category": "A"},
    "M03": {"name": "Saddle & Seatpost",  "cost": 14.0,  "unit": "pcs", "reorder_point": 15, "category": "B"},
    "M04": {"name": "Brake Assembly",     "cost": 11.0,  "unit": "pcs", "reorder_point": 20, "category": "A"},
    "M05": {"name": "Gear Shifter Set",   "cost": 22.0,  "unit": "pcs", "reorder_point": 10, "category": "A"},
    "M06": {"name": "Paint & Lacquer",    "cost": 6.50,  "unit": "L",   "reorder_point": 10, "category": "C"},
}

# =============================================================================
# MASTER DATA — PRODUCTS (Bill of Materials)
# =============================================================================
PRODUCTS_CONFIG = {
    "P01": {
        "name": "City Cruiser",
        "price": 249.0,
        "bom": {"M01": 2, "M02": 2, "M03": 1, "M04": 1, "M06": 1},  # no gears
        "production_hours": 4,
        "category": "Standard",
        "description": "Entry-level urban commuter bicycle",
    },
    "P02": {
        "name": "Trail Blazer",
        "price": 449.0,
        "bom": {"M01": 3, "M02": 2, "M03": 1, "M04": 2, "M05": 1, "M06": 2},
        "production_hours": 7,
        "category": "Sport",
        "description": "21-speed mountain bike for outdoor enthusiasts",
    },
    "P03": {
        "name": "Pro Racer",
        "price": 799.0,
        "bom": {"M01": 4, "M02": 2, "M03": 1, "M04": 2, "M05": 2, "M06": 2},
        "production_hours": 10,
        "category": "Premium",
        "description": "Professional-grade carbon-fibre racing bicycle",
    },
}

# =============================================================================
# MASTER DATA — SUPPLIERS
# =============================================================================
SUPPLIERS_CONFIG = {
    "S01": {
        "name": "IronCore Metals",
        "category": "Steel & Frames",
        "materials": ["M01"],
        "base_price": {"M01": 18.0},
        "lead_time_days": 3,
        "quality_rate": 0.97,   # 97% defect-free
        "reliability": 0.95,    # 95% on-time
        "min_order_qty": 20,
        "description": "Domestic steel supplier. Reliable but slightly pricier.",
        "country": "USA",
    },
    "S02": {
        "name": "AsiaParts Co.",
        "category": "Multi-component",
        "materials": ["M01", "M02", "M04", "M06"],
        "base_price": {"M01": 14.0, "M02": 7.50, "M04": 9.0, "M06": 5.00},
        "lead_time_days": 7,
        "quality_rate": 0.88,   # higher defect risk
        "reliability": 0.82,
        "min_order_qty": 50,
        "description": "Low-cost Asian importer. Cheap but unreliable.",
        "country": "China",
    },
    "S03": {
        "name": "WheelTech Solutions",
        "category": "Tires & Wheels",
        "materials": ["M02"],
        "base_price": {"M02": 9.50},
        "lead_time_days": 2,
        "quality_rate": 0.99,
        "reliability": 0.98,
        "min_order_qty": 10,
        "description": "Premium tire specialist. Best quality, fair price.",
        "country": "Germany",
    },
    "S04": {
        "name": "ComfortRide Ergonomics",
        "category": "Saddles & Ergonomics",
        "materials": ["M03"],
        "base_price": {"M03": 14.0},
        "lead_time_days": 4,
        "quality_rate": 0.95,
        "reliability": 0.90,
        "min_order_qty": 10,
        "description": "Ergonomic components specialist.",
        "country": "Italy",
    },
    "S05": {
        "name": "BrakeMaster Inc.",
        "category": "Brakes & Gears",
        "materials": ["M04", "M05"],
        "base_price": {"M04": 11.0, "M05": 22.0},
        "lead_time_days": 3,
        "quality_rate": 0.96,
        "reliability": 0.93,
        "min_order_qty": 10,
        "description": "Mechanical components. Good quality and delivery.",
        "country": "USA",
    },
}

# =============================================================================
# MASTER DATA — CUSTOMERS (CRM)
# =============================================================================
CUSTOMERS_CONFIG = [
    {"name": "BuildRight Sports",   "tier": "Enterprise", "city": "Chicago",    "email": "purchasing@buildright.com",  "mrr_base": 4500},
    {"name": "CityRide Retail",     "tier": "Mid-Market", "city": "Austin",     "email": "orders@cityride.com",        "mrr_base": 2200},
    {"name": "EcoCycle Co.",        "tier": "Small",      "city": "Portland",   "email": "info@ecocycle.co",           "mrr_base": 800},
    {"name": "AthleteZone",         "tier": "Mid-Market", "city": "New York",   "email": "procurement@athletezone.com","mrr_base": 3100},
    {"name": "GreenPath Mobility",  "tier": "Small",      "city": "Seattle",    "email": "orders@greenpath.io",        "mrr_base": 650},
    {"name": "ProSport Distributors","tier": "Enterprise","city": "Dallas",     "email": "b2b@prosport.com",           "mrr_base": 6800},
]

# =============================================================================
# SIMULATION PARAMETERS
# =============================================================================
DEMAND_PARAMS = {
    "daily_orders_min": 1,
    "daily_orders_max": 4,
    "rush_order_probability": 0.15,   # 15% chance of rush order (due in 2 days)
    "stockout_penalty_per_unit": 35,  # Lost margin when we can't ship
    "late_shipment_penalty_pct": 0.05,# 5% discount for late orders
}

PRODUCTION_PARAMS = {
    "quality_pass_rate": 0.97,        # 3% of production has quality issues
    "rework_cost_per_unit": 25,
}

FINANCIAL_PARAMS = {
    "storage_cost_per_unit_day": 0.50,
    "ar_payment_days": 14,            # Customers pay in 14 days
    "ap_payment_days": 30,            # We pay suppliers in 30 days
    "daily_overhead": 800,            # Rent, utilities, salaries
}

# SRM-specific
SRM_PARAMS = {
    "rfq_response_days_simulated": 0, # With SRM: instant response in portal
    "rfq_response_days_manual": 1,    # Without SRM: response arrives next day by "email"
    "contract_discount_pct": 0.04,    # 4% discount for contracted volumes
    "supplier_score_weights": {"quality": 0.40, "delivery": 0.35, "price": 0.25},
}

# CRM-specific
CRM_PARAMS = {
    "lead_to_opportunity_days": 2,
    "opportunity_close_days_avg": 7,
    "marketing_campaigns": {
        "digital_ads":     {"cost": 500,   "leads_min": 1, "leads_max": 2, "win_prob_range": (30, 55)},
        "outbound_calls":  {"cost": 1200,  "leads_min": 2, "leads_max": 4, "win_prob_range": (45, 65)},
        "trade_show":      {"cost": 3500,  "leads_min": 3, "leads_max": 5, "win_prob_range": (60, 80)},
    },
}

# =============================================================================
# UI STYLING
# =============================================================================
THEME = {
    "primary":   "#1A56DB",      # SAP-blue
    "secondary": "#0E9F6E",      # Green (good)
    "warning":   "#E3A008",      # Amber
    "danger":    "#E02424",      # Red (critical)
    "bg":        "#F8FAFC",
    "card_bg":   "#FFFFFF",
    "border":    "#E2E8F0",
    "text_muted":"#64748B",
    "sidebar_bg":"#1E293B",
}

MODULE_COLORS = {
    "ERP": "#1A56DB",
    "SRM": "#7E3AF2",
    "CRM": "#0E9F6E",
}
