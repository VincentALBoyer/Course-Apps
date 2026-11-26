/* Queue Lab — Staffing challenge: plan baristas per hour for a café's day. */
(function () {
  "use strict";
  const { $, esc } = MG;
  const Q = MG.QL;
  const { DAY, num, pct, money } = Q;

  let G = null; // { day, plan, attempts, bench, benchPlan }
  let active = false;

  const hourLabel = (h) => `${DAY.startHour + h}:00`;
  const rhoClass = (r) => (r >= 1 ? "bad" : r >= 0.9 ? "warn" : "ok");

  // ── start ────────────────────────────────────────────────────────────
  $("st-start").addEventListener("click", () => {
    const code = ($("st-code").value.trim() || MG.newGameCode()).toUpperCase();
    const day = Q.makeDay(code);
    G = { day, plan: day.lamH.map(() => 3), attempts: [], bench: null, benchPlan: Q.formulaPlan(day) };
    $("st-setup").hidden = true;
    $("st-game").hidden = false;
    $("st-results").hidden = true;
    $("st-code-out").textContent = code;
    $("st-svc").textContent = `${day.svcMin} min`;
    $("st-mu").textContent = `${num(60 / day.svcMin, 0)} / h`;
    window.scrollTo({ top: 0 });
    renderPlan();
  });
  $("st-code").addEventListener("keydown", (e) => { if (e.key === "Enter") $("st-start").click(); });
  $("st-new").addEventListener("click", () => {
    $("st-game").hidden = true;
    $("st-setup").hidden = false;
    $("st-code").value = "";
    G = null;
  });
  $("st-copy").addEventListener("click", () => {
    const code = G.day.code;
    (navigator.clipboard ? navigator.clipboard.writeText(code) : Promise.reject())
      .then(() => MG.toast(`Copied ${code}`), () => MG.toast(`Game code: ${code}`));
  });
  $("st-forecast").addEventListener("change", renderPlan);

  // ── plan table ───────────────────────────────────────────────────────
  $("st-plan").addEventListener("click", (e) => {
    const b = e.target.closest("button[data-h]");
    if (!b) return;
    const h = Number(b.dataset.h);
    G.plan[h] = Math.max(1, Math.min(DAY.maxStaff, G.plan[h] + Number(b.dataset.d)));
    renderPlan();
  });

  function renderPlan() {
    const { day, plan } = G;
    const fc = $("st-forecast").checked;
    let wages = 0;
    let fTotal = 0;
    const rows = plan.map((c, h) => {
      const f = Q.forecastHour(day, h, c);
      wages += f.wages;
      fTotal += f.cost;
      const fcCells = fc ? `<td>${f.stable ? num(f.Wq, 1) : "∞"}</td><td>${money(f.cost)}</td>` : "";
      return `<tr><td class="text">${hourLabel(h)}</td><td>${day.lamH[h]}</td>
        <td class="ql-step"><button class="btn small" data-h="${h}" data-d="-1" type="button" aria-label="One barista less at ${hourLabel(h)}" ${c <= 1 ? "disabled" : ""}>−</button>
          <b>${c}</b><button class="btn small" data-h="${h}" data-d="1" type="button" aria-label="One barista more at ${hourLabel(h)}" ${c >= DAY.maxStaff ? "disabled" : ""}>+</button></td>
        <td><span class="ql-rho ${rhoClass(f.rho)}">${num(f.rho, 2)}</span></td>${fcCells}</tr>`;
    }).join("");
    const fcHead = fc ? `<th title="M/M/c steady-state average wait in line, in minutes">W<sub>q</sub> min</th><th title="Wages + forecast waiting cost">Cost</th>` : "";
    const fcFoot = fc ? `<td></td><td><b>${money(fTotal)}</b></td>` : "";
    $("st-plan").innerHTML = `<thead><tr><th class="text">Hour</th><th title="Expected customers per hour">λ / h</th><th class="ql-step-h">Baristas</th><th title="λ / (c·μ)">ρ</th>${fcHead}</tr></thead>
      <tbody>${rows}</tbody>
      <tfoot><tr><td class="text"><b>Day</b></td><td>${day.lamH.reduce((a, b) => a + b, 0)}</td><td class="ql-step-total">${plan.reduce((a, b) => a + b, 0)} barista-hours · ${money(wages)}</td><td></td>${fcFoot}</tr></tfoot>`;
    renderDemand();
  }

  function renderDemand() {
    if (!active || !globalThis.Plotly) return;
    const { day, plan } = G;
    const c = MG.theme.colors();
    const mu = 60 / day.svcMin;
    const H = DAY.hours;
    const capX = Array.from({ length: H + 1 }, (_, h) => DAY.startHour + h);
    const capY = plan.concat(plan[H - 1]).map((k) => k * mu);
    const over = day.lamH.map((l, h) => l >= plan[h] * mu);
    MG.plot($("chart-demand"), [
      { type: "bar", x: day.lamH.map((_, h) => DAY.startHour + h + 0.5), y: day.lamH, width: 0.78, name: "Expected customers / h",
        marker: { color: over.map((o) => (o ? Q.color("--ql-bad") : Q.color("--ql-demand"))) },
        hovertemplate: "%{y} customers / h<extra></extra>" },
      { x: capX, y: capY, mode: "lines", line: { shape: "hv", color: c.text, width: 2.5 }, name: "Your capacity",
        hovertemplate: "capacity %{y:.0f} / h<extra></extra>" },
    ], {
      margin: { l: 48, r: 12, t: 8, b: 36 }, height: 300, legend: { orientation: "h", y: 1.12, x: 0 }, bargap: 0,
      xaxis: { tickvals: capX, ticktext: capX.map((h) => h + ":00"), range: [DAY.startHour, DAY.startHour + H] },
      yaxis: { title: "customers per hour", rangemode: "tozero" },
    }, { displayModeBar: false });
  }

  // ── run the day ──────────────────────────────────────────────────────
  $("st-run").addEventListener("click", () => {
    if (!G.bench) G.bench = Q.runDay(G.day, G.benchPlan);
    const res = Q.runDay(G.day, G.plan);
    G.attempts.push(res);
    $("st-results").hidden = false; // visible first, so Plotly sizes the chart to its column
    renderResults(res);
    $("st-results").scrollIntoView({ behavior: "smooth", block: "start" });
  });

  function renderResults(res) {
    const b = G.bench;
    const diff = res.cost - b.cost;
    const samePlan = res.plan.every((c, h) => c === b.plan[h]);
    const planStr = (p) => p.join(" · ");
    // The formula plan stays secret until the student matches or beats it: before that, only its
    // total cost is shown (its wage/waiting split or line chart would give the staffing away).
    if (samePlan || diff <= 0.5) G.revealed = true;
    const shown = G.revealed;
    const secret = b.plan.map(() => "?").join(" · ");
    let cls;
    let head;
    if (samePlan) {
      cls = "info";
      head = "🧮 This is exactly the formula plan.";
    } else if (diff < -0.5) {
      cls = "success";
      head = `🎉 You beat the formula plan by ${money(-diff)}!`;
      if (!G.beaten) { G.beaten = true; MG.balloons(); }
    } else if (diff <= 0.5) {
      cls = "success";
      head = "🤝 Same cost as the formula plan.";
    } else if (diff / b.cost <= 0.05) {
      cls = "info";
      head = `👍 Close: ${money(diff)} (${num((100 * diff) / b.cost, 1)}%) more than the formula plan.`;
    } else {
      cls = "warning";
      head = `${money(diff)} (${num((100 * diff) / b.cost, 0)}%) more than the formula plan. Look at the hour-by-hour table to see where it went.`;
    }
    $("st-res-title").textContent = `📋 How the day went (attempt ${G.attempts.length})`;
    $("st-verdict").innerHTML = `<div class="alert ${cls}"><b>${head}</b><br>
      ${shown
        ? `The <b>formula plan</b> ${planStr(b.plan)} picks, for each hour on its own, the staffing with the lowest M/M/c
      forecast cost (wages + λ · W<sub>q</sub> · $0.30). It ignores the line carried over from one hour into the next,
      so a smart plan can beat it.`
        : `The <b>formula plan</b> (kept secret until you match it) costs <b>${money(b.cost)}</b> on these same customers.
      It uses queueing formulas to pick each hour's staffing. Can you match it?`}</div>`;

    const m = (label, val, sub) => `<div><div class="metric-label">${label}</div><div class="metric-value">${val}</div>${sub ? `<div class="metric-delta ql-muted">${sub}</div>` : ""}</div>`;
    $("st-metrics").innerHTML = [
      m("Total cost", money(res.cost), `formula plan ${money(b.cost)}`),
      m("Wages", money(res.wages), `${res.plan.reduce((a, c) => a + c, 0)} barista-hours`),
      m("Waiting cost", money(res.waitCost), shown ? `formula plan ${money(b.waitCost)}` : ""),
      m("Average wait", num(res.avgWait) + " min", `${res.n} customers`),
      m(`Waited ≤ ${DAY.target} min`, pct(res.within), `formula plan ${pct(b.within)}`),
      m("Longest line", res.maxQ, `last customer out at ${Q.clock(DAY.startHour + res.closed / 60)}`),
    ].join("");

    $("st-hours").innerHTML = `<thead><tr><th class="text">Hour</th><th>Baristas</th><th>Customers</th><th>Avg wait</th><th>Longest wait</th><th>Wages</th><th>Waiting</th><th>Total</th></tr></thead><tbody>${res.hours
      .map((h) => {
        const avg = h.n ? h.sumWait / h.n : 0;
        return `<tr><td class="text">${hourLabel(h.h)}</td><td>${h.c}</td><td>${h.n}</td><td class="${avg > DAY.target ? "ql-badtxt" : ""}">${num(avg)} min</td>
          <td>${num(h.maxWait, 1)} min</td><td>${money(h.wages)}</td><td>${money(h.wait)}</td><td><b>${money(h.wages + h.wait)}</b></td></tr>`;
      }).join("")}</tbody>`;

    const best = Math.min(...G.attempts.map((a) => a.cost));
    $("st-attempts").innerHTML = `<thead><tr><th class="text">#</th><th class="text">Plan (baristas per hour)</th><th>Wages</th><th>Waiting</th><th>Total</th><th>vs formula</th></tr></thead><tbody>${G.attempts
      .map((a, i) => `<tr${a.cost === best ? ' class="ql-best"' : ""}><td class="text">${i + 1}${a.cost === best ? " ⭐" : ""}</td><td class="text ql-mono">${planStr(a.plan)}</td>
        <td>${money(a.wages)}</td><td>${money(a.waitCost)}</td><td><b>${money(a.cost)}</b></td><td>${MG.signed(Math.round(a.cost - b.cost))}</td></tr>`)
      .reverse().join("")}<tr class="ql-formula"><td class="text">🧮</td><td class="text ql-mono">${shown ? planStr(b.plan) : secret}</td><td>${shown ? money(b.wages) : "?"}</td><td>${shown ? money(b.waitCost) : "?"}</td><td><b>${money(b.cost)}</b></td><td>formula</td></tr></tbody>`;

    G.last = res;
    renderDay();
  }

  function renderDay() {
    if (!active || !globalThis.Plotly || !G || !G.last) return;
    const c = MG.theme.colors();
    const line = (res, name, color, width, dash) => {
      const x = res.trace.map((p) => DAY.startHour + p[0] / 60);
      const y = res.trace.map((p) => p[2]);
      return { x, y, mode: "lines", name, line: { shape: "hv", color, width, dash }, hovertemplate: "%{y} in line<extra>" + name + "</extra>" };
    };
    const end = DAY.startHour + Math.max(G.last.closed, G.bench.closed, DAY.hours * 60) / 60;
    const traces = [line(G.last, "Your plan", c.accent, 2, "solid")];
    if (G.revealed) traces.unshift(line(G.bench, "Formula plan", c.muted, 1.5, "dot"));
    MG.plot($("chart-day"), traces, {
      margin: { l: 44, r: 12, t: 8, b: 36 }, height: 300, legend: { orientation: "h", y: 1.12, x: 0 },
      xaxis: { range: [DAY.startHour, end], tickvals: Array.from({ length: Math.ceil(end - DAY.startHour) + 1 }, (_, i) => DAY.startHour + i), ticktext: Array.from({ length: Math.ceil(end - DAY.startHour) + 1 }, (_, i) => DAY.startHour + i + ":00") },
      yaxis: { title: "people in line", rangemode: "tozero" },
      shapes: [{ type: "line", x0: DAY.startHour + DAY.hours, x1: DAY.startHour + DAY.hours, yref: "paper", y0: 0, y1: 1, line: { color: c.muted, width: 1, dash: "dash" } }],
      annotations: [{ x: DAY.startHour + DAY.hours, yref: "paper", y: 1, text: "doors close ", showarrow: false, xanchor: "right", yanchor: "top", font: { size: 11, color: c.muted } }],
    }, { displayModeBar: false });
  }

  Q.views.staffing = {
    onShow() { active = true; if (G) { renderDemand(); renderDay(); } },
    onHide() { active = false; },
    onTheme() { if (active && G) { renderDemand(); renderDay(); } },
  };
})();
