"""Excel import/export for Challenge mode (instance generation) and Scoring
mode (grading a filled-in submission).

Single unified file format — one "items" sheet carries BOTH the instance
definition and the solution columns, so nothing has to be typed twice:

    instance_id, bin_width, bin_height, item_id, width, height, profit,
    x, y, rotated

x/y/rotated start blank (Challenge mode's downloadable file) and get filled
in offline for whichever items the student decides to pack; a blank x/y
means "not placed" — no error, it just scores no profit for that item.

A "meta" sheet carries generation provenance (seed, difficulty, instance
count) plus a content signature (hash of the instance-defining columns)
that Scoring mode uses to detect whether the problem data itself — bin
size, item dimensions, profits — was altered after generation.
"""

import hashlib
import io
import random

import pandas as pd

from game_logic import generate_instance, rects_overlap

ITEM_COLUMNS = ["instance_id", "bin_width", "bin_height", "item_id", "width", "height", "profit"]
SOLUTION_COLUMNS = ["x", "y", "rotated"]
ALL_COLUMNS = ITEM_COLUMNS + SOLUTION_COLUMNS

FORMAT_NOTES = [
    "One row per item. instance_id groups items that belong to the same bin — "
    "there is one fixed bin per instance_id, sized bin_width x bin_height.",
    "instance_id, bin_width, bin_height, item_id, width, height, profit are the "
    "problem data — do not edit them. Scoring mode checks a signature computed "
    "over these columns and will flag the file if they don't match what was "
    "generated.",
    "Fill in x, y, and rotated only for the items you decide to pack. Leave x "
    "AND y both blank to mark an item as not placed — that's fine, it just "
    "scores no profit for that item. Filling in only one of x/y is invalid.",
    "Coordinates: x=0, y=0 is the bin's TOP-LEFT corner. x increases to the "
    "right, y increases DOWNWARD (screen/matrix convention).",
    "rotated: TRUE swaps the item's width and height (a w x h item occupies "
    "h x w once rotated). Leave blank or FALSE for no rotation.",
    "Placements must not overlap or go outside the bin. If any item in an "
    "instance does, that WHOLE instance scores 0 profit, even for the items "
    "that were placed validly.",
    "Upload this same file, filled in, to Scoring mode to get graded.",
]


def generate_instances(seed: int, difficulty: float, n_instances: int) -> list:
    """Reproducible from (seed, difficulty, n_instances) alone."""
    rng = random.Random(seed)
    return [generate_instance(i + 1, difficulty, rng) for i in range(n_instances)]


def _instance_rows(instances: list) -> list:
    return [
        {
            "instance_id": inst.id, "bin_width": inst.bin_w, "bin_height": inst.bin_h,
            "item_id": it.id, "width": it.w, "height": it.h, "profit": it.profit,
        }
        for inst in instances
        for it in inst.items
    ]


def _signature(rows) -> str:
    """Order-independent hash over the ground-truth (non-solution) columns —
    used to detect if instance data was edited after generation."""
    canon = sorted(
        (
            int(r["instance_id"]), int(r["bin_width"]), int(r["bin_height"]),
            int(r["item_id"]), int(r["width"]), int(r["height"]), int(r["profit"]),
        )
        for r in rows
    )
    blob = "|".join(",".join(map(str, row)) for row in canon)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def instances_workbook_bytes(instances: list, seed, difficulty, n_instances: int, placements_by_instance: dict = None) -> bytes:
    """Build the single combined workbook.

    If placements_by_instance ({instance_id: list[PlacedItem]}) is given,
    x/y/rotated are filled in from it (Game mode's export of what the
    student actually did); otherwise they're left blank (Challenge mode's
    downloadable file, ready to be filled in offline).
    """
    rows = _instance_rows(instances)
    signature = _signature(rows)

    placed_lookup = {}
    for instance_id, placements in (placements_by_instance or {}).items():
        for p in placements:
            placed_lookup[(instance_id, p.item.id)] = (p.x, p.y, p.rotated)

    for row in rows:
        x, y, rotated = placed_lookup.get((row["instance_id"], row["item_id"]), (None, None, None))
        row["x"], row["y"], row["rotated"] = x, y, rotated

    items_df = pd.DataFrame(rows, columns=ALL_COLUMNS)
    meta_df = pd.DataFrame([{
        "seed": seed, "difficulty": difficulty, "num_instances": n_instances, "signature": signature,
    }])
    notes_df = pd.DataFrame({"Format notes": FORMAT_NOTES})

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        items_df.to_excel(writer, sheet_name="items", index=False)
        meta_df.to_excel(writer, sheet_name="meta", index=False)
        notes_df.to_excel(writer, sheet_name="notes", index=False)
        writer.sheets["notes"].column_dimensions["A"].width = 100
    return buf.getvalue()


