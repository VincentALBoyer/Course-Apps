# Project Scheduling Simulation

> ⚠️ **No longer maintained.** This app still works, but it won't receive fixes or updates. An identical copy is kept in [`../Archive/Project_Scheduling_App`](../Archive/Project_Scheduling_App).

An educational Streamlit application designed to help students understand the complexities of project scheduling, resource management, and the Critical Path Method (CPM).

## Features
- **Multiple Projects**: Manage tasks across "Project Alpha", "Project Beta", and shared tasks.
- **Precedence Constraints**: Tasks are linked; some cannot start until others are finished.
- **Skill-Based Assignment**: Workers have specific skills (Frontend, Backend, etc.). Tasks can only be assigned to qualified personnel.
- **Dynamic Scheduling**: The app automatically calculates the earliest possible start and finish times for every task.
- **Gantt Chart Visualization**: Real-time feedback on the team's load and project timeline.
- **Goal-Oriented**: Students strive to minimize the total makespan (completion time).

## Problem Description

The simulation presents a resource-constrained project scheduling problem (RCPSP) where you manage a team of 4 specialists to complete 3 different projects.

### 👥 The Team (Resource Constraints)
| Worker | Skills |
| :--- | :--- |
| **Alice** | Frontend, Design |
| **Bob** | Backend, Database |
| **Charlie** | Backend, Frontend |
| **Diana** | Testing, Documentation |

### 📋 The Projects (Tasks & Precedence)

#### Project Alpha: Enterprise Portal
| ID | Task Name | Duration (Hrs) | Required Skill | Predecessors |
| :--- | :--- | :--- | :--- | :--- |
| **T1** | Project Discovery | 4 | Design | - |
| **T2** | Backend Core | 6 | Backend | T1 |
| **T3** | UI Layout | 5 | Frontend | T1 |
| **T4** | Final Review | 4 | Testing | T2, T3 |

#### Project Beta: API Suite
| ID | Task Name | Duration (Hrs) | Required Skill | Predecessors |
| :--- | :--- | :--- | :--- | :--- |
| **T5** | DB Architecture | 3 | Database | - |
| **T6** | API Integration | 8 | Backend | T5 |
| **T7** | Beta Testing | 4 | Testing | T6 |

#### Project Gamma: Internal Tools
| ID | Task Name | Duration (Hrs) | Required Skill | Predecessors |
| :--- | :--- | :--- | :--- | :--- |
| **T8** | Asset Design | 6 | Design | - |
| **T9** | Documentation | 3 | Documentation | T8 |

### 🎯 Your Goal
Your objective is to assign the right workers to the right tasks while respecting the **precedence constraints** and **skill requirements**. Try to find the optimal assignment that results in the shortest possible total completion time (**makespan**).

## How to Run
From the repo root:
```bash
streamlit run streamlit-apps/Project_Scheduling_App/app.py
```

## Setup
Ensure you have the following installed:
- streamlit
- pandas
- plotly
- dataclasses (Python 3.7+)
