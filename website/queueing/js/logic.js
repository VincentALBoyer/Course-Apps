/* Queue Lab: queueing formulas, the discrete-event simulator and the
 * staffing challenge's day. No DOM here; the tabs live in the other files.
 * Time is in minutes everywhere in this file. */
(function () {
  "use strict";
  const MG = (globalThis.MG = globalThis.MG || {});
  const QL = (MG.QL = MG.QL || {});

  // ── Variability of gaps between arrivals / of service times ──────────
  // cv2 = squared coefficient of variation (variance / mean²).
  const expo = (rng) => -Math.log(1 - rng.random());
  const VAR = {
    random: { label: "Random", kendall: "M", cv2: 1, draw: (rng, mean) => expo(rng) * mean },
    steady: { label: "Steady", kendall: "E₄", cv2: 0.25, draw: (rng, mean) => ((expo(rng) + expo(rng) + expo(rng) + expo(rng)) * mean) / 4 },
    clock: { label: "Clockwork", kendall: "D", cv2: 0, draw: (rng, mean) => mean },
  };

  // ── Formulas ─────────────────────────────────────────────────────────
  /** Erlang C: probability an arrival waits in M/M/c, offered load a = λ/μ < c. */
  function erlangC(c, a) {
    let term = 1;
    let sum = 1; // Σ_{k<c} a^k / k!
    for (let k = 1; k < c; k++) { term *= a / k; sum += term; }
    const top = (term * a) / c / (1 - a / c); // a^c / c! · 1 / (1 − ρ)
    return top / (sum + top);
  }

  /** M/M/c steady state. lam, mu per minute. */
  function mmc(lam, mu, c) {
    const rho = lam / (c * mu);
    if (!(rho < 1)) return { rho, stable: false, Pwait: 1, Lq: Infinity, Wq: Infinity };
    const Pwait = erlangC(c, lam / mu);
    const Lq = (Pwait * rho) / (1 - rho);
    return { rho, stable: true, Pwait, Lq, Wq: Lq / lam };
  }

  /**
   * Long-run averages for the café's settings. lam, mu per minute.
   * Shared line: exact for M/M/c, M/G/1 (Pollaczek–Khinchine) and D/D/c;
   * otherwise the Allen–Cunneen approximation Wq ≈ Wq(M/M/c)·(ca² + cs²)/2.
   * Separate lines with random choice: c independent single-server queues.
   * Separate lines with "join the shortest": no closed form (formula: false).
   */
  function theory({ lam, mu, c, arr = "random", svc = "random", layout = "shared", choice = "shortest" }) {
    const ca2 = VAR[arr].cv2;
    const cs2 = VAR[svc].cv2;
    const rho = lam / (c * mu);
    const out = { rho, stable: rho < 1, formula: true, exact: false, kendall: "", Pwait: null };
    const sep = layout === "separate" && c > 1;
    if (sep) {
      out.kendall = `${c} lines × ${arr === "random" ? "M" : "G"}/${VAR[svc].kendall}/1`;
      if (choice !== "random") { out.formula = false; return out; }
      // Randomly splitting a stream into c makes each part more random.
      const ca2Line = ca2 / c + (1 - 1 / c);
      const base = mmc(lam / c, mu, 1);
      out.Wq = base.Wq * ((ca2Line + cs2) / 2);
      out.exact = arr === "random";
      if (out.exact && out.stable) out.Pwait = rho;
    } else {
      out.kendall = `${VAR[arr].kendall}/${VAR[svc].kendall}/${c}`;
      const base = mmc(lam, mu, c);
      out.Wq = base.Wq * ((ca2 + cs2) / 2);
      out.exact = (ca2 === 1 && (cs2 === 1 || c === 1)) || (ca2 === 0 && cs2 === 0);
      if (out.stable) {
        if (ca2 === 1 && cs2 === 1) out.Pwait = base.Pwait;
        else if (ca2 === 1 && c === 1) out.Pwait = rho;
        else if (ca2 === 0 && cs2 === 0) out.Pwait = 0;
      }
    }
    if (!out.stable) { out.Wq = Infinity; out.Pwait = 1; }
    if (ca2 === 0 && cs2 === 0 && out.stable) out.Wq = 0;
    out.Lq = lam * out.Wq;
    out.W = out.Wq + 1 / mu;
    out.L = lam * out.W;
    return out;
  }

  // ── Discrete-event simulator ─────────────────────────────────────────
  /**
   * FCFS multi-server queue with one shared line or a line per server.
   * opts:
   *   maxServers   number of server slots
   *   staff        servers on shift at t = 0 (or staffAt(0))
   *   staffAt(t)   servers on shift after each time in shiftTimes
   *   arrivals()   returns the next {t, svc} (absolute, increasing) or null
   *   layout       "shared" | "separate";  choice "shortest" | "random"
   *   lineRng      PyRandom for random line choice
   *   keep         keep every customer in .all;  trace  record [t, inSystem, inLine]
   *   traceWindow  minutes of trace to keep (default: all)
   * A server going off shift finishes its customer, then stops.
   */
  class QueueSim {
    constructor(o) {
      this.layout = o.layout || "shared";
      this.choice = o.choice || "shortest";
      this.lineRng = o.lineRng || null;
      this.maxC = o.maxServers;
      this.staffAt = o.staffAt || null;
      this.shifts = (o.shiftTimes || []).slice();
      this.source = o.arrivals;
      this.traceWindow = o.traceWindow || Infinity;
      this.t = 0;
      this.c = o.staff != null ? o.staff : this.staffAt(0);
      this.servers = Array.from({ length: this.maxC }, () => ({ cust: null, until: Infinity }));
      this.queues = Array.from({ length: this.layout === "shared" ? 1 : this.maxC }, () => []);
      this.nextId = 0;
      this.nSys = 0;
      this.nQ = 0;
      this.busy = 0;
      this.maxQ = 0;
      this.all = o.keep ? [] : null;
      this.trace = o.trace ? [[0, 0, 0]] : null;
      this.next = this.source();
      this.resetStats();
    }

    /** Start measuring again from now; only customers arriving from now on count for waits. */
    resetStats() {
      this.st = { t0: this.t, fromId: this.nextId, areaN: 0, areaQ: 0, areaBusy: 0, areaStaff: 0, arrived: 0, started: 0, waited: 0, sumWq: 0, done: 0, sumW: 0 };
    }

    stats() {
      const s = this.st;
      const T = this.t - s.t0;
      return {
        T, arrived: s.arrived, started: s.started, done: s.done,
        L: T > 0 ? s.areaN / T : NaN,
        Lq: T > 0 ? s.areaQ / T : NaN,
        util: s.areaStaff > 0 ? s.areaBusy / s.areaStaff : NaN,
        lam: T > 0 ? s.arrived / T : NaN,
        Wq: s.started ? s.sumWq / s.started : NaN,
        W: s.done ? s.sumW / s.done : NaN,
        Pwait: s.started ? s.waited / s.started : NaN,
      };
    }

    /** Process every event up to time tEnd (Infinity: until nothing is left). */
    advance(tEnd) {
      const sv = this.servers;
      for (;;) {
        const tA = this.next ? this.next.t : Infinity;
        let tD = Infinity;
        let sD = -1;
        for (let s = 0; s < this.maxC; s++) if (sv[s].until < tD) { tD = sv[s].until; sD = s; }
        const tS = this.shifts.length ? this.shifts[0] : Infinity;
        const t = Math.min(tA, tD, tS);
        if (t === Infinity || t > tEnd) break;
        this._to(t);
        if (tD === t) this._depart(sD);
        else if (tS === t) { this.shifts.shift(); this.setStaff(this.staffAt(t)); }
        else this._arrive();
      }
      if (tEnd !== Infinity) this._to(tEnd);
    }

    setStaff(c) {
      c = Math.max(1, Math.min(this.maxC, c));
      const old = this.c;
      this.c = c;
      if (this.layout === "shared") {
        const q = this.queues[0];
        for (let s = 0; s < c && q.length; s++) if (!this.servers[s].cust) { this.nQ--; this._start(s, q.shift()); }
      } else if (c < old) {
        // The lines of baristas going off shift rejoin the open lines, oldest first.
        const moved = [];
        for (let s = c; s < old; s++) { moved.push(...this.queues[s]); this.queues[s] = []; }
        moved.sort((a, b) => a.tArr - b.tArr);
        for (const cu of moved) {
          const k = this._shortest();
          cu.line = k;
          if (!this.servers[k].cust) { this.nQ--; this._start(k, cu); } else this.queues[k].push(cu);
        }
      }
      this._mark();
    }

    _to(t) {
      const dt = t - this.t;
      if (dt > 0) {
        const s = this.st;
        s.areaN += this.nSys * dt;
        s.areaQ += this.nQ * dt;
        s.areaBusy += this.busy * dt;
        s.areaStaff += this.c * dt;
        this.t = t;
      }
    }

    _mark() {
      const tr = this.trace;
      if (!tr) return;
      tr.push([this.t, this.nSys, this.nQ]);
      if (this.traceWindow !== Infinity && tr[0][0] < this.t - this.traceWindow - 60) {
        const cut = this.t - this.traceWindow;
        let i = 0;
        while (i < tr.length - 1 && tr[i + 1][0] < cut) i++;
        tr.splice(0, i);
      }
    }

    _shortest() {
      let k = 0;
      let best = Infinity;
      for (let s = 0; s < this.c; s++) {
        const len = this.queues[s].length + (this.servers[s].cust ? 1 : 0);
        if (len < best) { best = len; k = s; }
      }
      return k;
    }

    _arrive() {
      const a = this.next;
      this.next = this.source();
      const cu = { id: this.nextId++, tArr: this.t, svc: a.svc, tStart: null, tEnd: null, server: -1, line: 0, tag: a.tag };
      if (this.all) this.all.push(cu);
      this.nSys++;
      if (cu.id >= this.st.fromId) this.st.arrived++;
      if (this.layout === "shared") {
        let s = -1;
        for (let k = 0; k < this.c; k++) if (!this.servers[k].cust) { s = k; break; }
        if (s >= 0) this._start(s, cu); else { this.queues[0].push(cu); this.nQ++; }
      } else {
        const k = this.choice === "random" ? Math.floor(this.lineRng.random() * this.c) : this._shortest();
        cu.line = k;
        if (!this.servers[k].cust) this._start(k, cu); else { this.queues[k].push(cu); this.nQ++; }
      }
      if (this.nQ > this.maxQ) this.maxQ = this.nQ;
      this._mark();
    }

    _start(s, cu) {
      const srv = this.servers[s];
      cu.tStart = this.t;
      cu.server = s;
      srv.cust = cu;
      srv.until = this.t + cu.svc;
      this.busy++;
      if (cu.id >= this.st.fromId) {
        const w = this.t - cu.tArr;
        this.st.started++;
        this.st.sumWq += w;
        if (w > 1e-9) this.st.waited++;
      }
    }

    _depart(s) {
      const srv = this.servers[s];
      const cu = srv.cust;
      cu.tEnd = this.t;
      srv.cust = null;
      srv.until = Infinity;
      this.busy--;
      this.nSys--;
      if (cu.id >= this.st.fromId) { this.st.done++; this.st.sumW += cu.tEnd - cu.tArr; }
      if (s < this.c) {
        const q = this.queues[this.layout === "shared" ? 0 : s];
        if (q.length) { this.nQ--; this._start(s, q.shift()); }
      }
      this._mark();
    }
  }

  /** Simulate n customers (after a warm-up) with mean service time 1. */
  function simulatePoint({ rho, c, arr, svc, layout = "shared", choice = "random", n = 20000, warm = 2000 }) {
    const lam = rho * c;
    const rA = new MG.PyRandom(null);
    const rS = new MG.PyRandom(null);
    const rL = new MG.PyRandom(null);
    let t = 0;
    const sim = new QueueSim({
      maxServers: c, staff: c, layout, choice, lineRng: rL,
      arrivals: () => { t += VAR[arr].draw(rA, 1 / lam); return { t, svc: VAR[svc].draw(rS, 1) }; },
    });
    while (sim.nextId < warm) sim.advance(sim.t + 50);
    sim.resetStats();
    while (sim.nextId < warm + n) sim.advance(sim.t + 50);
    return sim.stats();
  }

  // ── Staffing challenge ───────────────────────────────────────────────
  const DAY = {
    startHour: 7,
    hours: 8,
    wage: 18, // $ per barista per hour
    waitCost: 0.3, // $ per customer-minute in line (lost goodwill)
    maxStaff: 8,
    target: 3, // service-level threshold, minutes in line
  };
  // A café's day, customers per hour: breakfast rush, quiet morning, lunch rush.
  const SHAPE = [70, 115, 85, 55, 65, 105, 80, 45];

  /** The day for a game code: demand per hour, service time, and every customer. */
  function makeDay(code) {
    const seed = MG.codeToSeed(code);
    const rng = new MG.PyRandom(seed);
    const svcMin = rng.choice([1.5, 2, 2.5]);
    const scale = 2 / svcMin; // keep the needed staff in the same range for every service time
    const lamH = SHAPE.map((v) => Math.max(10, 5 * Math.round((v * scale * rng.uniform(0.8, 1.2)) / 5)));
    const rA = new MG.PyRandom(seed * 3n + 1n);
    const rS = new MG.PyRandom(seed * 3n + 2n);
    const customers = [];
    for (let h = 0; h < DAY.hours; h++) {
      let t = h * 60;
      for (;;) {
        t += expo(rA) * (60 / lamH[h]);
        if (t >= (h + 1) * 60) break;
        customers.push({ t, svc: expo(rS) * svcMin, tag: h });
      }
    }
    return { code, svcMin, lamH, customers };
  }

  /** M/M/c forecast of one hour with c baristas: $ wages + $ waiting. */
  function forecastHour(day, h, c) {
    const r = mmc(day.lamH[h] / 60, 1 / day.svcMin, c);
    const waitMin = r.stable ? day.lamH[h] * r.Wq : Infinity; // customer-minutes in line
    return { rho: r.rho, stable: r.stable, Wq: r.Wq, wages: DAY.wage * c, wait: waitMin * DAY.waitCost, cost: DAY.wage * c + waitMin * DAY.waitCost };
  }

  /** Per hour, the staffing with the lowest M/M/c forecast cost. */
  function formulaPlan(day) {
    return day.lamH.map((_, h) => {
      let best = DAY.maxStaff;
      let bestCost = Infinity;
      for (let c = 1; c <= DAY.maxStaff; c++) {
        const f = forecastHour(day, h, c);
        if (f.cost < bestCost - 1e-9) { bestCost = f.cost; best = c; }
      }
      return best;
    });
  }

  /** Run the day with a staffing plan on the day's customers (same for every plan). */
  function runDay(day, plan) {
    let i = 0;
    const H = DAY.hours;
    const sim = new QueueSim({
      maxServers: DAY.maxStaff,
      staffAt: (t) => plan[Math.min(H - 1, Math.floor(t / 60 + 1e-9))],
      shiftTimes: Array.from({ length: H - 1 }, (_, h) => (h + 1) * 60),
      arrivals: () => (i < day.customers.length ? day.customers[i++] : null),
      keep: true,
      trace: true,
    });
    sim.advance(Infinity);
    const hours = plan.map((c, h) => ({ h, c, n: 0, sumWait: 0, maxWait: 0 }));
    let sumWait = 0;
    let within = 0;
    for (const cu of sim.all) {
      const w = cu.tStart - cu.tArr;
      const hr = hours[cu.tag];
      hr.n++;
      hr.sumWait += w;
      if (w > hr.maxWait) hr.maxWait = w;
      sumWait += w;
      if (w <= DAY.target) within++;
    }
    for (const hr of hours) { hr.wages = DAY.wage * hr.c; hr.wait = hr.sumWait * DAY.waitCost; }
    const wages = plan.reduce((a, c) => a + c * DAY.wage, 0);
    const waitCost = sumWait * DAY.waitCost;
    const n = sim.all.length;
    return {
      plan: plan.slice(), hours, n, wages, waitCost, cost: wages + waitCost,
      avgWait: n ? sumWait / n : 0, within: n ? within / n : 1, maxQ: sim.maxQ,
      closed: sim.t, trace: sim.trace,
    };
  }

  // ── Formatting ───────────────────────────────────────────────────────
  /** Short number: "—" for missing, "∞" for unbounded, 2–3 significant digits otherwise. */
  function num(x, d) {
    if (x == null || Number.isNaN(x)) return "—";
    if (!Number.isFinite(x)) return "∞";
    if (d != null) return x.toFixed(d);
    const a = Math.abs(x);
    return a < 10 ? x.toFixed(2) : a < 100 ? x.toFixed(1) : Math.round(x).toLocaleString("en-US");
  }
  const pct = (x) => (x == null || Number.isNaN(x) ? "—" : Math.round(x * 100) + "%");
  const money = (x) => (Number.isFinite(x) ? "$" + Math.round(x).toLocaleString("en-US") : "∞");
  const clock = (hour) => `${Math.floor(hour)}:${String(Math.round((hour % 1) * 60)).padStart(2, "0")}`;

  /** Read one of this page's CSS color tokens (for Plotly). */
  function color(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }

  Object.assign(QL, { VAR, erlangC, mmc, theory, QueueSim, simulatePoint, DAY, makeDay, forecastHour, formulaPlan, runDay, num, pct, money, clock, color, views: QL.views || {} });
})();
