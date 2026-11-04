# =============================================================================
# Page 03 — Inventory & Warehouse Management
# =============================================================================
import streamlit as st
import pandas as pd
import plotly.express as px

if "sim_state" not in st.session_state:
    st.warning("Simulation state not initialized. Please go to the Home page first.")
    st.stop()

state = st.session_state.sim_state

st.html("""
<div class='page-header'>
    <h2>📦 Inventory & Warehouse</h2>
    <p>Real-time stock levels, material movements, ABC analysis, and reorder alerts</p>
</div>
""")

# ── KPIs ──────────────────────────────────────────────────────────────────────
total_raw_val = sum(state.stock_materials.get(m, 0) * mat.cost for m, mat in state.materials.items())
total_fg_val = sum(state.stock_finished.get(p, 0) * prod.price for p, prod in state.products.items())
low_stock = sum(1 for m, mat in state.materials.items()
                if state.stock_materials.get(m, 0) <= mat.reorder_point)

k1, k2, k3, k4 = st.columns(4)
k1.metric("Raw Material Value", f"${total_raw_val:,.0f}")
k2.metric("Finished Goods Value", f"${total_fg_val:,.0f}")
k3.metric("Total Inventory Value", f"${total_raw_val + total_fg_val:,.0f}")
k4.metric("Low Stock Alerts", low_stock, delta="items below reorder point" if low_stock > 0 else None,
          delta_color="inverse" if low_stock > 0 else "normal")

st.divider()

tab_raw, tab_fg, tab_mvt = st.tabs(["🧱 Raw Materials", "🚲 Finished Goods", "📋 Movement Log"])

# ── Raw Materials ─────────────────────────────────────────────────────────────
with tab_raw:
    rows = []
    for mid, mat in state.materials.items():
        qty = state.stock_materials.get(mid, 0)
        inbound = sum(po.qty for po in state.purchase_orders
                      if po.material_id == mid and po.status == "OnOrder")
        net_available = qty + inbound
        usage_7d = sum(
            sum(prod.bom.get(mid, 0) * wo.qty / max(1, (state.current_day - wo.day_started))
                for wo in state.work_orders if wo.status == "Completed")
            for prod in state.products.values()
        )
        # Estimate avg daily demand (from previous 7 days sales)
        shipped_7d = sum(so.qty for so in state.sales_orders 
                         if so.product_id in state.products and so.status == "Shipped" and (state.current_day - so.shipped_day) <= 7)
        avg_daily_demand = max(0.1, shipped_7d / 7.0)
        # For simplicity, use a heuristic for materials: proportional to product demand
        mat_usage_est = avg_daily_demand * 2 # Heuristic factor
        days_stock = qty / mat_usage_est if mat_usage_est > 0 else 99

        status = "🔴 CRITICAL" if qty == 0 else (
            "🟠 LOW" if qty <= mat.reorder_point else (
                "🟡 OK" if qty <= mat.reorder_point * 2 else "🟢 Good"
            ))
        rows.append({
            "ABC": mat.category,
            "Material": mat.name,
            "On Hand": qty,
            "Inbound POs": inbound,
            "Net Available": net_available,
            "Days of Stock": f"{days_stock:.1f}",
            "Reorder Point": mat.reorder_point,
            "Unit Cost": f"${mat.cost:.2f}",
            "Stock Value": f"${qty * mat.cost:,.0f}",
            "Status": status,
        })
    df = pd.DataFrame(rows).sort_values(["ABC", "Material"])
    st.dataframe(df, use_container_width=True, hide_index=True,
                 column_config={
                     "On Hand": st.column_config.NumberColumn(format="%d"),
                     "ABC": st.column_config.TextColumn(width="small"),
                 })

    # ABC Treemap
    st.html("<div class='section-title'>📊 ABC Stock Value Analysis</div>")
    abc_data = [{"Material": mat.name, "Value": state.stock_materials.get(mid, 0) * mat.cost,
                 "ABC": mat.category}
                for mid, mat in state.materials.items()]
    fig = px.treemap(pd.DataFrame(abc_data), path=["ABC", "Material"], values="Value",
                     color="ABC", color_discrete_map={"A": "#1A56DB", "B": "#7E3AF2", "C": "#94A3B8"},
                     title="Inventory Value by ABC Category")
    fig.update_layout(height=280, margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig, use_container_width=True)

# ── Finished Goods ────────────────────────────────────────────────────────────
with tab_fg:
    fg_rows = []
    for pid, prod in state.products.items():
        qty = state.stock_finished.get(pid, 0)
        open_demand = sum(so.qty for so in state.sales_orders
                          if so.product_id == pid and so.status == "Open")
        wip_qty = sum(wo.qty for wo in state.work_orders
                      if wo.product_id == pid and wo.status == "InProgress")
        coverage = qty - open_demand
        fg_rows.append({
            "Product": prod.name, "Category": prod.category,
            "In Stock": qty, "Open Demand": open_demand,
            "WIP": wip_qty, "Net Coverage": coverage,
            "Status": "✅ Covered" if coverage >= 0 else f"⚠️ Short {-coverage}",
            "Sales Price": f"${prod.price:.0f}",
            "Stock Value": f"${qty * prod.price:,.0f}",
        })
    st.dataframe(pd.DataFrame(fg_rows), use_container_width=True, hide_index=True)

# ── Movement Log ──────────────────────────────────────────────────────────────
with tab_mvt:
    if state.inventory_movements:
        mvt_data = []
        for m in sorted(state.inventory_movements, key=lambda x: x.day, reverse=True)[:50]:
            mat_name = state.materials[m.material_id].name if m.material_id and m.material_id in state.materials else "—"
            prod_name = state.products[m.product_id].name if m.product_id and m.product_id in state.products else "—"
            mvt_data.append({
                "Day": m.day, "Type": m.movement_type,
                "Material": mat_name, "Product": prod_name,
                "Qty": m.qty, "Ref": m.ref_id, "Description": m.description,
            })
        st.dataframe(pd.DataFrame(mvt_data), use_container_width=True, hide_index=True)
    else:
        st.info("No inventory movements recorded yet.")
