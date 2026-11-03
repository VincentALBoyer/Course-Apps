/* Small UI helpers shared by every minigame: light/dark toggle, toasts,
 * downloads, tables, Plotly with theme colors, celebration balloons. */
(function () {
  "use strict";
  const MG = (globalThis.MG = globalThis.MG || {});

  MG.$ = (id) => document.getElementById(id);
  MG.sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  /** Escape text for safe insertion into innerHTML. */
  MG.esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

  // ── light / dark theme ───────────────────────────────────────────────
  // Starts from the system setting; an explicit choice is remembered per
  // browser (each page applies it before first paint with a tiny inline
  // script in <head>). The same "mg-theme" key is used site-wide.
  const systemDark = window.matchMedia("(prefers-color-scheme: dark)");
  const listeners = [];
  const theme = {
    current: () => document.documentElement.dataset.theme || (systemDark.matches ? "dark" : "light"),
    /** Theme token values, for libraries (Plotly) that bake colors in. */
    colors() {
      const css = getComputedStyle(document.documentElement);
      const v = (name) => css.getPropertyValue(name).trim();
      return { text: v("--text"), muted: v("--muted"), border: v("--border"), accent: v("--accent"), bg: v("--bg") };
    },
    onChange(fn) { listeners.push(fn); },
  };
  MG.theme = theme;

  function updateToggle() {
    const btn = MG.$("theme-toggle");
    if (!btn) return;
    const dark = theme.current() === "dark";
    btn.textContent = dark ? "☀️ Light" : "🌙 Dark";
    btn.setAttribute("aria-label", dark ? "Switch to light mode" : "Switch to dark mode");
    btn.title = btn.getAttribute("aria-label");
  }
  function notify() { updateToggle(); listeners.forEach((fn) => { try { fn(); } catch (e) { console.error(e); } }); }

  const btn = MG.$("theme-toggle");
  if (btn) {
    btn.addEventListener("click", () => {
      const next = theme.current() === "dark" ? "light" : "dark";
      document.documentElement.dataset.theme = next;
      try { localStorage.setItem("mg-theme", next); } catch (e) { /* storage blocked: still switches */ }
      notify();
    });
  }
  systemDark.addEventListener("change", notify);
  updateToggle();

  // ── feedback ─────────────────────────────────────────────────────────
  MG.toast = function toast(text) {
    let stack = MG.$("toast-stack");
    if (!stack) {
      stack = document.createElement("div");
      stack.id = "toast-stack";
      stack.setAttribute("aria-live", "polite");
      document.body.appendChild(stack);
    }
    const t = document.createElement("div");
    t.className = "toast";
    t.textContent = text;
    stack.appendChild(t);
    setTimeout(() => { t.classList.add("leaving"); setTimeout(() => t.remove(), 350); }, 4000);
  };

  MG.balloons = function balloons() {
    const emojis = ["🎈", "🎈", "🎉", "🎈", "✨"];
    for (let i = 0; i < 24; i++) {
      const b = document.createElement("div");
      b.className = "balloon";
      b.textContent = emojis[i % emojis.length];
      b.style.left = Math.random() * 95 + "vw";
      b.style.animationDelay = Math.random() * 0.9 + "s";
      document.body.appendChild(b);
      setTimeout(() => b.remove(), 4500);
    }
  };

  MG.download = function download(data, filename, mime) {
    const url = URL.createObjectURL(new Blob([data], { type: mime }));
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };

  /** columns: [{key, label, fmt?, text?}] */
  MG.renderTable = function renderTable(table, columns, rows) {
    const thead = document.createElement("thead");
    const hr = document.createElement("tr");
    for (const c of columns) {
      const th = document.createElement("th");
      th.textContent = c.label;
      if (c.text) th.className = "text";
      hr.appendChild(th);
    }
    thead.appendChild(hr);
    const tbody = document.createElement("tbody");
    for (const r of rows) {
      const tr = document.createElement("tr");
      for (const c of columns) {
        const td = document.createElement("td");
        td.textContent = c.fmt ? c.fmt(r[c.key], r) : String(r[c.key]);
        if (c.text) td.className = "text";
        tr.appendChild(td);
      }
      tbody.appendChild(tr);
    }
    table.replaceChildren(thead, tbody);
  };

  /** Plotly.react with the site's defaults and the current theme's text
   *  and grid colors applied (transparent background). */
  MG.plot = function plot(el, data, layout, config = {}) {
    const c = theme.colors();
    const axis = (a = {}) => ({ gridcolor: c.border, zerolinecolor: c.border, ...a });
    const full = {
      paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
      font: { color: c.text },
      ...layout,
      xaxis: axis(layout.xaxis),
      yaxis: axis(layout.yaxis),
    };
    return Plotly.react(el, data, full, { responsive: true, displaylogo: false, ...config });
  };

  /** Python's f"{n:+d}" */
  MG.signed = (n) => (n >= 0 ? "+" + n : String(n));

  MG.yesNo = (v) => (v ? "✓" : "✗");
})();
