"""Generates the downloadable end-of-run PDF performance report students
submit as grading evidence. Pure derived output - reads GameState, writes
nothing back."""

from datetime import datetime

from fpdf import FPDF
from fpdf.fonts import FontFace

from game_engine import GameState, get_kpis, get_pnl_statement, get_supplier_scorecard, get_customer_scorecard

_PAGE_W = 190  # usable width in mm on an A4 page with default margins


def _money(value: float) -> str:
    return f"-${abs(value):,.0f}" if value < 0 else f"${value:,.0f}"


def _section_title(pdf: FPDF, title: str) -> None:
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(20, 20, 20)
    pdf.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(200, 200, 200)
    pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + _PAGE_W, pdf.get_y())
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(0, 0, 0)


def _kv_table(pdf: FPDF, rows: list[tuple[str, str]]) -> None:
    with pdf.table(borders_layout="NONE", col_widths=(60, 40), text_align=("LEFT", "RIGHT"), line_height=6) as table:
        for label, value in rows:
            row = table.row()
            row.cell(label)
            row.cell(value)


def _data_table(pdf: FPDF, headers: list[str], rows: list[list[str]], col_widths=None) -> None:
    with pdf.table(headings_style=FontFace(emphasis="BOLD"), col_widths=col_widths, line_height=5.5, text_align="CENTER") as table:
        row = table.row()
        for h in headers:
            row.cell(h)
        for data_row in rows:
            row = table.row()
            for cell in data_row:
                row.cell(str(cell))


def build_pdf(state: GameState, student_name: str, student_id: str) -> bytes:
    kpis = get_kpis(state)
    pnl = get_pnl_statement(state)

    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, "ERP Sim - Performance Report", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(90, 90, 90)
    pdf.cell(0, 6, "Global Gadgets Inc. - Simulated Fulfillment Operations", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)

    _kv_table(pdf, [
        ("Student", student_name),
        ("Student ID", student_id),
        ("Days completed", f"{state.current_day} / {state.max_days}"),
        ("Report generated", datetime.now().strftime("%Y-%m-%d %H:%M")),
    ])

    _section_title(pdf, "Final Results")
    _kv_table(pdf, [
        ("Net Profit", _money(kpis["profit"])),
        ("Ending Cash", _money(kpis["cash"])),
        ("Units Sold", f"{kpis['units_sold']}"),
        ("Sales Order Fill Rate", f"{kpis['fill_rate']:.0f}%"),
        ("Ending On-Hand Inventory", f"{kpis['inventory']}"),
    ])

    _section_title(pdf, "Profit & Loss Statement")
    _kv_table(pdf, [
        ("Revenue", _money(pnl["revenue"])),
        ("Cost of Goods Sold", _money(-pnl["cogs"])),
        ("Gross Margin", _money(pnl["gross_margin"])),
        ("Holding Costs", _money(-pnl["holding_costs"])),
        ("Late Delivery Penalties", _money(-pnl["penalties"])),
        ("Net Profit", _money(pnl["net_profit"])),
    ])

    _section_title(pdf, "Supplier Scorecard (SRM)")
    scard = get_supplier_scorecard(state)
    _data_table(
        pdf,
        ["Supplier", "Orders", "Units", "Spend ($)", "Avg Lead Time (d)"],
        [[
            r["supplier"], r["orders"], r["units_purchased"],
            f"{r['total_spend']:,.0f}",
            f"{r['avg_lead_time_days']:.1f}" if r["avg_lead_time_days"] is not None else "-",
        ] for r in scard],
        col_widths=(55, 25, 25, 40, 45),
    )

    _section_title(pdf, "Customer Scorecard (CRM)")
    ccard = get_customer_scorecard(state)
    _data_table(
        pdf,
        ["Customer", "Orders", "Units", "Revenue ($)", "On-Time (%)"],
        [[
            r["customer"], r["orders"], r["units_ordered"],
            f"{r['revenue']:,.0f}",
            f"{r['on_time_pct']:.0f}" if r["on_time_pct"] is not None else "-",
        ] for r in ccard],
        col_widths=(55, 25, 25, 40, 45),
    )

    _section_title(pdf, "Day-by-Day History")
    _data_table(
        pdf,
        ["Day", "Cash ($)", "Profit ($)", "Inventory", "Open SOs", "Inbound"],
        [[
            h["day"], f"{h['cash']:,.0f}", f"{h['profit']:,.0f}",
            h["inventory"], h["orders_pending"], h["incoming_qty"],
        ] for h in state.history],
        col_widths=(20, 35, 35, 30, 30, 30),
    )

    return bytes(pdf.output())
