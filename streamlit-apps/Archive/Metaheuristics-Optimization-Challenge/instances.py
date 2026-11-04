import random

# Fixed instances for Knapsack Problem
# Each instance: {"items": [{"id": i, "w": weight, "v": value}, ...], "capacity": C}
KNAPSACK_INSTANCES = []

# Instance 1
KNAPSACK_INSTANCES.append({
    "capacity": 50,
    "items": [
        {"id": 0, "w": 10, "v": 60}, {"id": 1, "w": 20, "v": 100}, {"id": 2, "w": 30, "v": 120},
        {"id": 3, "w": 5, "v": 30}, {"id": 4, "w": 15, "v": 70}, {"id": 5, "w": 8, "v": 45},
        {"id": 6, "w": 10, "v": 50}, {"id": 7, "w": 12, "v": 55}, {"id": 8, "w": 7, "v": 40},
        {"id": 9, "w": 18, "v": 90}, {"id": 10, "w": 3, "v": 15}, {"id": 11, "w": 25, "v": 110},
        {"id": 12, "w": 6, "v": 35}, {"id": 13, "w": 14, "v": 75}, {"id": 14, "w": 9, "v": 48}
    ]
})

# Instance 2
KNAPSACK_INSTANCES.append({
    "capacity": 65,
    "items": [
        {"id": 0, "w": 12, "v": 70}, {"id": 1, "w": 25, "v": 110}, {"id": 2, "w": 35, "v": 130},
        {"id": 3, "w": 8, "v": 40}, {"id": 4, "w": 18, "v": 80}, {"id": 5, "w": 10, "v": 55},
        {"id": 6, "w": 5, "v": 25}, {"id": 7, "w": 15, "v": 75}, {"id": 8, "w": 20, "v": 95},
        {"id": 9, "w": 22, "v": 105}, {"id": 10, "w": 4, "v": 20}, {"id": 11, "w": 28, "v": 120},
        {"id": 12, "w": 7, "v": 38}, {"id": 13, "w": 16, "v": 85}, {"id": 14, "w": 11, "v": 60}
    ]
})

# Adding more generic instances to reach 10
# Using fixed seeds for the rest to ensure they're consistent across calls
for i in range(2, 10):
    rng = random.Random(i + 100) # Fixed seed
    cap = rnd_cap = 50 + i * 5
    n_items = 15 + (i % 3) * 5
    items = []
    for j in range(n_items):
        w = rng.randint(2, 25)
        v = rng.randint(10, 80)
        items.append({"id": j, "w": w, "v": v})
    KNAPSACK_INSTANCES.append({"capacity": cap, "items": items})

# Fixed instances for p-Median Problem
# Each instance: {"cities": [{"id": i, "x": x, "y": y}, ...], "p": p}
PMEDIAN_INSTANCES = []

# Instance 1
PMEDIAN_INSTANCES.append({
    "p": 3,
    "cities": [
        {"id": 0, "x": 10, "y": 20}, {"id": 1, "x": 15, "y": 80}, {"id": 2, "w": 35, "x": 80, "y": 50},
        {"id": 3, "x": 50, "y": 90}, {"id": 4, "x": 20, "y": 25}, {"id": 5, "x": 45, "y": 10},
        {"id": 6, "x": 70, "y": 80}, {"id": 7, "x": 90, "y": 20}, {"id": 8, "x": 55, "y": 55},
        {"id": 9, "x": 30, "y": 40}, {"id": 10, "x": 85, "y": 95}, {"id": 11, "x": 10, "y": 60},
        {"id": 12, "x": 65, "y": 15}, {"id": 13, "x": 25, "y": 75}, {"id": 14, "x": 40, "y": 30}
    ]
})

# Adding more generic instances to reach 10
for i in range(1, 10):
    rng = random.Random(i + 200) # Fixed seed
    p = 3 + (i % 3)
    n_cities = 20 + (i % 2) * 10
    cities = []
    for j in range(n_cities):
        x = rng.randint(0, 100)
        y = rng.randint(0, 100)
        cities.append({"id": j, "x": x, "y": y})
    PMEDIAN_INSTANCES.append({"p": p, "cities": cities})
