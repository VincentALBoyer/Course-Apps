import pandas as pd
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import datetime

@dataclass
class Task:
    id: str
    name: str
    project: str
    duration: int  # in hours or days
    skills_required: List[str]
    predecessors: List[str] = field(default_factory=list)
    assigned_worker: Optional[str] = None
    start_time: Optional[int] = None
    end_time: Optional[int] = None

@dataclass
class Worker:
    id: str
    name: str
    skills: List[str]

class SchedulingLogic:
    def __init__(self, hard_mode=False):
        self.tasks: Dict[str, Task] = {}
        self.workers: Dict[str, Worker] = {}
        self.hard_mode = hard_mode
        self.reset_game(hard_mode)

    def reset_game(self, hard_mode=None):
        if hard_mode is not None:
            self.hard_mode = hard_mode
        
        # Sample Data
        self.workers = {
            "W1": Worker("W1", "Alice", ["Frontend", "Design"]),
            "W2": Worker("W2", "Bob", ["Backend", "Database"]),
            "W3": Worker("W3", "Charlie", ["Backend", "Frontend"]),
            "W4": Worker("W4", "Diana", ["Testing", "Documentation"]),
        }

        # Base Projects
        self.tasks = {
            # Project Alpha: Diamond Structure (T1 -> [T2, T3] -> T4)
            "T1": Task("T1", "Project Discovery", "Project Alpha", 4, ["Design"]),
            "T2": Task("T2", "Backend Core", "Project Alpha", 6, ["Backend"], ["T1"]),
            "T3": Task("T3", "UI Layout", "Project Alpha", 5, ["Frontend"], ["T1"]),
            "T4": Task("T4", "Final Review", "Project Alpha", 4, ["Testing"], ["T2", "T3"]),

            # Project Beta: Sequential
            "T5": Task("T5", "DB Architecture", "Project Beta", 3, ["Database"]),
            "T6": Task("T6", "API Integration", "Project Beta", 8, ["Backend"], ["T5"]),
            "T7": Task("T7", "Beta Testing", "Project Beta", 4, ["Testing"], ["T6"]),

            # Project Gamma: Simple
            "T8": Task("T8", "Asset Design", "Project Gamma", 6, ["Design"]),
            "T9": Task("T9", "Documentation", "Project Gamma", 3, ["Documentation"], ["T8"]),
        }

        if self.hard_mode:
            # Add 3 more projects for "Hard Mode"
            hard_tasks = {
                # Project Delta: Parallel tasks
                "T10": Task("T10", "Market Research", "Project Delta", 5, ["Design"]),
                "T11": Task("T11", "Security Audit", "Project Delta", 6, ["Backend"]),
                "T12": Task("T12", "Legal Review", "Project Delta", 4, ["Documentation"]),

                # Project Epsilon: Long chain
                "T13": Task("T13", "Schema Design", "Project Epsilon", 4, ["Database"]),
                "T14": Task("T14", "CRUD API", "Project Epsilon", 5, ["Backend"]),
                "T15": Task("T15", "Admin UI", "Project Epsilon", 6, ["Frontend"], ["T14"]),
                "T16": Task("T16", "Deployment", "Project Epsilon", 3, ["Testing"], ["T15"]),

                # Project Zeta: Heavy Frontend
                "T17": Task("T17", "Wireframes", "Project Zeta", 4, ["Design"]),
                "T18": Task("T18", "Vue/React Setup", "Project Zeta", 5, ["Frontend"], ["T17"]),
                "T19": Task("T19", "Mobile Responsive", "Project Zeta", 6, ["Frontend"]),
            }
            self.tasks.update(hard_tasks)

    def assign_task(self, task_id: str, worker_id: str) -> bool:
        if task_id not in self.tasks or worker_id not in self.workers:
            return False
        
        task = self.tasks[task_id]
        worker = self.workers[worker_id]
        
        # Check if worker has required skill
        if not any(skill in worker.skills for skill in task.skills_required):
            return False
            
        task.assigned_worker = worker_id
        return True

    def deassign_task(self, task_id: str):
        if task_id in self.tasks:
            self.tasks[task_id].assigned_worker = None

    def calculate_schedule(self):
        """
        Calculates the start and end times for all assigned tasks based on worker availability 
        and precedence constraints.
        """
        # Clear previous calculation
        for t in self.tasks.values():
            t.start_time = None
            t.end_time = None
            
        assigned_tasks = [t for t in self.tasks.values() if t.assigned_worker]
        
        # Simple simulation to find timelines
        # worker_busy_until tracks when each worker is free
        worker_busy_until: Dict[str, int] = {w_id: 0 for w_id in self.workers}
        
        # We need to process tasks in topological order based on predecessors
        # but also restricted by worker availability.
        
        pending = list(assigned_tasks)
        completed = set()
        
        # Add tasks with no predecessors or whose predecessors are not in the assigned list (e.g. they won't be completed in this session if not assigned)
        # Actually, for the simulation to work, all tasks in a chain SHOULD be assigned.
        # If a predecessor is NOT assigned, we assume it's NOT DONE and subsequent tasks can't start.
        
        # To simplify: only calculate for assigned tasks. If a task has an unassigned predecessor, it can't start.
        
        iteration_limit = 100
        while pending and iteration_limit > 0:
            iteration_limit -= 1
            changed = False
            
            for task in pending[:]:
                # Check if all predecessors are completed
                preds_ready = True
                max_pred_finish = 0
                for pred_id in task.predecessors:
                    if pred_id in self.tasks:
                        p = self.tasks[pred_id]
                        if p.end_time is not None:
                            max_pred_finish = max(max_pred_finish, p.end_time)
                        else:
                            # Predecessor not assigned or not yet scheduled
                            preds_ready = False
                            break
                
                if preds_ready:
                    # Task can start at the later of:
                    # 1. When all predecessors are finished
                    # 2. When the assigned worker is free
                    start = max(max_pred_finish, worker_busy_until[task.assigned_worker])
                    task.start_time = start
                    task.end_time = start + task.duration
                    
                    worker_busy_until[task.assigned_worker] = task.end_time
                    completed.add(task.id)
                    pending.remove(task)
                    changed = True
            
            if not changed:
                break # Circular dependency or unassigned predecessors
                
        return max(worker_busy_until.values()) if worker_busy_until else 0

    def get_makespan(self) -> int:
        return self.calculate_schedule()

    def get_unassigned_tasks(self) -> List[Task]:
        return [t for t in self.tasks.values() if t.assigned_worker is None]

    def get_worker_assignments(self, worker_id: str) -> List[Task]:
        assigned = [t for t in self.tasks.values() if t.assigned_worker == worker_id]
        # Sort by start time if available
        return sorted(assigned, key=lambda x: x.start_time if x.start_time is not None else 999)

    def get_project_stats(self) -> Dict:
        projects = {}
        for t in self.tasks.values():
            if t.project not in projects:
                projects[t.project] = {"total": 0, "done": 0}
            projects[t.project]["total"] += 1
            if t.assigned_worker:
                projects[t.project]["done"] += 1
        return projects
