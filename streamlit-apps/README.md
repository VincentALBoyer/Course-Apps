# Streamlit apps (no longer maintained)

> ⚠️ **These apps are no longer maintained.** They are kept for reference and
> still run, but they won't receive fixes or updates. Each live app shows a
> banner saying so.
>
> The optimization minigames now live on the website,
> **https://vincentalboyer.github.io/Course-Apps/** (source in
> [`../website`](../website)). It gives the same games for the same game codes.

## Apps

| Folder | What it is | Web version |
|---|---|---|
| [`Greedy_BinPacking_App`](../Greedy_BinPacking_App) (at the repo root) | 2D bin packing minigame for greedy heuristics: drag-and-drop game, Excel challenge generator, and grader. | [Greedy Bin Packing](https://vincentalboyer.github.io/Course-Apps/binpacking/) |
| [`GA_WordGame_App`](GA_WordGame_App) | Genetic algorithm minigame: run selection, crossover and mutation by hand to evolve a hidden word. | [GA Word Game](https://vincentalboyer.github.io/Course-Apps/ga-wordgame/) |
| [`TabuSearch_GridGame_App`](TabuSearch_GridGame_App) | Tabu search minigame: build a max-sum path on a grid, then improve it with swap moves, tenure and aspiration. | [Tabu Search](https://vincentalboyer.github.io/Course-Apps/tabu-search/) |
| [`ExhaustiveVsLocalSearch_App`](ExhaustiveVsLocalSearch_App) | Exhaustive vs. local search over a hidden 1-D landscape. | [Peak and Valley](https://vincentalboyer.github.io/Course-Apps/peak-and-valley/) |
| [`ERP_App`](ERP_App) | Integrated ERP simulation ("Global Gadgets Inc.") with SRM, CRM, Inventory & Ops and Finance modules, plus a "What is an ERP?" lesson. | — |
| [`EGEL-Area2`](EGEL-Area2) | "Mega-Factory: Lockdown", an escape-room review game (in Spanish) for EGEL-IINDU exam preparation. | — |
| [`Kids_MathWriting_App`](Kids_MathWriting_App) | "Aventura Mágica: Números y Letras", a game (in Spanish) for young kids to practice addition, multiplication and spelling. | — |
| [`Project_Scheduling_App`](Project_Scheduling_App) | Project scheduling simulation (CPM, resources, drag-and-drop schedule). An identical copy is in `Archive/`. | — |

[`Archive/`](Archive) holds older, retired apps (CRM, SRM, ERP_Sim_Integrated,
Project Scheduling and others).

## Run an app

Each app has its own `requirements.txt`. From the repo root:

```bash
pip install -r streamlit-apps/GA_WordGame_App/requirements.txt
streamlit run streamlit-apps/GA_WordGame_App/app.py
```

The EGEL escape room's entry point is `streamlit-apps/EGEL-Area2/streamlit_app.py`.

## Tests

```bash
pip install pytest
pytest streamlit-apps/tests
```

## Streamlit Community Cloud

Each deployed app points to a file path in this repo. Those paths now start
with `streamlit-apps/`, for example `streamlit-apps/GA_WordGame_App/app.py`.

The bin packing app is the exception: it stays at the repo root,
`Greedy_BinPacking_App/app.py`, so its existing deployment
(binpacking.streamlit.app) keeps working.
