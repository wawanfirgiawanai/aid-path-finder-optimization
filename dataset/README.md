# Dataset — Conference Version (vConfrence)

This folder holds the single road network and the 44 documented test cases (40 evaluation + 4 tuning) used in the
conference paper *"Comparative Evaluation of Risk-Aware Routing Algorithms and a Two-Level Hybrid A\*–GA for
Disaster Relief Distribution"* (ICITISEE 2026).

> **Disclaimer.** This is a simulation dataset. Only the road geometry comes from OpenStreetMap. Depots,
> destinations, agents and risk values are simulated, and no data from any actual disaster event or field
> operation is included.

## 1. One road network

| Item | Value |
|---|---|
| Area | Mamuju, West Sulawesi, Indonesia |
| Centre / radius | −2.692, 118.898 / 1,500 m |
| Source | OpenStreetMap drive network via OSMnx (simplified, largest connected component, undirected) |
| Size | 455 nodes (intersections), 516 edges (road segments), 42.3 km of road |
| Edge attributes | `distance_m` (OSM length), `risk` r ~ U(0, 1) with seed 42, `cost` = distance_m × (1 + risk) |
| Risk classes | low r ≤ 0.33, medium 0.33 < r ≤ 0.66, high r > 0.66 |
| Files | `network/mamuju_r1500_nodes.csv`, `network/mamuju_r1500_edges.csv`, `network/mamuju_r1500_edges.geojson` |

## 2. Test cases: same network, different start and destination points

Every test case uses the network above. It differs only in **which nodes are the depots (start points), how many
agents each depot has, and which nodes are the destinations**. Points are network nodes drawn with a fixed seed
and kept at least 150 m apart.

| Group | Test cases | Depots × agents | Destinations | Force distribution | Point seeds | Runs per algorithm | Purpose |
|---|---|---|---|---|---|---|---|
| SA-SD | SA-SD-01 … 05 | 1 × 1 | 1 | no | 2026–2030 | 30 | main |
| SA-MD | SA-MD-01 … 05 | 1 × 1 | 4 | no | 2026–2030 | 30 | main |
| MA-SD | MA-SD-01 … 05 | 2 × 2 | 1 | yes | 2026–2030 | 30 | main |
| MA-MD | MA-MD-01 … 05 | 2 × 2 | 4 | yes | 2026–2030 | 30 | main |
| SC-05 | SC-05-01 … 05 | 2 × 2 | 5 | yes | 3500–3504 | 10 | scalability |
| SC-10 | SC-10-01 … 05 | 2 × 2 | 10 | yes | 4000–4004 | 10 | scalability |
| SC-20 | SC-20-01 … 05 | 2 × 2 | 20 | yes | 5000–5004 | 10 | scalability |
| SC-30 | SC-30-01 … 05 | 2 × 2 | 30 | yes | 6000–6004 | 10 | scalability |
| TUNE | TUNE-A, B, C, D | 1×1, 2×2, 2×2, 2×2 | 4, 4, 20, 30 | no, yes, yes, yes | 9001–9004 | 5 per configuration | tuning only |

Test case `-01` of each main group is the instance of the first version of the paper. Cases with the same point
seed share their first points (for example SA-SD-01 and SA-MD-01 have the same depot). *Force distribution* means
every agent must be dispatched; with more agents than destinations (MA-SD), every agent drives to its nearest
destination.

Evaluation: 20 main cases × 6 algorithms × 30 runs = 3,600 runs; 20 scalability cases × 6 algorithms × 10 runs =
1,200 runs. Algorithms: Dijkstra, A\*, BFS, GA, ACO and the proposed hybrid A\*–GA (Dijkstra returns the same paths
and costs as A\* and is therefore omitted from the paper).

## 3. Files of the test cases (`test_cases/`)

| File | Content |
|---|---|
| `test_cases.json` | Every case: id, group, purpose, seed, depots (label, node id, agents, lat, lng), destinations |
| `test_cases_points.csv` | One row per point: case_id, group, role (depot/destination), label, node_id, lat, lng, agents |
| `test_cases_summary.csv` | One row per case: sizes, force distribution, seed, spacing |
| `test_cases.geojson` | All points for QGIS / Leaflet (property `case_id`) |
| `maps/<CASE_ID>.png` | Map of the points of every case on the risk-coloured network |
| `app_sessions/<CASE_ID>.json` | Ready-to-import session for the web app (Initialize, then Import) |

A full catalogue with the coordinates and map of every case is in
[`docs/Dataset_dan_Test_Case.docx`](../docs/Dataset_dan_Test_Case.docx).

## 4. Other files

| File | Content |
|---|---|
| `tuned_params.json` | GA, ACO and hybrid A\*–GA parameters selected by tuning and used for every evaluation run |
| `metadata.json` | Network size, groups, seeds, note |
| `SHA256SUMS` | Checksums of all files (`sha256sum -c SHA256SUMS`) |

## 5. Rebuild and reproduce

```bash
backend/.venv/Scripts/python experiments/build_dataset.py          # rebuild test cases, maps, sessions
backend/.venv/Scripts/python experiments/run_experiments.py --phase all --params-file dataset/tuned_params.json --out experiments/runs/cli
backend/.venv/Scripts/python experiments/verify_dataset.py         # compare with the published runs
```

## 6. License

Road geometry © OpenStreetMap contributors, [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/). The derived
network, test cases and parameters are released under the same license.
