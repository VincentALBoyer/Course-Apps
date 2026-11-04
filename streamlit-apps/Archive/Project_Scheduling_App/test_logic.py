from logic import SchedulingLogic

def test_logic():
    logic = SchedulingLogic()
    print("Initial Tasks:", len(logic.get_unassigned_tasks()))
    
    # Assign T1 (Design) to Alice (Design)
    logic.assign_task("T1", "W1")
    print("Assigned T1 to Alice")
    
    # Assign T2 (Backend, after T1) to Bob (Backend)
    logic.assign_task("T2", "W2")
    print("Assigned T2 to Bob")
    
    makespan = logic.get_makespan()
    print(f"Current Makespan: {makespan}")
    
    t1 = logic.tasks["T1"]
    t2 = logic.tasks["T2"]
    print(f"T1: {t1.start_time} - {t1.end_time}")
    print(f"T2: {t2.start_time} - {t2.end_time}")
    
    assert t2.start_time >= t1.end_time
    print("Precedence Test Passed!")

if __name__ == "__main__":
    test_logic()
