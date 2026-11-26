/* Queue Lab — Explore tab: wait vs load curves, variability and pooling. */
(function () {
  "use strict";
  const { $, esc } = MG;
  const Q = MG.QL;
  const { num, pct } = Q;

  const X = { rho: 0.8, c: 1, arr: "random", svc: "random", sep: true, log: false };
  let simDots = []; // { rho, y, curve }
  let active = false;

  const RHOS = [];
  for (let r = 0.01; r < 0.995; r += 0.005) RHOS.push(Number(r.toFixed(3)));

  /** The curves to draw for the current settings. mu = 1: waits are in service times. */
  function curves() {
    const list = [{ key: "shared", name: X.c > 1 ? `One shared line, ${X.c} baristas` : "One barista", color: "--accent", dash: "solid",
      f: (rho) => Q.theory({ lam: rho * X.c, mu: 1, c: X.c, arr: X.arr, svc: X.svc }) }];
    if (X.c > 1 && X.sep) {
      list.push({ key: "sep", name: `A line per barista (${X.c} lines)`, color: "--ql-sep", dash: "solid",
        f: (rho) => Q.theory({ lam: rho * X.c, mu: 1, c: X.c, arr: X.arr, svc: X.svc, layout: "separate", choice: "random" }) });
    }
    // With random arrivals, each separate line is exactly M/G/1 at the same ρ, so the M/M/1 reference
    // would sit on top of the separate-lines curve when service is random too.
    const sameAsSep = X.c > 1 && X.sep && X.arr === "random" && X.svc === "random";
    if ((X.c > 1 || X.arr !== "random" || X.svc !== "random") && !sameAsSep) {
      list.push({ key: "ref", name: "Reference: M/M/1", color: "--muted", dash: "dot",
        f: (rho) => Q.theory({ lam: rho, mu: 1, c: 1 }) });
    }
    return list;
  }

  function render() {
    $("x-rho-out").textContent = X.rho.toFixed(2);
    $("x-c-out").textContent = X.c;
    $("x-sep").disabled = X.c === 1;
    $("x-sep").closest("label").classList.toggle("ql-disabled", X.c === 1);
    const cs = curves();
    renderReadout(cs);
    if (active) renderChart(cs);
  }

  function renderChart(cs) {
    if (!globalThis.Plotly) return;
    const c = MG.theme.colors();
    const ymax = 10;
    const traces = [];
    for (const cv of cs) {
      const col = Q.color(cv.color);
      const ys = RHOS.map((r) => cv.f(r).Wq);
      traces.push({ x: RHOS, y: X.log ? ys.map((y) => (y > 0 ? y : null)) : ys, mode: "lines", name: cv.name, line: { color: col, width: cv.key === "ref" ? 1.6 : 2.6, dash: cv.dash },
        hovertemplate: "ρ = %{x:.2f}<br>wait = %{y:.2f} service times<extra>" + esc(cv.name) + "</extra>" });
      const here = cv.f(X.rho).Wq;
      if (here > 0 || !X.log) {
        traces.push({ x: [X.rho], y: [here], mode: "markers", showlegend: false, hoverinfo: "skip", marker: { color: col, size: 10, line: { color: c.bg, width: 2 } } });
      }
      const pts = simDots.filter((d) => d.curve === cv.key);
      if (pts.length) {
        traces.push({ x: pts.map((d) => d.rho), y: pts.map((d) => (X.log && d.y <= 0 ? null : d.y)), mode: "markers", name: "Simulated", showlegend: cv.key === "shared",
          marker: { color: col, size: 8, symbol: "diamond", opacity: 0.75, line: { color: c.text, width: 1 } },
          hovertemplate: "ρ = %{x:.2f}<br>simulated wait = %{y:.2f}<extra>20,000 customers</extra>" });
      }
    }
    MG.plot($("chart-x"), traces, {
      margin: { l: 56, r: 12, t: 8, b: 44 }, height: 380,
      legend: { orientation: "h", y: 1.1, x: 0 },
      xaxis: { title: "ρ = load (share of time baristas are busy)", range: [0, 1], dtick: 0.1 },
      yaxis: X.log
        ? { title: "wait in line (service times)", type: "log", range: [-2, 2.3] }
        : { title: "wait in line (service times)", range: [0, ymax] },
      shapes: [{ type: "line", x0: X.rho, x1: X.rho, yref: "paper", y0: 0, y1: 1, line: { color: c.muted, width: 1, dash: "dot" } }],
    }, { displayModeBar: false });
  }

  function renderReadout(cs) {
    const up = Math.min(0.99, X.rho + 0.05);
    const items = cs.map((cv) => {
      const a = cv.f(X.rho);
      const b = cv.f(up);
      const ratio = a.Wq > 0 ? b.Wq / a.Wq : null;
      const facts = [
        `<li><span>Wait in line</span><b>${num(a.Wq)} service times</b></li>`,
        `<li><span>With a 2-minute drink</span><b>${num(a.Wq * 2, 1)} min</b></li>`,
      ];
      if (a.Pwait != null) facts.push(`<li><span>Chance of waiting</span><b>${pct(a.Pwait)}</b></li>`);
      if (ratio != null) facts.push(`<li><span>If ρ rises to ${up.toFixed(2)}</span><b>wait ×${num(ratio, 1)}</b></li>`);
      return `<div class="ql-read"><div class="ql-read-name"><i class="lg-dot" style="background:${Q.color(cv.color)}"></i>${esc(cv.name)}</div><ul>${facts.join("")}</ul></div>`;
    }).join("");
    $("x-readout").innerHTML = `<p class="ql-read-at">At ρ = <b>${X.rho.toFixed(2)}</b></p>${items}`;
  }

  // ── inputs ───────────────────────────────────────────────────────────
  const clearDots = () => { simDots = []; };
  $("x-rho").addEventListener("input", () => { X.rho = Number($("x-rho").value); render(); });
  $("x-c").addEventListener("input", () => { X.c = Number($("x-c").value); clearDots(); render(); });
  document.querySelectorAll('input[name="x-arr"]').forEach((r) => r.addEventListener("change", () => { X.arr = r.value; clearDots(); render(); }));
  document.querySelectorAll('input[name="x-svc"]').forEach((r) => r.addEventListener("change", () => { X.svc = r.value; clearDots(); render(); }));
  $("x-sep").addEventListener("change", () => { X.sep = $("x-sep").checked; render(); });
  $("x-log").addEventListener("change", () => { X.log = $("x-log").checked; render(); });
  $("x-clear").addEventListener("click", () => { clearDots(); render(); });

  $("x-sim").addEventListener("click", () => {
    const btn = $("x-sim");
    btn.disabled = true;
    // Let the button repaint before the (short) blocking run.
    setTimeout(() => {
      const cs = curves().filter((cv) => cv.key !== "ref");
      const msgs = [];
      for (const cv of cs) {
        const s = Q.simulatePoint({ rho: X.rho, c: X.c, arr: X.arr, svc: X.svc, layout: cv.key === "sep" ? "separate" : "shared", choice: "random" });
        simDots.push({ rho: X.rho, y: s.Wq, curve: cv.key });
        msgs.push(`${cv.key === "sep" ? "separate lines" : "shared line"} ${num(s.Wq)} (theory ${num(cv.f(X.rho).Wq)})`);
      }
      btn.disabled = false;
      render();
      MG.toast(`20,000 customers at ρ = ${X.rho.toFixed(2)}: wait ${msgs.join("; ")} service times.`);
    }, 20);
  });

  Q.views.explore = {
    onShow() { active = true; render(); },
    onHide() { active = false; },
    onTheme() { if (active) render(); },
  };
  render();
})();
