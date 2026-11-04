from game_engine import GameState, create_customer_order, ship_specific_order, generate_customer_demand

def test_manual_shipping():
    state = GameState()
    state.inventory = 50
    
    # 1. Create order
    print("Testing Order Creation...")
    order = create_customer_order(state, 40)
    print(f"Created Order #{order.id} for {order.customer.name} (Qty: {order.quantity}, Due: Day {order.due_date})")
    
    # 2. Try strict shipping (Available)
    print("\nTesting Valid Shipping...")
    success = ship_specific_order(state, order.id)
    if success:
        print("SUCCESS: Order shipped.")
        if state.inventory == 10:
            print("SUCCESS: Inventory deducted correctly (50 -> 10).")
        else:
            print(f"FAILURE: Inventory mismatch ({state.inventory})")
            
        if order.status == "in_transit":
             print("SUCCESS: Order status updated.")
    else:
        print("FAILURE: Valid shipping failed.")

    # 3. Create order > Inventory
    print("\nTesting Insufficient Stock...")
    order2 = create_customer_order(state, 20) # Need 20, have 10
    success2 = ship_specific_order(state, order2.id)
    if not success2:
        print("SUCCESS: Shipping blocked due to low stock.")
    else:
        print("FAILURE: Shipping allowed despite low stock!")

if __name__ == "__main__":
    test_manual_shipping()