def parse_submission_workbook(file):
    """Parse and structurally validate a submission file.

    Returns (items_df, integrity) where integrity is
    {"checked": bool, "ok": bool, "message": str} describing the result of
    comparing against the file's own recorded signature (if any).

    Raises ValueError (with a specific, user-facing message) for structural
    problems that make the file impossible to score.
    """
    xls = pd.ExcelFile(file)

    if "items" in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name="items")
    else:
        df = pd.read_excel(xls, sheet_name=xls.sheet_names[0])

    missing = set(ITEM_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"File is missing required column(s): {sorted(missing)}")
    for col in SOLUTION_COLUMNS:
        if col not in df.columns:
            df[col] = None

    df = df.dropna(subset=["instance_id", "item_id"]).copy()
    if df.empty:
        raise ValueError("File has no item rows.")

    for col in ["instance_id", "bin_width", "bin_height", "item_id", "width", "height", "profit"]:
        if df[col].isna().any():
            raise ValueError(f"Column '{col}' has missing values — every item row needs it filled in.")
        df[col] = df[col].astype(int)

    dup_mask = df.duplicated(subset=["instance_id", "item_id"], keep=False)
    if dup_mask.any():
        bad = df.loc[dup_mask, ["instance_id", "item_id"]].drop_duplicates()
        pairs = ", ".join(f"instance {r.instance_id}/item {r.item_id}" for r in bad.itertuples())
        raise ValueError(f"Duplicate item rows found: {pairs}")

    bin_nunique = df.groupby("instance_id")[["bin_width", "bin_height"]].nunique()
    inconsistent = bin_nunique[(bin_nunique["bin_width"] > 1) | (bin_nunique["bin_height"] > 1)]
    if len(inconsistent):
        raise ValueError(f"Inconsistent bin_width/bin_height within instance(s): {list(inconsistent.index)}")

    df["rotated"] = df["rotated"].apply(lambda v: bool(v) if pd.notna(v) else False)
    x_filled = df["x"].notna()
    y_filled = df["y"].notna()
    # A row with neither x nor y filled in is a normal "not placed" item —
    # only one of the two filled in is a data-integrity problem, since a
    # position isn't meaningful without both coordinates.
    if (x_filled != y_filled).any():
        bad = df.loc[x_filled != y_filled, ["instance_id", "item_id"]]
        pairs = ", ".join(f"instance {r.instance_id}/item {r.item_id}" for r in bad.itertuples())
        raise ValueError(
            f"Incomplete placement data (only one of x/y filled in) for: {pairs}. "
            "Fill in both x and y, or leave both blank to mark the item as not placed."
        )
    df.loc[x_filled, "x"] = df.loc[x_filled, "x"].astype(int)
    df.loc[y_filled, "y"] = df.loc[y_filled, "y"].astype(int)

    integrity = {
        "checked": False, "ok": True,
        "message": "No signature found in this file (no 'meta' sheet) — integrity not verified.",
    }
    if "meta" in xls.sheet_names:
        meta_df = pd.read_excel(xls, sheet_name="meta")
        if "signature" in meta_df.columns and len(meta_df):
            stored = str(meta_df["signature"].iloc[0])
            actual = _signature(df[ITEM_COLUMNS].to_dict("records"))
            integrity["checked"] = True
            if actual == stored:
                integrity["ok"] = True
                integrity["message"] = "Instance data matches the signature recorded at generation time."
            else:
                integrity["ok"] = False
                integrity["message"] = (
                    "Instance data (bin size, item dimensions, or profits) does not match the "
                    "signature recorded when this file was generated — it may have been edited."
                )

    return df, integrity


def score_submission(df: pd.DataFrame):
    """Grade a submission. Returns (results_df, summary, reconstructed) where
    reconstructed maps instance_id -> layout details usable for plotting."""
    results = []
    reconstructed = {}

    for instance_id, group in df.groupby("instance_id"):
        bin_w = int(group["bin_width"].iloc[0])
        bin_h = int(group["bin_height"].iloc[0])
        items_by_id = {
            int(r.item_id): (int(r.width), int(r.height), int(r.profit))
            for r in group.itertuples()
        }
        potential_profit = sum(p for _, _, p in items_by_id.values())

        placed = []
        for r in group.itertuples():
            if pd.isna(r.x) or pd.isna(r.y):
                continue
            w0, h0, profit = items_by_id[int(r.item_id)]
            rotated = bool(r.rotated)
            w, h = (h0, w0) if rotated else (w0, h0)
            placed.append({
                "item_id": int(r.item_id), "x": int(r.x), "y": int(r.y),
                "w": w, "h": h, "profit": profit, "rotated": rotated,
            })

        feasible = True
        error = None
        for p in placed:
            if p["x"] < 0 or p["y"] < 0 or p["x"] + p["w"] > bin_w or p["y"] + p["h"] > bin_h:
                feasible = False
                error = f"item {p['item_id']} is out of bounds"
                break
        if feasible:
            for i in range(len(placed)):
                for j in range(i + 1, len(placed)):
                    a, b = placed[i], placed[j]
                    if rects_overlap(a["x"], a["y"], a["w"], a["h"], b["x"], b["y"], b["w"], b["h"]):
                        feasible = False
                        error = f"items {a['item_id']} and {b['item_id']} overlap"
                        break
                if not feasible:
                    break

        profit = sum(p["profit"] for p in placed) if feasible else 0
        packed_area = sum(p["w"] * p["h"] for p in placed)
        utilization = min(100.0, 100.0 * packed_area / (bin_w * bin_h)) if bin_w * bin_h else 0.0

        results.append({
            "instance_id": instance_id, "feasible": feasible, "error": error or "",
            "profit": profit, "potential_profit": potential_profit,
            "utilization": utilization, "items_placed": len(placed), "items_total": len(items_by_id),
        })
        reconstructed[instance_id] = {
            "bin_w": bin_w, "bin_h": bin_h, "placed": placed,
            "items_by_id": items_by_id, "feasible": feasible,
        }

    results_df = pd.DataFrame(results)
    summary = {
        "total_score": int(results_df["profit"].sum()) if len(results_df) else 0,
        "total_potential": int(results_df["potential_profit"].sum()) if len(results_df) else 0,
        "avg_utilization": float(results_df["utilization"].mean()) if len(results_df) else 0.0,
        "n_instances": len(results_df),
        "n_feasible": int(results_df["feasible"].sum()) if len(results_df) else 0,
    }
    return results_df, summary, reconstructed
