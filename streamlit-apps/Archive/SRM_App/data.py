import pandas as pd
import random
import uuid

# -----------------------------------------------------------------------------
# CONSTANTS
# -----------------------------------------------------------------------------
SUPPLIER_NAMES = [
    "Global Chips Ltd", "FastTrack Logistics", "Raw Materials Inc", 
    "Precision Components", "Alpha Steel", "Omega Polymers", 
    "Green Pack Solutions", "MicroTech Asia"
]

LOCATIONS = ["China", "Germany", "Mexico", "Vietnam", "USA", "India"]

# -----------------------------------------------------------------------------
# DATA GENERATION
# -----------------------------------------------------------------------------

def generate_suppliers(n=8):
    """Generate supplier database with performance metrics"""
    suppliers = []
    for _ in range(n):
        s_name = random.choice(SUPPLIER_NAMES)
        SUPPLIER_NAMES.remove(s_name) if s_name in SUPPLIER_NAMES else None
        
        suppliers.append({
            "id": str(uuid.uuid4())[:8],
            "name": s_name,
            "location": random.choice(LOCATIONS),
            "quality_score": random.randint(75, 99), # out of 100
            "on_time_delivery": random.randint(60, 98), # %
            "cost_index": random.choice(["Low", "Medium", "High"]),
            "status": "Approved"
        })
    return pd.DataFrame(suppliers)

def generate_rfp_bids(item_name):
    """Generate 3 bids for a specific item RFP"""
    bids = []
    names = random.sample(["Bidder A", "Bidder B", "Bidder C"], 3)
    
    for name in names:
        cost = random.randint(10000, 50000)
        lead_time = random.randint(10, 45)
        quality = random.choice(["Standard", "High", "Premium"])
        
        # Trade-off logic
        if cost < 20000:
            quality = "Standard"
        if quality == "Premium":
            cost = int(cost * 1.5)
            
        bids.append({
            "bidder": name,
            "cost": cost,
            "lead_time_days": lead_time,
            "quality_tier": quality,
            "score": 0 # to be calculated by user
        })
    return pd.DataFrame(bids)
