"""Offline tests for the two-level hybrid A*-GA solver (synthetic graph, no network needed)."""
import random
import sys
from pathlib import Path

import networkx as nx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from graph_service import GraphService  # noqa: E402
from algorithms import solve_vrp  # noqa: E402
from hybrid import (AllocationProblem, exact_allocation, multi_domain_inversion,  # noqa: E402
                    order_crossover, solve_hybrid)


@pytest.fixture(scope="module")
def gs():
    g = GraphService()
    g.rng = random.Random(7)
    g._generate_synthetic_graph(-2.692, 118.898, 1500)
    return g


def _instance(gs, n_depots, apd, n_dest, seed):
    nodes = random.Random(seed).sample(sorted(gs.graph.nodes()), n_depots + n_dest)
    return ([{"node_id": str(n), "agents": apd} for n in nodes[:n_depots]],
            [{"node_id": str(n)} for n in nodes[n_depots:]])


def test_level1_is_exact(gs):
    starts, dests = _instance(gs, 1, 1, 1, 3)
    r = solve_hybrid(gs, starts, dests, None, False, seed=1)
    exact = nx.shortest_path_length(gs.graph, int(starts[0]['node_id']), int(dests[0]['node_id']), weight='cost')
    assert r['summary']['total_cost'] == pytest.approx(exact, abs=0.05)


def test_never_worse_than_greedy_dijkstra_and_hits_optimum(gs):
    for seed in range(5):
        starts, dests = _instance(gs, 2, 2, 5, seed)
        random.seed(seed)
        dij = solve_vrp(gs, starts, dests, 'dijkstra', None, True)['summary']['total_cost']
        res, prob = solve_hybrid(gs, starts, dests, None, True, seed=seed, return_problem=True)
        _, opt = exact_allocation(prob, max_tokens=9)
        assert res['summary']['total_cost'] <= dij + 0.05
        assert res['summary']['total_cost'] == pytest.approx(opt, abs=0.1)
        assert res['summary']['destinations_covered'] == 5
        assert res['summary']['agents_used'] == 4  # forced distribution


def test_operators_keep_permutation():
    rng = random.Random(0)
    M = [[abs(i - j) for j in range(8)] for i in range(8)]
    prob = AllocationProblem(M, [0, 1], [2, 3, 4, 5, 6, 7])
    base = prob.tokens()
    for _ in range(200):
        a, b = base[:], base[:]
        rng.shuffle(a)
        rng.shuffle(b)
        assert sorted(order_crossover(a, b, rng)) == base
        assert sorted(multi_domain_inversion(a, prob, rng)) == base


def test_dispatch_through_solve_vrp(gs):
    starts, dests = _instance(gs, 1, 2, 3, 4)
    random.seed(0)
    r = solve_vrp(gs, starts, dests, 'hybrid', None, True)
    assert r['algorithm'] == 'hybrid'
    assert r['summary']['destinations_covered'] == 3
