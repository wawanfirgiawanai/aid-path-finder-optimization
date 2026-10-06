# OptiRoute: Risk-Aware Disaster Relief Routing with a Two-Level Hybrid A\*–GA

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Data: ODbL](https://img.shields.io/badge/Data-ODbL%201.0-brightgreen.svg)](https://opendatacommons.org/licenses/odbl/1-0/)
![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB.svg)
![Node 18+](https://img.shields.io/badge/Node.js-18%2B-339933.svg)
![ICITISEE 2026](https://img.shields.io/badge/Paper-ICITISEE%202026-orange.svg)

This repository contains the web system, source code, frozen dataset, and experiment pipeline of the paper:

> W. Firgiawan, B. Amaliah, A. Saikhu, A. H. Basori, Sulfayanti, and N. Nur, "Risk-Aware Disaster Relief Routing:
> Comparing Exact, Metaheuristic, and Two-Level Hybrid A\*–GA Methods," *2026 10th International Conference on
> Information Technology, Information Systems and Electrical Engineering (ICITISEE)*, IEEE, 2026.

OptiRoute compares **A\***, **Breadth-First Search (BFS)**, a **Genetic Algorithm (GA)**, and **Ant Colony
Optimization (ACO)** under a risk-aware cost, and proposes a **two-level hybrid A\*–GA**. All methods are evaluated
on one OpenStreetMap road network of Mamuju, Indonesia, with **40 documented test cases**.

> **Disclaimer.** This is a simulation study. Only the road geometry comes from OpenStreetMap. Depots, destinations,
> agents, and road risks are simulated and do not describe a real disaster event.

![Two-level hybrid A*-GA framework](docs/figures/fig2_framework.png)

---

## Contents

1. [Overview](#1-overview)
2. [Method](#2-method)
3. [Dataset and test cases](#3-dataset-and-test-cases)
4. [Installation](#4-installation)
5. [Running the application](#5-running-the-application)
6. [Reproducing the experiments](#6-reproducing-the-experiments)
7. [Results](#7-results)
8. [Repository structure](#8-repository-structure)
9. [API reference](#9-api-reference)
10. [How to cite](#10-how-to-cite)
11. [License and acknowledgment](#11-license-and-acknowledgment)

---

## 1. Overview

After a disaster, relief vehicles must reach the affected locations quickly while avoiding hazardous roads.
Shortest-path algorithms such as A\* return an optimal route between two points, but they do not decide **which
vehicle serves which location, and in what order**. This allocation is a multi-depot vehicle routing problem
(MDVRP), which is NP-hard.

OptiRoute addresses both decisions:

| Feature | Description |
|---|---|
| Risk-aware cost | Every road segment has a length *d* (m) and a risk *r* ∈ [0, 1]; its cost is *d*(1 + *r*). |
| Baselines | A\*, BFS, path-level GA, and path-level ACO, combined with a greedy nearest-destination allocation. |
| Proposed method | Two-level hybrid: exact A\* paths (Level 1) and a GA on allocation and visiting order (Level 2). |
| Web application | Interactive map (React + Leaflet) to place depots and destinations, close roads, and compare algorithms. |
| Reproducible study | One frozen network, 40 + 4 test cases, tuned parameters, statistics, and an Excel report generated in one step. |

## 2. Method

### 2.1 Problem and cost function

The road network is an undirected graph *G* = (*V*, *E*). The cost of edge (*i*, *j*) is

```
c_ij = d_ij × (1 + r_ij)
```

Vehicles start at depots and serve the destinations on open routes. The objective is the minimum total cost over all
agent routes. Four metrics are reported for every run:

| Metric | Definition |
|---|---|
| Distance (m) | Total length Σ *d_ij* of the traversed edges |
| Risk exposure | Length-weighted mean risk Σ *d_ij r_ij* / Σ *d_ij* ∈ [0, 1] |
| Cost | Total risk-aware cost Σ *d_ij*(1 + *r_ij*) |
| Time (ms) | Wall-clock time of one complete solution, including the cost matrix |

### 2.2 Algorithms

| Algorithm | Type | Implementation |
|---|---|---|
| A\* | Exact | Haversine heuristic; admissible because *c_ij* ≥ *d_ij* ≥ *h* |
| BFS | Uninformed | Fewest edges; ignores edge cost |
| GA | Metaheuristic (path level) | Chromosome = node path; tournament selection, crossover at a shared node, sub-path mutation |
| ACO | Metaheuristic (path level) | τ^α η^β with η = 1/cost, elitist deposit, MAX–MIN bounds |
| **Hybrid A\*–GA** | **Two-level (proposed)** | Exact A\* paths + GA on allocation and visiting order |

For more than one destination, the baselines assign destinations with a greedy nearest-destination rule and route each
leg with the chosen algorithm. Dijkstra is also implemented in the code; it returns the same paths and costs as A\* and
is therefore not reported separately in the paper.

### 2.3 Two-level hybrid A\*–GA

- **Level 1 (exact paths).** A\* computes the least-cost path between every pair of key nodes (depots and
  destinations) and stores the costs in a matrix *M*. For *m* key nodes, this requires *m*(*m* − 1)/2 searches.
- **Level 2 (allocation and visiting order).** A chromosome is a permutation of the destinations with *K* − 1 agent
  separators. The GA uses:
  - fitness = total route cost read from *M*, with a penalty for idle agents under forced distribution;
  - a greedy warm start, which guarantees that the hybrid is never worse than the greedy baseline;
  - tournament selection with elitism;
  - order crossover (OX1);
  - multi-domain inversion mutation (seven variants from four cut points);
  - early stopping after a fixed number of generations without improvement.

Level 2 does not access the road graph. Source code: [`backend/hybrid.py`](backend/hybrid.py); unit tests:
[`backend/tests/test_hybrid.py`](backend/tests/test_hybrid.py).

### 2.4 Tuned parameters

Parameters were selected by random search over 24 configurations on tuning cases that are not used for evaluation
([`dataset/tuned_params.json`](dataset/tuned_params.json)).

| Algorithm | Selected parameters |
|---|---|
| GA | population 100, generations 200, crossover 0.8, mutation 0.2, tournament 3, elitism 5 |
| ACO | ants 10, iterations 50, α = 1.0, β = 1.0, evaporation 0.1 |
| Hybrid A\*–GA | population 30, generations 100, crossover 0.8, mutation 0.5, tournament 3, elitism 4, stall limit 30 |

## 3. Dataset and test cases

**Road network.** Mamuju, West Sulawesi, Indonesia; centre (−2.692, 118.898), radius 1,500 m; 455 nodes and 516 road
segments. Risk values are drawn as *r* ~ U(0, 1) with seed 42. The network is stored in
[`dataset/network/`](dataset/network/), so the application and the experiments run **offline**.

| Group | Test cases | Depots × agents | Destinations | Runs per algorithm |
|---|---|---|---|---|
| SA-SD | SA-SD-01 … 05 | 1 × 1 | 1 | 30 |
| SA-MD | SA-MD-01 … 05 | 1 × 1 | 4 | 30 |
| MA-SD | MA-SD-01 … 05 | 2 × 2 | 1 | 30 |
| MA-MD | MA-MD-01 … 05 | 2 × 2 | 4 | 30 |
| SC-05 / 10 / 20 / 30 | SC-xx-01 … 05 | 2 × 2 | 5 / 10 / 20 / 30 | 10 |
| TUNE | TUNE-A … D | — | — | parameter tuning only |

SA = single agent, MA = multiple agents, SD = single destination, MD = multiple destinations, SC = scalability.

![Test-case scenarios](docs/figures/fig1_scenarios.png)

| Location | Content |
|---|---|
| [`dataset/README.md`](dataset/README.md) | Schema of every dataset file |
| `dataset/test_cases/` | Test cases as JSON, CSV, and GeoJSON; one map per case; importable app sessions |
| [`docs/Dataset_dan_Test_Case.pdf`](docs/Dataset_dan_Test_Case.pdf) | Catalogue of every case: points, map, and results (Indonesian) |
| `dataset/SHA256SUMS` | Checksums of the frozen files |

## 4. Installation

The commands below are given for **Windows PowerShell** (the default terminal of VS Code on Windows) and for
**Linux/macOS (bash)**.

### 4.1 Prerequisites

| Tool | Version | Check |
|---|---|---|
| [Git](https://git-scm.com) | any recent version | `git --version` |
| [Python](https://www.python.org/downloads/) | **3.11** | `python --version` or `py -3.11 --version` |
| [Node.js](https://nodejs.org) | 18 or newer | `node --version` |
| Yarn | 1.22 | `yarn --version` (install with `npm install -g yarn`) |

### 4.2 Clone the repository

```bash
git clone https://github.com/wawanfirgiawanai/aid-path-finder-optimization.git
cd aid-path-finder-optimization
```

All following commands start from this project folder.

### 4.3 Backend (Python virtual environment)

The backend runs in its own virtual environment with pinned packages from
[`backend/requirements.txt`](backend/requirements.txt).

Windows (PowerShell):

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
cd ..
```

Linux/macOS:

```bash
cd backend
python3.11 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
cd ..
```

### 4.4 Frontend (React)

Windows (PowerShell):

```powershell
cd frontend
yarn.cmd install
Copy-Item .env.example .env
cd ..
```

Linux/macOS:

```bash
cd frontend
yarn install
cp .env.example .env
cd ..
```

`frontend/.env` sets `REACT_APP_BACKEND_URL=http://localhost:8001`. On Windows, `yarn.cmd` avoids the PowerShell
error *"running scripts is disabled on this system"*.

### 4.5 Verify the installation

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_hybrid.py -q      # Windows
```

```bash
backend/.venv/bin/python -m pytest backend/tests/test_hybrid.py -q                # Linux/macOS
```

The expected output is `4 passed`.

## 5. Running the application

The application has two parts that run at the same time in two terminals.

| Part | Address | Ready when the terminal shows |
|---|---|---|
| Backend (FastAPI) | http://127.0.0.1:8001 | `Uvicorn running on http://127.0.0.1:8001` |
| Frontend (React) | http://localhost:3000 | `Compiled successfully!` |

**Terminal 1: backend**

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn server:app --host 127.0.0.1 --port 8001     # Linux/macOS: .venv/bin/python
```

**Terminal 2: frontend**

```powershell
cd frontend
yarn.cmd start                                                                     # Linux/macOS: yarn start
```

Open **http://localhost:3000** in a browser. Stop each part with **Ctrl+C**.

In **VS Code**, open the project folder and press **Ctrl+Shift+B** (task *Run App (Backend + Frontend)*), or open
*Run and Debug* (`Ctrl+Shift+D`), select **OptiRoute: Full App**, and press **F5**.

### 5.1 First steps

1. Press **Initialize** to load the Mamuju network (loaded from `dataset/network/`; no internet access needed).
2. Press **Import** and select `dataset/test_cases/app_sessions/MA-MD-01.json` to load a test case of the paper.
3. Press **Compare All Algorithms** and open the **Comparison** tab.
4. Press **Run Paper Experiments** to reproduce the full study from the browser.

| Network and routes | Algorithm comparison |
|---|---|
| ![Network view](docs/images/app_network.png) | ![Comparison view](docs/images/app_comparison.png) |

### 5.2 Troubleshooting

| Problem | Solution |
|---|---|
| Port 8001 or 3000 is already in use | Close the earlier server, or in PowerShell: `Get-NetTCPConnection -LocalPort 8001,3000 -State Listen \| ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }` |
| `Router.__init__() got an unexpected keyword argument 'on_startup'` | The backend was started with a global Python; use the interpreter in `backend/.venv` |
| Buttons show "Network Error" | The backend is not running, or `frontend/.env` is missing; restart the frontend after creating it |
| **Initialize** is slow for a different location | Areas other than the default Mamuju network are downloaded from the Overpass API and need internet access |

## 6. Reproducing the experiments

**From the web application:** click **Run Paper Experiments** and then **Run all paper experiments**. The pipeline
runs parameter tuning, the 20 main cases, the 20 scalability cases, and the statistical report. Each run is saved in
`experiments/runs/<run-id>/` and never overwrites the published results.

**From the terminal** (project folder, Windows; on Linux/macOS use `backend/.venv/bin/python` and `/`):

```powershell
.\backend\.venv\Scripts\python.exe -W ignore experiments\run_experiments.py --phase all --params-file dataset\tuned_params.json --out experiments\runs\cli --jobs 8
.\backend\.venv\Scripts\python.exe -W ignore experiments\verify_dataset.py --jobs 8
```

| Option | Meaning |
|---|---|
| `--phase` | `all`, `tune`, `main`, `scale`, or `report` |
| `--params-file` | Use the frozen parameters of the paper instead of re-tuning |
| `--jobs N` | Number of worker processes |
| `--out DIR` | Write `results/` and `figures/` to `DIR` |

Costs and distances are identical on every machine because all stochastic runs are seeded; only computation times
differ. `verify_dataset.py` checks every seeded run against the published results.

| Script | Output |
|---|---|
| `experiments/run_experiments.py` | Tuning, main and scalability runs, statistics, figures, Excel workbook |
| `experiments/export_excel.py` | Rebuilds `OptiRoute_Results.xlsx` from existing results |
| `experiments/make_paper_figures.py --astar-only` | Figures of the paper |
| `experiments/make_scenario_maps.py [CASE]` | Route map of one test case |
| `experiments/build_dataset.py` | Test cases, maps, app sessions, and checksums |
| `experiments/verify_dataset.py` | Reproduction check against the published runs |

## 7. Results

All numbers below are taken from the paper and can be recomputed from [`experiments/results/`](experiments/results/).
The main scenarios use 5 test cases × 30 runs per algorithm; the scalability scenarios use 5 test cases × 10 runs
per size.

### 7.1 Main scenarios (mean cost over five test cases)

| Scenario | A\* | BFS | GA | ACO | **Hybrid A\*–GA** | Hybrid optimum hits |
|---|---:|---:|---:|---:|---:|---:|
| SA-SD | **2,147.7** | 2,212.5 | 2,177.5 | 2,218.2 | **2,147.7** | 150/150 |
| SA-MD | 6,093.3 | 7,370.2 | 6,132.9 | 6,524.7 | **5,972.9** | 150/150 |
| MA-SD | **10,400.2** | 13,116.0 | 10,717.1 | 10,753.4 | **10,400.2** | — |
| MA-MD | 8,675.1 | 10,754.8 | 8,836.2 | 8,977.0 | **7,997.4** | 150/150 |

Lower cost is better. Optimum hits count the runs (out of 150) that reach the proven optimum; no optimum was
enumerated for MA-SD, where no allocation decision exists. The full table with best, average, and standard deviation
of distance, risk exposure, and cost is Table III of the paper.

![Cost relative to A* per main scenario](docs/figures/fig3_main_cost.png)

### 7.2 Hybrid A\*–GA versus each baseline (40 test cases)

| Hybrid vs. | Better / tie / worse | Mean Δcost (%) | Max. saving (%) | *p* (Wilcoxon, Holm) |
|---|:---:|---:|---:|---:|
| A\* | 22 / 18 / 0 | −3.0 | −22.7 | 1.0 × 10⁻⁵ |
| BFS | 37 / 3 / 0 | −14.1 | −62.4 | 1.3 × 10⁻⁷ |
| GA | 37 / 3 / 0 | −4.3 | −28.6 | 1.3 × 10⁻⁷ |
| ACO | 40 / 0 / 0 | −8.4 | −26.3 | 7.3 × 10⁻¹² |

The algorithms differ significantly over the 40 cases (Friedman χ² = 134.0, *p* < 10⁻²⁷). Within each case, a hybrid
run is cheaper than a GA run with probability A₁₂ = 0.88 and than an ACO run with probability A₁₂ = 0.89.

### 7.3 Scalability (cost relative to A\* / mean time)

| Destinations | A\* time (ms) | GA vs. A\* (%) / ms | ACO vs. A\* (%) / ms | Hybrid vs. A\* (%) / ms |
|---:|---:|---:|---:|---:|
| 5 | 4.6 | +1.4 / 3,233 | +12.8 / 133 | **−4.4** / 26 |
| 10 | 8.6 | +1.0 / 6,452 | +7.5 / 284 | **−3.1** / 65 |
| 20 | 16.1 | +0.5 / 12,152 | +3.5 / 570 | **−2.4** / 141 |
| 30 | 24.5 | +0.3 / 15,175 | +3.4 / 695 | **−2.8** / 279 |

At 30 destinations, the hybrid is 54 times faster than the path-level GA.

| Routes of each algorithm | Scalability |
|---|---|
| ![Route maps](docs/figures/fig4_route_maps.png) | ![Scalability](docs/figures/fig5_scalability.png) |

### 7.4 Key findings

- **Exact paths:** A\* returns the optimal path in milliseconds; path-level GA and ACO are slower, less stable, and
  never achieve a lower cost.
- **Optimality:** the hybrid reaches the proven optimum in every run of all 15 verifiable cases, with zero standard
  deviation in all 20 main cases, and is never worse than any baseline.
- **Source of the gain:** the improvement comes entirely from the allocation level and appears only where an
  allocation or ordering decision exists (SA-MD, MA-MD, and the scalability cases).

### 7.5 Result files

| File | Content |
|---|---|
| `experiments/results/OptiRoute_Results.xlsx` | All results in one workbook (summary, per case, statistics, scalability, tuning, raw runs) |
| `experiments/results/main_runs.csv`, `scale_runs.csv` | Every individual run (including the Dijkstra runs) |
| `experiments/results/table_*.csv`, `stats_*.csv`, `summary.json` | Aggregated tables and statistical tests |
| `experiments/results/optimum.csv` | Proven optimum of the verifiable cases |
| `docs/figures/` | Figures of the paper |

## 8. Repository structure

```
aid-path-finder-optimization/
├── backend/
│   ├── server.py               FastAPI endpoints
│   ├── graph_service.py        road network, risk field, metrics, dataset loader
│   ├── algorithms.py           A*, Dijkstra, BFS, GA, ACO, greedy multi-depot solver
│   ├── hybrid.py               proposed two-level hybrid A*-GA
│   ├── experiment_runner.py    background runner for the experiments dialog
│   ├── tests/                  unit and API tests
│   └── requirements.txt        pinned Python dependencies
├── frontend/                   React + Leaflet web application
├── dataset/
│   ├── network/                frozen Mamuju network (nodes, edges, GeoJSON)
│   ├── test_cases/             40 + 4 test cases, maps, app sessions
│   ├── tuned_params.json       parameters used in the paper
│   └── metadata.json, SHA256SUMS
├── experiments/
│   ├── run_experiments.py      tuning, main, scalability, report
│   ├── verify_dataset.py       reproduction check
│   ├── export_excel.py         Excel workbook of all results
│   ├── make_*.py, build_dataset.py
│   ├── results/                published results of the paper
│   └── figures/                generated figures
├── docs/                       figures, screenshots, test-case catalogue
├── CITATION.cff
└── LICENSE
```

## 9. API reference

Base URL: `http://localhost:8001/api`

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/graph/init` | Load the network (`lat`, `lng`, `radius`, `seed`, `prefer_cache`) |
| GET | `/graph/data`, `/graph/nearest`, `/graph/summary` | Network GeoJSON, nearest node, network size |
| POST | `/graph/remove-edge`, `/graph/restore-edges`, `/graph/reset` | Road closures and reset |
| POST | `/route/optimize` | Solve with one algorithm (`"algorithm": "hybrid"` for the proposed method) |
| POST | `/route/compare`, `/route/benchmark` | All algorithms once, or *N* runs each |
| POST | `/experiments/run`, `/experiments/cancel` | Start or stop the experiment pipeline |
| GET | `/experiments/status`, `/experiments/results`, `/experiments/figure/{run}/{name}` | Progress, results, figures |
| GET | `/experiments/excel/{run}` | Download the results workbook |

## 10. How to cite

If you use this software, dataset, or results, please cite the paper:

```bibtex
@inproceedings{firgiawan2026riskaware,
  author    = {Firgiawan, Wawan and Amaliah, Bilqis and Saikhu, Ahmad and
               Basori, Ahmad Hoirul and Sulfayanti and Nur, Nahya},
  title     = {Risk-Aware Disaster Relief Routing: Comparing Exact, Metaheuristic,
               and Two-Level Hybrid {A*}--{GA} Methods},
  booktitle = {2026 10th International Conference on Information Technology,
               Information Systems and Electrical Engineering (ICITISEE)},
  address   = {Yogyakarta, Indonesia},
  publisher = {IEEE},
  year      = {2026},
  note      = {Accepted; to appear in IEEE Xplore}
}
```

IEEE style:

> W. Firgiawan, B. Amaliah, A. Saikhu, A. H. Basori, Sulfayanti, and N. Nur, "Risk-aware disaster relief routing:
> Comparing exact, metaheuristic, and two-level hybrid A\*–GA methods," in *Proc. 10th Int. Conf. Information
> Technology, Information Systems and Electrical Engineering (ICITISEE)*, Yogyakarta, Indonesia, 2026.

To cite the software itself, use the **"Cite this repository"** button on GitHub, which reads
[`CITATION.cff`](CITATION.cff). The DOI will be added once the paper is published in IEEE Xplore.

## 11. License and acknowledgment

- **Code:** [MIT License](LICENSE).
- **Dataset:** road geometry © OpenStreetMap contributors, available under the
  [Open Database License (ODbL) 1.0](https://opendatacommons.org/licenses/odbl/1-0/). The derived network, test
  cases, and parameters are released under the same license.

This work was supported by Institut Teknologi Sepuluh Nopember (ITS) and DPPM Diktisaintek.

**Contact:** Wawan Firgiawan, Department of Informatics, Institut Teknologi Sepuluh Nopember, Surabaya, Indonesia.
