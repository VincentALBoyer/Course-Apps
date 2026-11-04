from game_engine import GameState, place_supplier_order, SUPPLIERS, generate_customer_demand, create_customer_order

def test_engine():
    state = GameState()
    print(f"Initial Cash: {state.cash}")
    
    # Test placing order
    sid = "dragon"
    supplier = SUPPLIERS[sid]
    qty = 100
    # Ensure min order and cash check pass
    if qty >= supplier.min_order and state.cash >= qty * supplier.unit_price:
        order = place_supplier_order(state, sid, qty)
        
        if order:
            print(f"Order placed: {order}")
            expected_cash = 5000 - (qty * supplier.unit_price)
            if state.cash == expected_cash:
                print("SUCCESS: Cash deducted correctly")
            else:
                print(f"FAILURE: Cash mismatch. Expected {expected_cash}, got {state.cash}")
        else:
            print("FAILURE: Order not placed returned None")
    else:
        print("Test setup invalid for order")

    # Test demand
    demand = generate_customer_demand(1)
    print(f"Generated demand: {demand}")
    if demand > 0:
        print("SUCCESS: Demand generated")
    else:
        print("FAILURE: No demand")

if __name__ == "__main__":
    test_engine()
