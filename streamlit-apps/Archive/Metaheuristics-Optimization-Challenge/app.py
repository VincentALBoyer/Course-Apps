import os
# Fix PermissionError: [Errno 13] by unsetting the system-level SSLKEYLOGFILE variable
os.environ.pop('SSLKEYLOGFILE', None)

import streamlit as st
import time
import pandas as pd
import math
import logging
import sys
from instances import KNAPSACK_INSTANCES, PMEDIAN_INSTANCES
from solver_utils import calculate_knapsack_stats, calculate_p_median_stats, calculate_potential_total_distances

# --- LOGGING CONFIG ---
# Explicitly direct logs to stdout to avoid PermissionError on virtual volumes
logging.basicConfig(stream=sys.stdout, level=logging.INFO, force=True)

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="Metaheuristics Challenge",
    page_icon="🏆",
    layout="wide",
)

# --- CUSTOM CSS ---
def local_css():
    st.markdown(
        """
        <style>
        .stButton>button {
            width: 100%;
            border-radius: 8px;
            height: 3em;
            transition: all 0.3s ease;
        }
        .stButton>button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }
        .main {
            background-color: transparent;
        }
        [data-testid="stMetricValue"] {
            font-size: 24px;
        }
        .stat-card {
            background-color: rgba(128, 128, 128, 0.1);
            padding: 1rem;
            border-radius: 12px;
            border: 1px solid rgba(128, 128, 128, 0.2);
        }
        .table-header {
            font-weight: bold;
            border-bottom: 2px solid rgba(128, 128, 128, 0.3);
            padding: 10px 0;
            margin-bottom: 10px;
        }
        .table-row {
            padding: 8px 0;
            border-bottom: 1px solid rgba(128, 128, 128, 0.1);
        }
        .table-row:hover {
            background-color: rgba(128, 128, 128, 0.05);
        }
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        </style>
        """,
        unsafe_allow_html=True,
    )

local_css()

# --- STATE MANAGEMENT ---
if "phase" not in st.session_state:
    st.session_state.phase = "setup"  # setup, game, final
if "problem_type" not in st.session_state:
    st.session_state.problem_type = "knapsack"
if "mode" not in st.session_state:
    st.session_state.mode = "easy"
if "instance_index" not in st.session_state:
    st.session_state.instance_index = 0
if "results" not in st.session_state:
    st.session_state.results = []  # list of (fitness, time)
if "start_time" not in st.session_state:
    st.session_state.start_time = 0
if "current_selection" not in st.session_state:
    st.session_state.current_selection = set()

# Sorting state
if "ks_sort_col" not in st.session_state:
    st.session_state.ks_sort_col = "id"
if "ks_sort_asc" not in st.session_state:
    st.session_state.ks_sort_asc = True
if "pm_sort_col" not in st.session_state:
    st.session_state.pm_sort_col = "Facility ID"
if "pm_sort_asc" not in st.session_state:
    st.session_state.pm_sort_asc = True

# UI Reset Counters
if "ks_reset_ctr" not in st.session_state:
    st.session_state.ks_reset_ctr = 0
if "pm_reset_ctr" not in st.session_state:
    st.session_state.pm_reset_ctr = 0

# --- HELPERS ---
def start_challenge():
    st.session_state.phase = "game"
    st.session_state.instance_index = 0
    st.session_state.results = []
    st.session_state.start_time = time.time()
    st.session_state.current_selection = set()

def next_instance(fitness, duration):
    st.session_state.results.append({"fitness": fitness, "time": duration})
    if st.session_state.instance_index < 9:
        st.session_state.instance_index += 1
        st.session_state.current_selection = set()
    else:
        st.session_state.phase = "final"

def reset():
    st.session_state.phase = "setup"

# --- UI: SETUP ---
if st.session_state.phase == "setup":
    st.title("🏆 Metaheuristics Optimization Challenge")
    st.markdown("### Prepare for the race! Solve 10 instances as fast as possible.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.problem_type = st.selectbox(
            "Select Problem Type",
            ["knapsack", "p-median"],
            format_func=lambda x: "Knapsack Problem" if x == "knapsack" else "p-Median Problem"
        )
    with col2:
        st.session_state.mode = st.radio(
            "Select Difficulty",
            ["easy", "hard"],
            help="Easy: Shows additional metrics (ratios/assignment costs). Hard: Raw data only."
        )
    
    st.write("---")
    if st.button("🚀 START CHALLENGE"):
        start_challenge()
        st.rerun()

