/* Queue Lab — Simulate tab: an animated coffee counter, measured vs theory. */
(function () {
  "use strict";
  const { $, esc } = MG;
  const Q = MG.QL;
  const { num, pct } = Q;

  const MAXC = 6;
  const SPEEDS = [0.25, 0.5, 1, 2, 5, 15, 60]; // simulated minutes per real second
  const DEFAULTS = { lam: 30, svcMin: 1.5, c: 1, layout: "shared", choice: "shortest", arr: "random", svc: "random" };
  const PRESETS = [
    { name: "Busy but fine", p: { lam: 30, svcMin: 1.5, c: 1 }, what: "ρ = 0.75. A line forms now and then, then clears." },
    { name: "Almost full", p: { lam: 38, svcMin: 1.5, c: 1 }, what: "ρ = 0.95. Only 27% more customers, yet the wait is about 6 times longer." },
    { name: "Overloaded", p: { lam: 45, svcMin: 1.5, c: 1 }, what: "ρ > 1. The line never stops growing." },
    { name: "Clockwork café", p: { lam: 38, svcMin: 1.5, c: 1, arr: "clock", svc: "clock" }, what: "ρ = 0.95 again, but nothing is random. Nobody ever waits." },
    { name: "Two baristas, same load", p: { lam: 76, svcMin: 1.5, c: 2 }, what: "ρ = 0.95 with twice the customers and staff. Compare with “Almost full”." },
    { name: "A line per barista", p: { lam: 96, svcMin: 3, c: 6, layout: "separate", choice: "random" }, what: "ρ = 0.8, customers pick a line at random. Then switch to one shared line." },
  ];

  // Café geometry (SVG units).
  const MID = 110;
  const HEAD_X = 318; // first place in line
  const GAP = 14;
  const MAXVIS = 18; // customers drawn per line
  const R = 6; // customer radius
  const SERVE_X = 342;
  const DOOR = { x: 16, y: MID };

  const P = { ...DEFAULTS };
  let sim = null;
  let seed = null;
  let rngA, rngS, rngL, tNext;
  let playing = false;
  let speedIx = 3;
  let active = true; // tab visible
  let rafOn = false;
  let lastFrame = 0;
  let lastStats = 0;
  let wSeries = [];
  const dots = new Map(); // customer id -> { el, x, y, cust }
  let counterEls = [];
  let overflowEls = [];

  const NS = "http://www.w3.org/2000/svg";
  const svgEl = (tag, attrs = {}, parent) => {
    const e = document.createElementNS(NS, tag);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  };

  // ── static parts of the café ─────────────────────────────────────────
  const shop = $("shop");
  svgEl("rect", { class: "floor", x: 2, y: 2, width: 416, height: 216, rx: 14 }, shop);
  svgEl("rect", { class: "door", x: 2, y: MID - 20, width: 8, height: 40, rx: 2 }, shop);
  svgEl("text", { class: "door-label", x: 14, y: MID - 26 }, shop).textContent = "door";
  const gCounters = svgEl("g", {}, shop);
  const gOverflow = svgEl("g", {}, shop);
  const gDots = svgEl("g", {}, shop);

  for (let s = 0; s < MAXC; s++) {
    const g = svgEl("g", { class: "counter" }, gCounters);
    svgEl("rect", { class: "bar", x: 354, y: -13, width: 10, height: 26, rx: 2 }, g);
    svgEl("text", { class: "barista", x: 386, y: 1 }, g).textContent = "🧑‍🍳";
    svgEl("rect", { class: "prog-bg", x: SERVE_X - 8, y: 8, width: 16, height: 2.4, rx: 1.2 }, g);
    const prog = svgEl("rect", { class: "prog", x: SERVE_X - 8, y: 8, width: 0, height: 2.4, rx: 1.2 }, g);
    counterEls.push({ g, prog });
    const o = svgEl("text", { class: "overflow", x: 30, y: 0 }, gOverflow);
    overflowEls.push(o);
  }

  const yOf = (s, n) => {
    const sp = n > 1 ? Math.min(40, 172 / (n - 1)) : 0;
    return MID + (s - (n - 1) / 2) * sp;
  };

  // ── settings ─────────────────────────────────────────────────────────
  $("sim-presets").innerHTML = PRESETS.map((p, k) => `<button class="ql-preset" data-k="${k}" type="button">
      <strong>${esc(p.name)}</strong><span>${esc(p.what)}</span></button>`).join("");
  $("sim-presets").addEventListener("click", (e) => {
    const b = e.target.closest(".ql-preset");
    if (!b) return;
    Object.assign(P, DEFAULTS, PRESETS[b.dataset.k].p);
    syncInputs();
    build(false);
    setPlaying(true);
  });

  function syncInputs() {
    $("lam").value = P.lam;
    $("svc").value = P.svcMin;
    $("c").value = P.c;
    for (const [name, v] of [["layout", P.layout], ["choice", P.choice], ["arr", P.arr], ["svcv", P.svc]]) {
      document.querySelector(`input[name="${name}"][value="${v}"]`).checked = true;
    }
    syncOutputs();
  }

  function syncOutputs() {
    const mu = 60 / P.svcMin;
    $("lam-out").textContent = `${P.lam} / h · one every ${num(60 / P.lam, 1)} min`;
    $("svc-out").textContent = `${P.svcMin} min · μ = ${num(mu, mu < 100 ? 1 : 0)} / h`;
    $("c-out").textContent = P.c;
    $("choice-wrap").hidden = P.layout !== "separate";
  }

  const onLive = (fn) => () => { fn(); syncOutputs(); measuringAgain(); startLoop(); };
  $("lam").addEventListener("input", onLive(() => { P.lam = Number($("lam").value); }));
  $("svc").addEventListener("input", onLive(() => { P.svcMin = Number($("svc").value); }));
  $("c").addEventListener("input", onLive(() => { P.c = Number($("c").value); sim.setStaff(P.c); }));
  document.querySelectorAll('input[name="arr"]').forEach((r) => r.addEventListener("change", onLive(() => { P.arr = r.value; })));
  document.querySelectorAll('input[name="svcv"]').forEach((r) => r.addEventListener("change", onLive(() => { P.svc = r.value; })));
  // Changing the lines restarts the café (same customers).
  document.querySelectorAll('input[name="layout"]').forEach((r) => r.addEventListener("change", () => { P.layout = r.value; syncOutputs(); build(false); }));
  document.querySelectorAll('input[name="choice"]').forEach((r) => r.addEventListener("change", () => { P.choice = r.value; build(false); }));
  $("sim-defaults").addEventListener("click", () => { Object.assign(P, DEFAULTS); syncInputs(); build(false); });

  /** A setting changed mid-run: measurements start again from now. */
  function measuringAgain() {
    sim.resetStats();
    wSeries = [];
    renderStats(true);
  }

  // ── controls ─────────────────────────────────────────────────────────
  function setPlaying(on) {
    playing = on;
    $("sim-play").textContent = on ? "⏸ Pause" : "▶ Play";
    lastFrame = performance.now();
    startLoop();
  }
  $("sim-play").addEventListener("click", () => setPlaying(!playing));
  // Leaving the browser tab pauses too (switching the app's tabs pauses via onHide).
  document.addEventListener("visibilitychange", () => { if (document.hidden && playing) setPlaying(false); });
  $("sim-restart").addEventListener("click", () => build(false));
  $("sim-ff").addEventListener("click", () => {
    const target = sim.nextId + 1000;
    const t0 = performance.now();
    while (sim.nextId < target && performance.now() - t0 < 1500) sim.advance(sim.t + 30);
    pushW();
    renderStats(true);
    startLoop();
    MG.toast(`Jumped to ${num(sim.t, 0)} min: ${sim.nextId.toLocaleString("en-US")} customers so far.`);
  });
  $("sim-speed").addEventListener("input", () => { speedIx = Number($("sim-speed").value); syncSpeed(); });
  function syncSpeed() {
    const v = SPEEDS[speedIx];
    $("sim-speed-out").textContent = v < 1 ? `1 s = ${v * 60} s` : `1 s = ${v} min`;
  }
  document.addEventListener("keydown", (e) => {
    if (!active || e.target.closest("input, textarea, select, button, summary")) return;
    if (e.key === " ") { e.preventDefault(); setPlaying(!playing); }
  });

  // ── the simulation ───────────────────────────────────────────────────
  function build(newCustomers) {
    if (newCustomers || seed == null) seed = globalThis.crypto.getRandomValues(new Uint32Array(1))[0];
    rngA = new MG.PyRandom(seed);
    rngS = new MG.PyRandom(seed + 1);
    rngL = new MG.PyRandom(seed + 2);
    tNext = 0;
    sim = new Q.QueueSim({
      maxServers: MAXC, staff: P.c, layout: P.layout, choice: P.choice, lineRng: rngL,
      trace: true, traceWindow: 240,
      arrivals: () => {
        tNext += Q.VAR[P.arr].draw(rngA, 60 / P.lam);
        return { t: tNext, svc: Q.VAR[P.svc].draw(rngS, P.svcMin) };
      },
    });
    wSeries = [];
    for (const d of dots.values()) d.el.remove();
    dots.clear();
    renderShop(1);
    renderStats(true);
  }

  function startLoop() {
    if (rafOn || !active) return;
    rafOn = true;
    lastFrame = performance.now();
    requestAnimationFrame(frame);
  }

  function frame(now) {
    if (!active) { rafOn = false; return; }
    const dt = Math.min(0.1, (now - lastFrame) / 1000);
    lastFrame = now;
    if (playing) sim.advance(sim.t + dt * SPEEDS[speedIx]);
    renderShop(dt);
    if (now - lastStats > 400) {
      lastStats = now;
      if (playing) pushW();
      renderStats(false);
    }
    // Keep animating while playing or while customers are still walking.
    if (playing || settling) requestAnimationFrame(frame);
    else rafOn = false;
  }

  // ── drawing the café ─────────────────────────────────────────────────
  let settling = false;
  const waitClass = (w) => (w < 2 ? "w0" : w < 5 ? "w1" : "w2");

  function renderShop(dt) {
    const t = sim.t;
    let n = P.c;
    for (let s = P.c; s < MAXC; s++) if (sim.servers[s].cust) n = s + 1;
    const seen = new Set();
    const place = (cu, x, y, cls) => {
      seen.add(cu.id);
      let d = dots.get(cu.id);
      if (!d) {
        d = { el: svgEl("circle", { r: R, cx: DOOR.x, cy: DOOR.y }, gDots), x: DOOR.x, y: DOOR.y, cust: cu };
        dots.set(cu.id, d);
      }
      d.tx = x;
      d.ty = y;
      d.el.setAttribute("class", "cust " + cls);
    };

    // Counters
    for (let s = 0; s < MAXC; s++) {
      const { g, prog } = counterEls[s];
      const srv = sim.servers[s];
      const shown = s < n;
      g.style.display = shown ? "" : "none";
      overflowEls[s].textContent = "";
      if (!shown) continue;
      const y = yOf(s, n);
      g.setAttribute("transform", `translate(0 ${y})`);
      g.classList.toggle("off", s >= P.c);
      g.classList.toggle("busy", !!srv.cust);
      if (srv.cust) {
        place(srv.cust, SERVE_X, y, "srv");
        prog.setAttribute("width", (16 * Math.min(1, (t - srv.cust.tStart) / srv.cust.svc)).toFixed(2));
      } else prog.setAttribute("width", 0);
    }

    // Lines
    sim.queues.forEach((q, k) => {
      if (P.layout === "separate" && k >= n) return;
      const y = P.layout === "shared" ? MID : yOf(k, n);
      const m = Math.min(q.length, MAXVIS);
      for (let i = 0; i < m; i++) place(q[i], HEAD_X - i * GAP, y, waitClass(t - q[i].tArr));
      const o = overflowEls[k];
      o.textContent = q.length > MAXVIS ? `+${(q.length - MAXVIS).toLocaleString("en-US")}` : "";
      o.setAttribute("y", y - 9);
    });

    // Move every dot toward its place; served customers pick up their drink and fade out.
    const k = 1 - Math.exp(-dt * 9);
    settling = false;
    for (const [id, d] of dots) {
      if (!seen.has(id)) {
        if (d.cust.tEnd == null) { d.el.remove(); dots.delete(id); continue; } // moved out of view
        if (!d.leaving) {
          d.leaving = true;
          d.tx = d.x;
          d.ty = d.y - 14;
          d.el.setAttribute("class", "cust srv leaving");
        }
      }
      d.x += (d.tx - d.x) * k;
      d.y += (d.ty - d.y) * k;
      if (d.leaving) {
        d.op = (d.op ?? 1) - dt * 2.2;
        if (d.op <= 0) { d.el.remove(); dots.delete(id); continue; }
        d.el.setAttribute("opacity", d.op.toFixed(2));
      }
      if (Math.abs(d.tx - d.x) + Math.abs(d.ty - d.y) > 0.3 || d.leaving) settling = true;
      d.el.setAttribute("cx", d.x.toFixed(2));
      d.el.setAttribute("cy", d.y.toFixed(2));
    }

    $("sim-clock").textContent = `⏱ ${num(t, t < 100 ? 1 : 0)} min`;
    $("sim-count").textContent = `👥 ${sim.nSys.toLocaleString("en-US")} in shop`;
  }

  // ── numbers and charts ───────────────────────────────────────────────
  function theoryNow() {
    return Q.theory({ lam: P.lam / 60, mu: 1 / P.svcMin, c: P.c, arr: P.arr, svc: P.svc, layout: P.layout, choice: P.choice });
  }

  function pushW() {
    const s = sim.stats();
    if (s.started) wSeries.push([sim.t, s.Wq]);
    if (wSeries.length > 1500) wSeries = wSeries.filter((_, i) => i % 2 === 0 || i === wSeries.length - 1);
  }

  function renderStats(force) {
    const th = theoryNow();
    const s = sim.stats();
    $("sim-model").textContent = th.kendall;
    const rho = th.rho;
    const cls = rho >= 1 ? "bad" : rho >= 0.9 ? "warn" : "ok";
    $("sim-load").className = "ql-load " + cls;
    $("sim-load").innerHTML = `ρ = λ / (c·μ) = ${P.lam} / (${P.c} × ${num(60 / P.svcMin, 1)}) = <b>${num(rho, 2)}</b>
      <span class="ql-meter"><i style="width:${Math.min(100, rho * 100).toFixed(1)}%"></i></span>`;

    const has = th.formula;
    const tv = (x) => (has ? num(x) : "—");
    const rows = [
      ["People in the shop", "L", num(s.L), tv(th.L)],
      ["People in line", "L<sub>q</sub>", num(s.Lq), tv(th.Lq)],
      ["Time in the shop (min)", "W", num(s.W), tv(th.W)],
      ["Wait in line (min)", "W<sub>q</sub>", num(s.Wq), tv(th.Wq)],
      ["Chance of waiting", "P<sub>wait</sub>", pct(s.Pwait), th.Pwait == null ? "—" : pct(th.Pwait)],
      ["Barista utilization", "ρ", pct(s.util), pct(Math.min(1, th.rho))],
    ];
    const head = has ? (th.exact ? `Theory (${esc(th.kendall)})` : "Theory (approx.)") : "Theory";
    $("sim-table").innerHTML = `<thead><tr><th class="text">Measure</th><th class="text"></th><th>Measured</th><th>${head}</th></tr></thead><tbody>${rows
      .map(([a, b, m, t]) => `<tr><td class="text">${a}</td><td class="text ql-sym">${b}</td><td>${m}</td><td>${t}</td></tr>`)
      .join("")}</tbody>`;
    $("sim-since").textContent = `${s.started.toLocaleString("en-US")} customers over ${num(s.T, 0)} min` + (sim.st.t0 > 0 ? ` (since the change at ${num(sim.st.t0, 0)} min)` : "");

    let alert = "";
    if (!th.stable) {
      alert = `<p class="alert error">ρ ≥ 1: customers arrive faster than the baristas can serve them. The line grows without limit and there is no steady state, so no formula applies.</p>`;
    } else if (rho >= 0.9) {
      alert = `<p class="alert warning">ρ is close to 1: the line swings wildly, and the measured averages need many thousands of customers to settle. Try ⏩.</p>`;
    }
    $("sim-alert").innerHTML = alert;

    let note;
    if (!has) {
      const shared = Q.theory({ lam: P.lam / 60, mu: 1 / P.svcMin, c: P.c, arr: P.arr, svc: P.svc });
      const rnd = Q.theory({ lam: P.lam / 60, mu: 1 / P.svcMin, c: P.c, arr: P.arr, svc: P.svc, layout: "separate", choice: "random" });
      note = `“Join the shortest line” has no simple formula. It lands between one shared line (W<sub>q</sub> ≈ ${num(shared.Wq)} min) and picking a line at random (W<sub>q</sub> ≈ ${num(rnd.Wq)} min).`;
    } else if (th.exact) {
      note = P.layout === "separate" && P.c > 1
        ? `Each line is its own single-barista queue getting 1/${P.c} of the customers.`
        : P.arr === "random" && P.svc === "random"
          ? (P.c === 1 ? "M/M/1 formulas: W<sub>q</sub> = ρ/(1 − ρ) × service time." : "M/M/c formulas, with the Erlang C probability of waiting.")
          : P.arr === "clock" && P.svc === "clock" ? "Nothing is random, so as long as ρ < 1 nobody ever waits." : "Pollaczek–Khinchine formula for random arrivals and any service times (M/G/1).";
    } else {
      note = "Approximation (Kingman / Allen–Cunneen): the M/M/c wait × (c<sub>a</sub>² + c<sub>s</sub>²)/2. No exact formula exists for these settings.";
    }
    $("sim-note").innerHTML = note;

    // Little's law
    $("little-l").textContent = num(s.L);
    $("little-lw").textContent = num(s.lam * s.W);
    const measured = !Number.isNaN(s.W);
    $("little-lw-unit").textContent = measured ? `people = ${num(s.lam, 3)} /min × ${num(s.W)} min` : "customers/min × min";
    $("little-detail").innerHTML = measured
      ? `Units: (customers per minute) × (minutes) = customers. Measured λ = ${num(s.lam, 3)} per minute (${num(s.lam * 60, 1)} per hour), W = ${num(s.W)} min.`
      : "Press Play to measure.";

    if (force || !document.hidden) renderCharts(th);
  }

  function renderCharts(th) {
    if (!globalThis.Plotly || !active) return;
    const c = MG.theme.colors();
    const tr = sim.trace;
    const x0 = Math.max(0, sim.t - 240);
    const xs = [];
    const ys = [];
    let i0 = tr.length - 1;
    while (i0 > 0 && tr[i0][0] > x0) i0--; // one point before the window, so the step line starts at its left edge
    for (let i = i0; i < tr.length; i++) { xs.push(tr[i][0]); ys.push(tr[i][1]); }
    xs.push(sim.t);
    ys.push(sim.nSys);
    const range = [x0, Math.max(30, sim.t)];
    const base = { margin: { l: 44, r: 12, t: 8, b: 40 }, height: 240, showlegend: true, legend: { orientation: "h", y: 1.12, x: 0 } };
    const hline = (y, name) => ({ x: range, y: [y, y], mode: "lines", name, line: { color: c.text, dash: "dash", width: 1.5 }, hoverinfo: "skip" });

    const nTraces = [{ x: xs, y: ys, mode: "lines", line: { shape: "hv", color: Q.color("--ql-line"), width: 1.6 }, name: "In the shop", fill: "tozeroy", fillcolor: Q.color("--ql-line-fill") }];
    if (th.formula && th.stable) nTraces.push(hline(th.L, "Theory L"));
    MG.plot($("chart-n"), nTraces, { ...base, xaxis: { title: "minutes", range }, yaxis: { rangemode: "tozero", title: "people" } }, { displayModeBar: false });

    const wTraces = [{ x: wSeries.map((p) => p[0]), y: wSeries.map((p) => p[1]), mode: "lines", line: { color: c.accent, width: 2 }, name: "Measured average" }];
    const wRange = [wSeries.length ? wSeries[0][0] : 0, Math.max(30, sim.t)];
    if (th.formula && th.stable) wTraces.push({ ...hline(th.Wq, "Theory W<sub>q</sub>"), x: wRange });
    MG.plot($("chart-w"), wTraces, { ...base, xaxis: { title: "minutes", range: wRange }, yaxis: { rangemode: "tozero", title: "minutes" } }, { displayModeBar: false });
  }

  // ── tab hooks ────────────────────────────────────────────────────────
  Q.views.simulate = {
    onShow() { active = true; renderStats(true); startLoop(); },
    onHide() { active = false; setPlaying(false); },
    onTheme() { if (active) renderStats(true); },
  };

  syncInputs();
  syncSpeed();
  build(true);
  startLoop();
})();
