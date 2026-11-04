# Course-Apps

Apps and minigames used as in-class support for operations, supply chain and
optimization courses.

## Website (maintained)

**https://vincentalboyer.github.io/Course-Apps/**

Browser versions of the optimization minigames. They run entirely in each
student's browser, so a whole class can play at once, with nothing to install
and no sign-in.

| Game | Topic |
|---|---|
| [📦 Greedy Bin Packing](https://vincentalboyer.github.io/Course-Apps/binpacking/) | Greedy heuristics, with an instance generator and a grader |
| [🧬 GA Word Game](https://vincentalboyer.github.io/Course-Apps/ga-wordgame/) | Genetic algorithms |
| [🔀 Tabu Search: The Grid Game](https://vincentalboyer.github.io/Course-Apps/tabu-search/) | Tabu search |
| [⛰️ Peak and Valley](https://vincentalboyer.github.io/Course-Apps/peak-and-valley/) | Exhaustive vs. local search vs. greedy |

Source and details are in [`website/`](website).

## Streamlit apps (no longer maintained)

> ⚠️ The Streamlit apps in [`streamlit-apps/`](streamlit-apps) and
> [`Greedy_BinPacking_App/`](Greedy_BinPacking_App) are **no longer
> maintained**. They are kept for reference and still run, but they won't
> receive fixes or updates. Four of them have a web version above, which gives
> the same games for the same game codes.

| App | Web version |
|---|---|
| [`Greedy_BinPacking_App`](Greedy_BinPacking_App) | [Greedy Bin Packing](https://vincentalboyer.github.io/Course-Apps/binpacking/) |
| [`GA_WordGame_App`](streamlit-apps/GA_WordGame_App) | [GA Word Game](https://vincentalboyer.github.io/Course-Apps/ga-wordgame/) |
| [`TabuSearch_GridGame_App`](streamlit-apps/TabuSearch_GridGame_App) | [Tabu Search](https://vincentalboyer.github.io/Course-Apps/tabu-search/) |
| [`ExhaustiveVsLocalSearch_App`](streamlit-apps/ExhaustiveVsLocalSearch_App) | [Peak and Valley](https://vincentalboyer.github.io/Course-Apps/peak-and-valley/) |
| [`ERP_App`](streamlit-apps/ERP_App) | — |
| [`EGEL-Area2`](streamlit-apps/EGEL-Area2) | — |
| [`Kids_MathWriting_App`](streamlit-apps/Kids_MathWriting_App) | — |
| [`Project_Scheduling_App`](streamlit-apps/Project_Scheduling_App) | — |

Older, retired apps are in [`streamlit-apps/Archive`](streamlit-apps/Archive).
See [`streamlit-apps/README.md`](streamlit-apps/README.md) for what each app
does and how to run it.

## Layout

```text
website/          the maintained website (GitHub Pages)
streamlit-apps/   Streamlit apps, no longer maintained
  Archive/        older, retired apps
  tests/          tests for the Streamlit game logic
Greedy_BinPacking_App/   Streamlit bin packing app, no longer maintained;
                         kept at the root so binpacking.streamlit.app keeps working
```

## License

MIT. See [LICENSE](LICENSE).
