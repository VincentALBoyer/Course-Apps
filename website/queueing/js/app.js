/* Queue Lab — tabs and concepts. Each tab's controller registers in MG.QL.views. */
(function () {
  "use strict";
  const { $ } = MG;
  const Q = MG.QL;

  const CONCEPTS = [
    ["Arrival rate λ", "How many customers arrive per unit of time, on average. <b>Random</b> arrivals (a Poisson process) have exponential gaps: many short gaps and a few long ones, so customers come in bunches."],
    ["Service rate μ", "How many customers <b>one</b> barista serves per unit of time: μ = 1 / mean service time. A 1.5-minute drink means μ = 40 per hour."],
    ["Utilization ρ = λ / (c·μ)", "The share of time the baristas are busy, also called the load or traffic intensity. ρ = 0.75 means the baristas need 75% of their capacity to keep up with the customers."],
    ["Stability: ρ < 1", "If customers arrive faster than the baristas can serve them (ρ ≥ 1), the line grows forever. ρ = 0.99 is stable, but the line is long and swings wildly."],
    ["L, L<sub>q</sub>, W, W<sub>q</sub>", "<b>L</b>: average number of customers in the shop (in line + being served). <b>L<sub>q</sub></b>: average number in line. <b>W</b>: average time a customer spends in the shop. <b>W<sub>q</sub></b>: average wait in line. W = W<sub>q</sub> + 1/μ."],
    ["Little's law L = λ·W", "Average number in the system = arrival rate × average time in the system. It holds for <b>any</b> stable queue: any distributions, any number of servers, any line rule. Also L<sub>q</sub> = λ·W<sub>q</sub>. Know two of the three and you get the third."],
    ["Kendall notation A/S/c", "Arrivals / Service / number of servers. <b>M</b> = Markovian (random, exponential), <b>D</b> = deterministic (clockwork), <b>E<sub>4</sub></b> = Erlang-4 (steadier than random), <b>G</b> = general. M/M/1 = random arrivals, random service, one server."],
    ["M/M/1 formulas", "ρ = λ/μ, L<sub>q</sub> = ρ² / (1 − ρ), W<sub>q</sub> = ρ / (1 − ρ) × service time, P(wait) = ρ. At ρ = 0.5 you wait one service time on average; at 0.9, nine; at 0.99, ninety-nine."],
    ["M/M/c and Erlang C", "With c baristas and offered load a = λ/μ, the chance an arriving customer has to wait is the <b>Erlang C</b> formula C(c, a). Then L<sub>q</sub> = C · ρ / (1 − ρ) and W<sub>q</sub> = L<sub>q</sub> / λ."],
    ["Variability and Kingman", "For one server, <b>W<sub>q</sub> ≈ ρ/(1 − ρ) · (c<sub>a</sub>² + c<sub>s</sub>²)/2 · service time</b>, where c<sub>a</sub> and c<sub>s</sub> are the coefficients of variation (std / mean) of the gaps between arrivals and of the service times. Random: c² = 1; steady (Erlang-4): ¼; clockwork: 0. It is exact for random arrivals (Pollaczek–Khinchine). With c servers, the app multiplies the M/M/c wait by the same factor (Allen–Cunneen)."],
    ["Pooling", "One shared line feeding c baristas beats c separate lines at the same load: no barista sits idle while someone waits in another line. That's why banks and airports use one snake line. Letting customers pick the shortest line helps, but doesn't fully catch up."],
    ["Economies of scale", "At the same load ρ, more servers means shorter waits: two baristas at ρ = 0.9 give a much shorter wait than one barista at ρ = 0.9. Big systems can run busier for the same service."],
    ["Steady state vs transient", "The formulas give long-run averages. A simulation starts empty and is noisy, especially near ρ = 1: it can take many thousands of customers before the measured averages settle. A café whose demand changes every hour may never reach steady state."],
    ["Staffing trade-off", "Each extra barista costs a wage but cuts waiting. The best staffing balances the two: total cost = wages + cost of waiting. Because waits explode near ρ = 1, the cheapest plan usually keeps ρ well below 1 in the rush hours."],
  ];
  $("concepts").innerHTML = CONCEPTS.map(([t, b]) => `<details><summary>${t}</summary><p>${b}</p></details>`).join("");

  // ── tabs ─────────────────────────────────────────────────────────────
  const MODES = ["simulate", "explore", "staffing"];
  const tabs = document.querySelectorAll(".modes button");
  let current = null;
  function setMode(mode) {
    if (!MODES.includes(mode)) mode = "simulate";
    if (current && current !== mode) Q.views[current].onHide();
    current = mode;
    tabs.forEach((b) => b.setAttribute("aria-selected", String(b.dataset.mode === mode)));
    for (const m of MODES) $("mode-" + m).hidden = m !== mode;
    Q.views[mode].onShow();
    document.querySelectorAll(`#mode-${mode} .js-plotly-plot`).forEach((c) => Plotly.Plots.resize(c));
    try { history.replaceState(null, "", "#" + mode); } catch (e) { /* file:// or sandboxed */ }
  }
  tabs.forEach((b) => b.addEventListener("click", () => setMode(b.dataset.mode)));
  window.addEventListener("hashchange", () => setMode(location.hash.slice(1)));
  MG.theme.onChange(() => Q.views[current].onTheme());
  setMode(location.hash.slice(1));
})();