# --- UI: GAME ---
elif st.session_state.phase == "game":
    idx = st.session_state.instance_index
    instances = KNAPSACK_INSTANCES if st.session_state.problem_type == "knapsack" else PMEDIAN_INSTANCES
    instance = instances[idx]
    
    # Progress Header
    cols = st.columns([2, 1, 1])
    with cols[0]:
        st.subheader(f"Instance {idx + 1} / 10")
    with cols[1]:
        elapsed = time.time() - st.session_state.start_time
        st.metric("Total Time", f"{elapsed:.1f}s")
    with cols[2]:
        progress = (idx) / 10
        st.progress(progress)
    
    st.write("---")

    if st.session_state.problem_type == "knapsack":
        items = instance["items"]
        capacity = instance["capacity"]
        
        # Prepare data for display
        df_items = pd.DataFrame(items)
        df_items["Selected"] = [item["id"] in st.session_state.current_selection for item in items]
        # Reorder columns for better UX
        cols_to_show = ["Selected", "id", "v", "w"]
        if st.session_state.mode == "easy":
            df_items["ratio (v/w)"] = (df_items["v"] / df_items["w"]).round(2)
            cols_to_show.append("ratio (v/w)")
        
        stats = calculate_knapsack_stats(st.session_state.current_selection, items, capacity)
        
        # Dashboard metrics moved to top
        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("Current Value (Fitness)", stats["value"])
        with m2:
            st.metric("Used Capacity", f"{stats['weight']} / {capacity}")
        with m3:
            st.metric("Feasibility", "✅ OK" if stats["is_feasible"] else "❌ OVERLOAD")

        if not stats["is_feasible"]:
            st.warning("⚠️ Capacity exceeded! Please unselect items to proceed.")

        st.markdown("#### Select Items")
        
        # Persistent Sorting Controls
        ks_cols = ["id", "v", "w"]
        if st.session_state.mode == "easy":
            ks_cols.append("ratio (v/w)")
        
        sort_col1, sort_col2 = st.columns([3, 2])
        with sort_col1:
            st.session_state.ks_sort_col = st.selectbox(
                "Sort by", ks_cols, 
                index=ks_cols.index(st.session_state.ks_sort_col) if st.session_state.ks_sort_col in ks_cols else 0,
                key="ks_sort_select"
            )
        with sort_col2:
            st.session_state.ks_sort_asc = st.radio(
                "Order", ["Asc", "Desc"], 
                index=0 if st.session_state.ks_sort_asc else 1,
                horizontal=True,
                key="ks_sort_order"
            ) == "Asc"

        df_items = df_items.sort_values(by=st.session_state.ks_sort_col, ascending=st.session_state.ks_sort_asc)
        
        # Manual Table Header
        header_cols = st.columns([1, 1, 1, 1, 2] if st.session_state.mode == "easy" else [1, 1, 1, 1])
        with header_cols[0]: st.markdown("<div class='table-header'>Select</div>", unsafe_allow_html=True)
        with header_cols[1]: st.markdown("<div class='table-header'>ID</div>", unsafe_allow_html=True)
        with header_cols[2]: st.markdown("<div class='table-header'>Value</div>", unsafe_allow_html=True)
        with header_cols[3]: st.markdown("<div class='table-header'>Weight</div>", unsafe_allow_html=True)
        if st.session_state.mode == "easy":
            with header_cols[4]: st.markdown("<div class='table-header'>Ratio</div>", unsafe_allow_html=True)
            
        current_weight = sum(item["w"] for item in items if item["id"] in st.session_state.current_selection)
        
        # Manual Table Rows
        for _, row in df_items.iterrows():
            item_id = row["id"]
            is_selected = item_id in st.session_state.current_selection
            can_fit = is_selected or (current_weight + row["w"] <= capacity)
            
            row_cols = st.columns([1, 1, 1, 1, 2] if st.session_state.mode == "easy" else [1, 1, 1, 1])
            with row_cols[0]:
                checked = st.checkbox(
                    " ", key=f"ks_check_{idx}_{item_id}", value=is_selected, disabled=not can_fit, label_visibility="collapsed"
                )
                if checked != is_selected:
                    if checked:
                        st.session_state.current_selection.add(item_id)
                    else:
                        st.session_state.current_selection.remove(item_id)
                    st.rerun()
                    
            with row_cols[1]: st.markdown(f"<div class='table-row'>{item_id}</div>", unsafe_allow_html=True)
            with row_cols[2]: st.markdown(f"<div class='table-row'>{row['v']}</div>", unsafe_allow_html=True)
            with row_cols[3]: st.markdown(f"<div class='table-row'>{row['w']}</div>", unsafe_allow_html=True)
            if st.session_state.mode == "easy":
                with row_cols[4]: st.markdown(f"<div class='table-row'>{row['ratio (v/w)']}</div>", unsafe_allow_html=True)

        st.write("---")
        if st.button("NEXT INSTANCE", type="primary", disabled=not stats["is_feasible"]):
            next_instance(stats["value"], elapsed)
            st.rerun()

    elif st.session_state.problem_type == "p-median":
        cities = instance["cities"]
        p = instance["p"]
        stats = calculate_p_median_stats(st.session_state.current_selection, cities)
        potential_stats = calculate_potential_total_distances(st.session_state.current_selection, cities)
        
        # Dashboard stats
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Distance (Fitness)", f"{stats['total_distance']:.2f}")
        c2.metric("Facilities", f"{len(st.session_state.current_selection)} / {p}")
        
        is_feasible = len(st.session_state.current_selection) == p
        status_msg = "✅ OK" if is_feasible else f"Select {p} facilities"
        c3.metric("Feasibility", status_msg)

        if len(st.session_state.current_selection) > p:
            st.error(f"⚠️ Too many facilities! You must select EXACTLY {p}.")
        elif len(st.session_state.current_selection) < p:
            st.info(f"ℹ️ Select {p - len(st.session_state.current_selection)} more facilities.")

        st.markdown(f"#### Distance Matrix & Selection (Select {p} Facilities)")

        # Persistent Sorting Controls
        pm_cols = ["Facility ID", "Potential Total Dist"]
        sort_col1, sort_col2 = st.columns([3, 2])
        with sort_col1:
            st.session_state.pm_sort_col = st.selectbox(
                "Sort by", pm_cols, 
                index=pm_cols.index(st.session_state.pm_sort_col) if st.session_state.pm_sort_col in pm_cols else 0,
                key="pm_sort_select"
            )
        with sort_col2:
            st.session_state.pm_sort_asc = st.radio(
                "Order", ["Asc", "Desc"], 
                index=0 if st.session_state.pm_sort_asc else 1,
                horizontal=True,
                key="pm_sort_order"
            ) == "Asc"

        st.markdown(f"#### Selection & Distance Matrix (Select {p} Facilities)")

        # Create Distance Matrix DataFrame
        matrix_data = []
        for fac_city in cities:
            row = {
                "Selected": fac_city["id"] in st.session_state.current_selection,
                "Facility ID": fac_city["id"],
            }
            for cust_city in cities:
                dist = math.ceil(math.sqrt((fac_city["x"] - cust_city["x"])**2 + (fac_city["y"] - cust_city["y"])**2))
                is_assigned = stats["assignments"].get(cust_city["id"]) == fac_city["id"]
                val_str = f"{dist}"
                if is_assigned: val_str += " [A]"
                row[f"C{cust_city['id']}"] = val_str
            
            row["Potential Total Dist"] = round(potential_stats.get(fac_city["id"], 0), 1)
            matrix_data.append(row)

        df_matrix = pd.DataFrame(matrix_data)
        df_matrix = df_matrix.sort_values(by=st.session_state.pm_sort_col, ascending=st.session_state.pm_sort_asc)

        # Unified Matrix View (Manual Layout)
        cust_cols = [col for col in df_matrix.columns if col.startswith("C")]
        cust_cols.sort(key=lambda x: int(x[1:]))
        
        # Header setup
        # Weights: Sel(0.5), ID(0.5), PotCost(1), then Customers(0.6 each)
        col_weights = [0.5, 0.5, 1.0] + [0.6] * len(cust_cols)
        
        # Table Header
        h_cols = st.columns(col_weights)
        with h_cols[0]: st.markdown("<div class='table-header'>Sel</div>", unsafe_allow_html=True)
        with h_cols[1]: st.markdown("<div class='table-header'>ID</div>", unsafe_allow_html=True)
        with h_cols[2]: st.markdown("<div class='table-header'>Pot. Cost</div>", unsafe_allow_html=True)
        for i, cname in enumerate(cust_cols):
            with h_cols[3+i]: st.markdown(f"<div class='table-header'>{cname}</div>", unsafe_allow_html=True)

        # Table Rows
        for _, row in df_matrix.iterrows():
            fac_id = int(row["Facility ID"])
            is_sel = fac_id in st.session_state.current_selection
            can_sel = is_sel or (len(st.session_state.current_selection) < p)
            
            r_cols = st.columns(col_weights)
            with r_cols[0]:
                checked = st.checkbox(
                    " ", key=f"pm_check_{idx}_{fac_id}", value=is_sel, disabled=not can_sel, label_visibility="collapsed"
                )
                if checked != is_sel:
                    if checked: st.session_state.current_selection.add(fac_id)
                    else: st.session_state.current_selection.remove(fac_id)
                    st.rerun()
            
            with r_cols[1]: st.markdown(f"<div class='table-row'>{fac_id}</div>", unsafe_allow_html=True)
            with r_cols[2]: st.markdown(f"<div class='table-row'>{row['Potential Total Dist']}</div>", unsafe_allow_html=True)
            for i, cname in enumerate(cust_cols):
                with h_cols[3+i]: # Placeholder to align, but we need r_cols for the row
                    pass
                with r_cols[3+i]:
                    st.markdown(f"<div class='table-row'>{row[cname]}</div>", unsafe_allow_html=True)

        st.write("---")
        if st.button("NEXT INSTANCE", type="primary", disabled=not is_feasible):
            next_instance(stats["total_distance"], elapsed)
            st.rerun()

# --- UI: FINAL ---
elif st.session_state.phase == "final":
    st.title("🏁 Challenge Completed!")
    
    total_time = time.time() - st.session_state.start_time
    # Note: total_time here is accurate because game runs continuously
    
    avg_fitness = sum(r["fitness"] for r in st.session_state.results) / 10
    
    c1, c2 = st.columns(2)
    c1.metric("Average Fitness", f"{avg_fitness:.2f}")
    c2.metric("Total Time", f"{total_time:.1f}s")
    
    st.write("---")
    st.markdown("#### Detailed Results")
    st.table(pd.DataFrame(st.session_state.results))
    
    if st.button("RESTART"):
        reset()
        st.rerun()
