/* Excel import/export for Challenge mode (instance generation) and Scoring
 * mode (grading a filled-in submission). Port of
 * Greedy_BinPacking_App/excel_io.py — same file format, same signature, same
 * validation messages, so files move freely between this page and the
 * Streamlit app.
 *
 * One "items" sheet carries both the instance definition and the solution
 * columns:  instance_id, bin_width, bin_height, item_id, width, height,
 * profit, x, y, rotated. A "meta" sheet carries seed / difficulty / count
 * and a SHA-256 signature of the instance-defining columns.
 *
 * Requires the SheetJS global `XLSX`.
 */
(function () {
  "use strict";
  const BP = (globalThis.BP = globalThis.BP || {});

  const ITEM_COLUMNS = ["instance_id", "bin_width", "bin_height", "item_id", "width", "height", "profit"];
  const SOLUTION_COLUMNS = ["x", "y", "rotated"];
  const ALL_COLUMNS = ITEM_COLUMNS.concat(SOLUTION_COLUMNS);

  const FORMAT_NOTES = [
    "One row per item. instance_id groups items that belong to the same bin — " +
      "there is one fixed bin per instance_id, sized bin_width x bin_height.",
    "instance_id, bin_width, bin_height, item_id, width, height, profit are the " +
      "problem data — do not edit them. Scoring mode checks a signature computed " +
      "over these columns and will flag the file if they don't match what was " +
      "generated.",
    "Fill in x, y, and rotated only for the items you decide to pack. Leave x " +
      "AND y both blank to mark an item as not placed — that's fine, it just " +
      "scores no profit for that item. Filling in only one of x/y is invalid.",
    "Coordinates: x=0, y=0 is the bin's TOP-LEFT corner. x increases to the " +
      "right, y increases DOWNWARD (screen/matrix convention).",
    "rotated: TRUE swaps the item's width and height (a w x h item occupies " +
      "h x w once rotated). Leave blank or FALSE for no rotation.",
    "Placements must not overlap or go outside the bin. If any item in an " +
      "instance does, that WHOLE instance scores 0 profit, even for the items " +
      "that were placed validly.",
    "Upload this same file, filled in, to Scoring mode to get graded.",
  ];

  const isMissing = (v) => v === null || v === undefined || v === "" || (typeof v === "number" && Number.isNaN(v));

  /** pandas .astype(int): floats truncate toward zero. */
  function toInt(v) {
    if (typeof v === "boolean") return v ? 1 : 0;
    if (typeof v === "number") {
      if (!Number.isFinite(v)) throw new Error(`cannot convert ${v} to an integer`);
      return Math.trunc(v);
    }
    if (typeof v === "string" && /^\s*[+-]?\d+\s*$/.test(v)) return parseInt(v, 10);
    throw new Error(`invalid literal for int() with base 10: '${v}'`);
  }

  /** Python bool(v): any non-empty string (even "FALSE") is True. */
  function pyBool(v) {
    if (typeof v === "boolean") return v;
    if (typeof v === "number") return v !== 0;
    if (typeof v === "string") return v.length > 0;
    return Boolean(v);
  }

  /** Python-style repr of a list of ints / strings, for error messages. */
  const pyList = (xs) => "[" + xs.map((x) => (typeof x === "string" ? `'${x}'` : String(x))).join(", ") + "]";

  function instanceRows(instances) {
    const rows = [];
    for (const inst of instances) {
      for (const it of inst.items) {
        rows.push({
          instance_id: inst.id, bin_width: inst.bin_w, bin_height: inst.bin_h,
          item_id: it.id, width: it.w, height: it.h, profit: it.profit,
        });
      }
    }
    return rows;
  }

  async function sha256Hex(text) {
    const digest = await globalThis.crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
    return Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, "0")).join("");
  }

  /** Order-independent hash over the ground-truth (non-solution) columns. */
  function signature(rows) {
    const canon = rows.map((r) => ITEM_COLUMNS.map((c) => toInt(r[c])));
    canon.sort((a, b) => {
      for (let i = 0; i < a.length; i++) if (a[i] !== b[i]) return a[i] - b[i];
      return 0;
    });
    return sha256Hex(canon.map((row) => row.join(",")).join("|"));
  }

  /** Build the combined workbook (Uint8Array). placementsByInstance:
   *  {instance_id: [{item, x, y, rotated}]} fills x/y/rotated (Game export);
   *  without it they're left blank (Challenge download). */
  async function instancesWorkbookBytes(instances, seed, difficulty, nInstances, placementsByInstance = null) {
    const rows = instanceRows(instances);
    const sig = await signature(rows);

    const placed = new Map();
    for (const [instanceId, placements] of Object.entries(placementsByInstance || {})) {
      for (const p of placements) placed.set(`${instanceId}:${p.item.id}`, [p.x, p.y, p.rotated]);
    }

    const itemsAoa = [ALL_COLUMNS];
    for (const r of rows) {
      const [x, y, rotated] = placed.get(`${r.instance_id}:${r.item_id}`) || [null, null, null];
      itemsAoa.push(ITEM_COLUMNS.map((c) => r[c]).concat([x, y, rotated]));
    }

    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(itemsAoa), "items");
    XLSX.utils.book_append_sheet(
      wb,
      XLSX.utils.aoa_to_sheet([["seed", "difficulty", "num_instances", "signature"], [seed, difficulty, nInstances, sig]]),
      "meta",
    );
    const notes = XLSX.utils.aoa_to_sheet([["Format notes"]].concat(FORMAT_NOTES.map((n) => [n])));
    notes["!cols"] = [{ wch: 100 }];
    XLSX.utils.book_append_sheet(wb, notes, "notes");
    return XLSX.write(wb, { type: "array", bookType: "xlsx" });
  }

  function sheetRecords(ws) {
    const aoa = XLSX.utils.sheet_to_json(ws, { header: 1, defval: null, raw: true, blankrows: false });
    if (!aoa.length) return { columns: [], rows: [] };
    const columns = aoa[0].map((h) => (h === null ? "" : String(h)));
    const rows = aoa.slice(1).map((r) => {
      const o = {};
      columns.forEach((c, i) => { if (!(c in o)) o[c] = r[i] === undefined ? null : r[i]; });
      return o;
    });
    return { columns, rows };
  }

  /** Parse and validate a submission (ArrayBuffer). Returns {rows, integrity};
   *  throws Error with a user-facing message for unscorable files. */
  async function parseSubmissionWorkbook(data) {
    const wb = XLSX.read(data, { type: "array" });
    const sheetName = wb.SheetNames.includes("items") ? "items" : wb.SheetNames[0];
    const { columns, rows: allRows } = sheetRecords(wb.Sheets[sheetName]);

    const missing = ITEM_COLUMNS.filter((c) => !columns.includes(c)).sort();
    if (missing.length) throw new Error(`File is missing required column(s): ${pyList(missing)}`);

    let rows = allRows.filter((r) => !isMissing(r.instance_id) && !isMissing(r.item_id));
    if (!rows.length) throw new Error("File has no item rows.");

    for (const col of ITEM_COLUMNS) {
      if (rows.some((r) => isMissing(r[col]))) {
        throw new Error(`Column '${col}' has missing values — every item row needs it filled in.`);
      }
      for (const r of rows) r[col] = toInt(r[col]);
    }

    const counts = new Map();
    for (const r of rows) {
      const k = `${r.instance_id}:${r.item_id}`;
      counts.set(k, (counts.get(k) || 0) + 1);
    }
    const dupKeys = [];
    for (const r of rows) {
      const k = `${r.instance_id}:${r.item_id}`;
      if (counts.get(k) > 1 && !dupKeys.includes(k)) dupKeys.push(k);
    }
    if (dupKeys.length) {
      const pairs = dupKeys.map((k) => { const [i, j] = k.split(":"); return `instance ${i}/item ${j}`; }).join(", ");
      throw new Error(`Duplicate item rows found: ${pairs}`);
    }

    const bins = new Map();
    for (const r of rows) {
      if (!bins.has(r.instance_id)) bins.set(r.instance_id, { w: new Set(), h: new Set() });
      bins.get(r.instance_id).w.add(r.bin_width);
      bins.get(r.instance_id).h.add(r.bin_height);
    }
    const inconsistent = [...bins.entries()]
      .filter(([, b]) => b.w.size > 1 || b.h.size > 1)
      .map(([id]) => id)
      .sort((a, b) => a - b);
    if (inconsistent.length) {
      throw new Error(`Inconsistent bin_width/bin_height within instance(s): ${pyList(inconsistent)}`);
    }

    // pandas.read_excel turns a column whose filled cells are all booleans or
    // the words True/TRUE/true/False/FALSE/false into real booleans; any
    // other text is left as a string and then bool()'d (so "no" is True).
    const PD_TRUE = ["True", "TRUE", "true"];
    const PD_FALSE = ["False", "FALSE", "false"];
    const filled = allRows.map((r) => r.rotated).filter((v) => !isMissing(v));
    const boolLike = filled.length && filled.every((v) => typeof v === "boolean" || PD_TRUE.includes(v) || PD_FALSE.includes(v));
    for (const r of rows) {
      let v = r.rotated;
      if (boolLike && typeof v === "string") v = PD_TRUE.includes(v);
      r.rotated = isMissing(v) ? false : pyBool(v);
    }
    const partial = rows.filter((r) => isMissing(r.x) !== isMissing(r.y));
    if (partial.length) {
      const pairs = partial.map((r) => `instance ${r.instance_id}/item ${r.item_id}`).join(", ");
      throw new Error(
        `Incomplete placement data (only one of x/y filled in) for: ${pairs}. ` +
          "Fill in both x and y, or leave both blank to mark the item as not placed.",
      );
    }
    for (const r of rows) {
      r.x = isMissing(r.x) ? null : toInt(r.x);
      r.y = isMissing(r.y) ? null : toInt(r.y);
    }

    const integrity = {
      checked: false, ok: true,
      message: "No signature found in this file (no 'meta' sheet) — integrity not verified.",
    };
    if (wb.SheetNames.includes("meta")) {
      const meta = sheetRecords(wb.Sheets.meta);
      if (meta.columns.includes("signature") && meta.rows.length) {
        const v = meta.rows[0].signature;
        const stored = isMissing(v) ? "nan" : String(v);
        const actual = await signature(rows);
        integrity.checked = true;
        if (actual === stored) {
          integrity.message = "Instance data matches the signature recorded at generation time.";
        } else {
          integrity.ok = false;
          integrity.message =
            "Instance data (bin size, item dimensions, or profits) does not match the " +
            "signature recorded when this file was generated — it may have been edited.";
        }
      }
    }
    return { rows, integrity };
  }

  /** Grade a submission. Returns {results, summary, reconstructed}. */
  function scoreSubmission(rows) {
    const groups = new Map();
    for (const r of rows) {
      if (!groups.has(r.instance_id)) groups.set(r.instance_id, []);
      groups.get(r.instance_id).push(r);
    }
    const results = [];
    const reconstructed = new Map();

    for (const instanceId of [...groups.keys()].sort((a, b) => a - b)) {
      const group = groups.get(instanceId);
      const binW = group[0].bin_width;
      const binH = group[0].bin_height;
      const itemsById = new Map(group.map((r) => [r.item_id, [r.width, r.height, r.profit]]));
      let potentialProfit = 0;
      for (const [, , p] of itemsById.values()) potentialProfit += p;

      const placed = [];
      for (const r of group) {
        if (r.x === null || r.y === null) continue;
        const [w0, h0, profit] = itemsById.get(r.item_id);
        const rotated = Boolean(r.rotated);
        const [w, h] = rotated ? [h0, w0] : [w0, h0];
        placed.push({ item_id: r.item_id, x: r.x, y: r.y, w, h, profit, rotated });
      }

      let feasible = true;
      let error = null;
      for (const p of placed) {
        if (p.x < 0 || p.y < 0 || p.x + p.w > binW || p.y + p.h > binH) {
          feasible = false;
          error = `item ${p.item_id} is out of bounds`;
          break;
        }
      }
      if (feasible) {
        outer: for (let i = 0; i < placed.length; i++) {
          for (let j = i + 1; j < placed.length; j++) {
            const a = placed[i];
            const b = placed[j];
            if (BP.game.rectsOverlap(a.x, a.y, a.w, a.h, b.x, b.y, b.w, b.h)) {
              feasible = false;
              error = `items ${a.item_id} and ${b.item_id} overlap`;
              break outer;
            }
          }
        }
      }

      const profit = feasible ? placed.reduce((s, p) => s + p.profit, 0) : 0;
      const packedArea = placed.reduce((s, p) => s + p.w * p.h, 0);
      const utilization = binW * binH ? Math.min(100.0, (100.0 * packedArea) / (binW * binH)) : 0.0;

      results.push({
        instance_id: instanceId, feasible, error: error || "",
        profit, potential_profit: potentialProfit,
        utilization, items_placed: placed.length, items_total: itemsById.size,
      });
      reconstructed.set(instanceId, { bin_w: binW, bin_h: binH, placed, items_by_id: itemsById, feasible });
    }

    const sum = (k) => results.reduce((s, r) => s + r[k], 0);
    const summary = {
      total_score: sum("profit"),
      total_potential: sum("potential_profit"),
      avg_utilization: results.length ? sum("utilization") / results.length : 0.0,
      n_instances: results.length,
      n_feasible: results.filter((r) => r.feasible).length,
    };
    return { results, summary, reconstructed };
  }

  BP.excel = {
    ITEM_COLUMNS, ALL_COLUMNS,
    signature, instancesWorkbookBytes, parseSubmissionWorkbook, scoreSubmission,
  };
})();
