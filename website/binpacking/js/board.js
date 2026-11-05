/* Drag-and-drop bin board — port of
 * Greedy_BinPacking_App/frontend/index.html without the Streamlit iframe.
 *
 * Items are dragged from a palette on the left (at real-to-scale size while
 * dragging) and dropped onto a fixed grid bin on the right. The board never
 * changes game state itself: every action is reported through onEvent as
 *   {source: "palette"|"placed", item_id, x, y, rotated, remove?}
 * and the caller applies it and calls render() again. The overlap check
 * here only colors the live drop preview; feasibility is decided by
 * BP.game.isFeasible at the end of the round.
 */
(function () {
  "use strict";
  const BP = (globalThis.BP = globalThis.BP || {});

  const CELL = 26;

  function el(tag, className, text) {
    const e = document.createElement(tag);
    if (className) e.className = className;
    if (text !== undefined) e.textContent = text;
    return e;
  }

  const tooltipText = (profit, w, h) => `Profit: ${profit}  •  Size: ${w}×${h}`;

  function createBoard(root, onEvent) {
    root.classList.add("bp-root");
    const paletteEl = el("div", "bp-palette");
    const binWrapEl = el("div", "bp-bin-wrap");
    const binEl = el("div", "bp-bin");
    binWrapEl.appendChild(binEl);
    root.append(paletteEl, binWrapEl);

    const preview = el("div", "bp-preview");
    let data = { bin_w: 0, bin_h: 0, items: [], placed: [] };
    // Drag in progress: base (unrotated) size, current rotation, origin.
    let drag = null;

    function overlaps(x, y, w, h, excludeId) {
      if (x < 0 || y < 0 || x + w > data.bin_w || y + h > data.bin_h) return true;
      return data.placed.some(
        (p) => p.id !== excludeId && !(x + w <= p.x || p.x + p.w <= x || y + h <= p.y || p.y + p.h <= y),
      );
    }

    function makeGhost(e, w, h, color) {
      const ghost = el("div", "bp-ghost");
      Object.assign(ghost.style, { width: w * CELL + "px", height: h * CELL + "px", background: color });
      document.body.appendChild(ghost);
      // Anchor the ghost's center on the cursor; cellFromEvent uses the same
      // center-relative math so the drop lands where the ghost was shown.
      e.dataTransfer.setDragImage(ghost, (w * CELL) / 2, (h * CELL) / 2);
      setTimeout(() => ghost.remove(), 0);
    }

    function startDrag(e, id, baseW, baseH, color, rotated, source) {
      drag = { id, w: baseW, h: baseH, color, rotated, source };
      e.dataTransfer.setData("text/plain", String(id));
      e.dataTransfer.effectAllowed = "move";
      makeGhost(e, rotated ? baseH : baseW, rotated ? baseW : baseH, color);
    }

    function endDrag() {
      preview.style.display = "none";
      paletteEl.classList.remove("bp-drop-target");
      drag = null;
    }

    function footprint() {
      return drag.rotated ? [drag.h, drag.w] : [drag.w, drag.h];
    }

    function cellFromEvent(e, w, h) {
      const rect = binEl.getBoundingClientRect();
      return [
        Math.floor((e.clientX - rect.left - (w * CELL) / 2) / CELL),
        Math.floor((e.clientY - rect.top - (h * CELL) / 2) / CELL),
      ];
    }

    // Listeners on the persistent containers are attached once here (the
    // Streamlit component re-attached them on every render, stacking up).
    paletteEl.addEventListener("dragover", (e) => {
      if (!drag || drag.source !== "placed") return;
      e.preventDefault();
      paletteEl.classList.add("bp-drop-target");
    });
    paletteEl.addEventListener("dragleave", () => paletteEl.classList.remove("bp-drop-target"));
    paletteEl.addEventListener("drop", (e) => {
      paletteEl.classList.remove("bp-drop-target");
      if (!drag || drag.source !== "placed") return;
      e.preventDefault();
      const id = drag.id;
      endDrag();
      onEvent({ source: "placed", remove: true, item_id: id, x: 0, y: 0, rotated: false });
    });

    binEl.addEventListener("dragover", (e) => {
      e.preventDefault();
      if (!drag) return;
      const [w, h] = footprint();
      const [gx, gy] = cellFromEvent(e, w, h);
      const bad = overlaps(gx, gy, w, h, drag.source === "placed" ? drag.id : null);
      Object.assign(preview.style, {
        display: "block",
        left: gx * CELL + "px", top: gy * CELL + "px",
        width: w * CELL + "px", height: h * CELL + "px",
        borderColor: bad ? "#d32f2f" : "#2e7d32",
      });
    });
    binEl.addEventListener("dragleave", (e) => {
      if (!binEl.contains(e.relatedTarget)) preview.style.display = "none";
    });
    binEl.addEventListener("drop", (e) => {
      e.preventDefault();
      preview.style.display = "none";
      if (!drag) return;
      const [w, h] = footprint();
      const [gx, gy] = cellFromEvent(e, w, h);
      const ev = { source: drag.source, item_id: drag.id, x: gx, y: gy, rotated: drag.rotated };
      endDrag();
      onEvent(ev);
    });

    function iconButton(text, title, extraClass, handler) {
      const b = el("button", "bp-icon-btn" + (extraClass ? " " + extraClass : ""), text);
      b.type = "button";
      b.title = title;
      b.setAttribute("aria-label", title);
      b.addEventListener("click", (e) => { e.stopPropagation(); handler(); });
      return b;
    }

    function render(next) {
      // Normal drops end the drag before re-rendering, so a drag still in
      // flight here belongs to a board that was swapped out (e.g. the
      // stopwatch ran out mid-drag): drop it so it can't land in the new round.
      if (drag) endDrag();
      data = next;
      binWrapEl.style.width = data.bin_w * CELL + "px";
      binWrapEl.style.height = data.bin_h * CELL + "px";
      paletteEl.replaceChildren();
      binEl.replaceChildren();

      for (const p of data.placed) {
        const node = el("div", "bp-placed", "#" + p.id);
        node.draggable = true;
        Object.assign(node.style, {
          left: p.x * CELL + "px", top: p.y * CELL + "px",
          width: p.w * CELL + "px", height: p.h * CELL + "px", background: p.color,
        });
        node.title = tooltipText(p.profit, p.w, p.h);
        node.dataset.itemId = p.id;

        const controls = el("div", "bp-controls");
        controls.append(
          // Rotate in place: same top-left corner, width/height swapped.
          iconButton("⟳", "Rotate in place", "bp-rotate", () =>
            onEvent({ source: "placed", item_id: p.id, x: p.x, y: p.y, rotated: !p.rotated })),
          iconButton("✕", "Remove from bin", "bp-delete", () =>
            onEvent({ source: "placed", remove: true, item_id: p.id, x: 0, y: 0, rotated: false })),
        );
        node.appendChild(controls);

        node.addEventListener("dragstart", (e) => {
          // p.w/p.h are the on-screen (already rotated) footprint; recover
          // the base size so rotation math matches palette items.
          const baseW = p.rotated ? p.h : p.w;
          const baseH = p.rotated ? p.w : p.h;
          startDrag(e, p.id, baseW, baseH, p.color, p.rotated, "placed");
        });
        node.addEventListener("dragend", endDrag);
        binEl.appendChild(node);
      }
      binEl.appendChild(preview);

      for (const item of data.items) {
        const card = el("div", "bp-card");
        card.draggable = true;
        card.title = tooltipText(item.profit, item.w, item.h);
        card.dataset.itemId = item.id;
        const swatch = el("div", "bp-swatch");
        swatch.style.background = item.color;
        const label = el("div", "bp-label");
        label.append(el("div", "bp-label-id", "#" + item.id), el("div", "bp-label-detail", `${item.w}×${item.h} · $${item.profit}`));
        card.append(swatch, label);
        // No rotate control here: drop it in as-is and rotate it afterwards
        // with ⟳ on the placed item, so there's only one way to rotate.
        card.addEventListener("dragstart", (e) => startDrag(e, item.id, item.w, item.h, item.color, false, "palette"));
        card.addEventListener("dragend", endDrag);
        paletteEl.appendChild(card);
      }
      if (!data.items.length) paletteEl.appendChild(el("div", "bp-palette-empty", "All items placed. Drag one back here to remove it."));
    }

    return { render };
  }

  BP.createBoard = createBoard;
  BP.BOARD_CELL = CELL;
})();
