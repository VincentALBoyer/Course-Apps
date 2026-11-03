# MyStreamlitApp

A collection of Streamlit-based teaching simulations and minigames for operations, supply chain, and optimization courses.

## Applications

- **[ERP_App](ERP_App)**: Integrated ERP simulation ("Global Gadgets Inc.") covering SRM, CRM, Inventory & Ops, and Finance modules on a shared game state, plus a built-in "What is an ERP?" lesson page.
- **[Greedy_BinPacking_App](Greedy_BinPacking_App)**: 2D bin-packing minigame teaching greedy heuristics — drag-and-drop game mode, offline Excel challenge generator, and a scoring/grading mode for submitted layouts.
- **[ExhaustiveVsLocalSearch_App](ExhaustiveVsLocalSearch_App)**: Minigame contrasting exhaustive vs. local search over a hidden 1-D landscape, built for an "Computational Complexity and Basic Optimization Concepts" course session. See its own [README](ExhaustiveVsLocalSearch_App/README.md) for details.
- **[GA_WordGame_App](GA_WordGame_App)**: Hands-on Genetic Algorithm minigame — hand-run selection, crossover, and mutation to evolve a hidden word. See its own [README](GA_WordGame_App/README.md) for details.
- **[TabuSearch_GridGame_App](TabuSearch_GridGame_App)**: Tabu Search minigame — build a max-sum path on a grid, then improve it with swap moves, tabu tenure, and aspiration, watching how tenure=0 cycles and how auto-play escapes local optima. See its own [README](TabuSearch_GridGame_App/README.md) for details.
- **[EGEL-Area2](EGEL-Area2)**: "Mega-Factory: Lockdown" — an escape-room-style review game (in Spanish) for EGEL-IINDU exam preparation.
- **[Kids_MathWriting_App](Kids_MathWriting_App)**: "Aventura Mágica: Números y Letras" — a colorful, mascot-guided game (in Spanish) for young kids to practice addition, multiplication as equal groups, and Spanish spelling. See its own [README](Kids_MathWriting_App/README.md) for details.

Older/retired apps (CRM, SRM, ERP_Sim, Project Scheduling, etc.) live under [Archive](Archive) and are not actively maintained.

## Website (no install)

Browser versions of the optimization minigames are published on GitHub Pages at
**https://vincentalboyer.github.io/MyStreamlitApp/**: Greedy Bin Packing, GA Word Game,
Tabu Search, and Peak and Valley (the web name of Exhaustive vs. Local Search). They run
entirely in the browser, so a whole class can play at once, and game codes give the
same games as the Streamlit versions. Source and details are in [website](website).

## Getting Started

Each app is self-contained; install its `requirements.txt` and run it directly with Streamlit, e.g.:
```bash
pip install -r ERP_App/requirements.txt
streamlit run ERP_App/app.py
```

```bash
streamlit run Greedy_BinPacking_App/app.py
streamlit run ExhaustiveVsLocalSearch_App/app.py
streamlit run GA_WordGame_App/app.py
streamlit run TabuSearch_GridGame_App/app.py
streamlit run EGEL-Area2/streamlit_app.py
streamlit run Kids_MathWriting_App/app.py
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
