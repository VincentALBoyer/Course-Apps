import pandas as pd
import random
import uuid

# -----------------------------------------------------------------------------
# CONSTANTS & CONFIG
# -----------------------------------------------------------------------------
CUSTOMER_NAMES = [
    "TechFront Inc", "Global Logistics Co", "Retail Giant Ltd", 
    "FastMove Express", "EcoSupply S.A.", "Urban Trends", 
    "MegaCorp Int.", "Nano Systems", "Green Foods", "BlueSky Aviation"
]

INDUSTRIES = ["Technology", "Retail", "Manufacturing", "Healthcare", "Logistics"]
LOCATIONS = ["North America", "Europe", "Asia-Pacific", "Latam"]

# -----------------------------------------------------------------------------
# DATA GENERATION
# -----------------------------------------------------------------------------

def generate_customers(n=10):
    """Generate initial customer base"""
    customers = []
    for _ in range(n):
        c_name = random.choice(CUSTOMER_NAMES)
        # Ensure unique names if n < len
        CUSTOMER_NAMES.remove(c_name) if c_name in CUSTOMER_NAMES else None
        
        customers.append({
            "id": str(uuid.uuid4())[:8],
            "name": c_name,
            "industry": random.choice(INDUSTRIES),
            "region": random.choice(LOCATIONS),
            "satisfaction": random.randint(70, 95), # Initial score
            "lifetime_value": random.randint(50000, 500000),
            "status": "Active"
        })
    return pd.DataFrame(customers)

def generate_leads(n=5):
    """Generate potential sales leads"""
    leads = []
    for i in range(n):
        leads.append({
            "id": str(uuid.uuid4())[:8],
            "company": f"Prospect {random.randint(100, 999)}",
            "potential_value": random.randint(10000, 100000),
            "stage": random.choice(["New", "Qualification", "Negotiation"]),
            "probability": random.randint(10, 60),
            "contact_email": f"contact{i}@prospect.com"
        })
    return pd.DataFrame(leads)

def generate_ticket(customer_name, day):
    """Create a service ticket"""
    issues = [
        "Late Delivery", "Damaged Goods", "Invoice Error", 
        "Access Issue", "Product Question"
    ]
    return {
        "id": f"TKT-{random.randint(1000, 9999)}",
        "customer": customer_name,
        "issue": random.choice(issues),
        "priority": random.choice(["Low", "Medium", "High", "Critical"]),
        "status": "Open",
        "day_created": day
    }
