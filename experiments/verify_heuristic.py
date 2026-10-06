"""Check the A* lower-bound argument against the stored (rounded) edge weights.

Edge lengths and costs are stored with two decimals, so cost >= length >= haversine holds only up to rounding.
This script reports
  1. edges whose stored cost (or length) is below the haversine distance of their end nodes,
  2. the largest difference between the stored cost and length x (1 + risk),
  3. whether A* (hybrid Level 1 and baseline implementation) returns the Dijkstra cost on every
     directed pair of key nodes (depots and destinations) of all test cases.

usage: python experiments/verify_heuristic.py
"""
import itertools
import json
import sys
from pathlib import Path

import networkx as nx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'backend'))
from algorithms import astar_search  # noqa: E402
from graph_service import GraphService, haversine  # noqa: E402
from hybrid import astar_cost  # noqa: E402


def main():
    meta = json.loads((ROOT / 'dataset' / 'metadata.json').read_text())
    net = ROOT / 'dataset' / 'network'
    gs = GraphService()
    gs.load_from_csv(net / f"{meta['network']}_nodes.csv", net / f"{meta['network']}_edges.csv", *meta['center'])
    G = gs.graph
    co = {n: (d['y'], d['x']) for n, d in G.nodes(data=True)}

    cost_def, len_def = [], []
    for u, v, d in G.edges(data=True):
        h = haversine(*co[u], *co[v])
        if d['cost'] < h:
            cost_def.append(h - d['cost'])
        if d['distance'] < h:
            len_def.append(h - d['distance'])
    rounding = max(abs(d['cost'] - d['distance'] * (1 + d['risk'])) for _, _, d in G.edges(data=True))
    print(f'edges: {G.number_of_edges()}')
    print(f'stored cost below haversine:   {len(cost_def)} edges, max deficit {max(cost_def, default=0):.4f} m')
    print(f'stored length below haversine: {len(len_def)} edges, max deficit {max(len_def, default=0):.4f} m')
    print(f'max |cost - length x (1 + risk)| from rounding: {rounding:.4f}')

    cases = json.loads((ROOT / 'dataset' / 'test_cases' / 'test_cases.json').read_text())
    pairs = set()
    for c in cases:
        keys = list(dict.fromkeys([p['node_id'] for p in c['depots']] + [p['node_id'] for p in c['destinations']]))
        pairs.update(itertools.permutations(keys, 2))
    diff_h = diff_b = 0
    for s, t in pairs:
        dj = nx.dijkstra_path_length(G, s, t, weight='cost')
        _, c_h, _ = astar_cost(G, s, t, co)
        p_b = astar_search(G, s, t, gs.nodes_data)[0]
        c_b = sum(G[a][b]['cost'] for a, b in zip(p_b, p_b[1:]))
        diff_h += abs(c_h - dj) > 1e-9
        diff_b += abs(c_b - dj) > 1e-9
    print(f'directed key-node pairs of {len(cases)} test cases: {len(pairs)}')
    print(f'pairs where A* cost != Dijkstra cost: hybrid Level 1 {diff_h}, baseline A* {diff_b}')


if __name__ == '__main__':
    main()
