import heapq
import math
import random
import time
import statistics
import networkx as nx
from collections import deque
from dataclasses import dataclass
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

DEFAULT_ALGO_PARAMS = {
    "ga_population": 50, "ga_generations": 100, "ga_crossover_rate": 0.8,
    "ga_mutation_rate": 0.05, "ga_tournament_k": 3, "ga_elitism": 2,
    "ga_stagnation_limit": 10,
    "aco_ants": 20, "aco_iterations": 50, "aco_alpha": 1.0, "aco_beta": 2.0,
    "aco_evaporation": 0.5, "aco_stagnation_limit": 10,
    # Hybrid A*-GA (proposed): level-1 A* cost matrix + level-2 allocation GA
    "hga_population": 60, "hga_generations": 200, "hga_crossover_rate": 0.9,
    "hga_mutation_rate": 0.3, "hga_tournament_k": 3, "hga_elitism": 2,
    "hga_stagnation_limit": 50, "hga_makespan_weight": 0.0
}


def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ========== DIJKSTRA ==========
def dijkstra_search(graph, source, target):
    dists = {source: 0}
    prev = {source: None}
    pq = [(0, source)]
    visited = set()
    explored = 0
    while pq:
        cd, cur = heapq.heappop(pq)
        if cur in visited:
            continue
        visited.add(cur)
        explored += 1
        if cur == target:
            break
        for nb in graph.neighbors(cur):
            if nb in visited:
                continue
            nd = cd + graph[cur][nb].get('cost', 1)
            if nd < dists.get(nb, float('inf')):
                dists[nb] = nd
                prev[nb] = cur
                heapq.heappush(pq, (nd, nb))
    if target not in prev:
        return None, 0, explored
    path = []
    c = target
    while c is not None:
        path.append(c)
        c = prev.get(c)
    path.reverse()
    return path, dists.get(target, 0), explored


# ========== A* ==========
def astar_search(graph, source, target, nodes_data):
    td = nodes_data.get(str(target), {})
    tlat, tlng = td.get('lat', 0), td.get('lng', 0)

    def h(n):
        nd = nodes_data.get(str(n), {})
        return haversine(nd.get('lat', 0), nd.get('lng', 0), tlat, tlng) if nd else 0

    g = {source: 0}
    prev = {source: None}
    pq = [(h(source), id(source), source)]
    visited = set()
    explored = 0
    while pq:
        _, _, cur = heapq.heappop(pq)
        if cur in visited:
            continue
        visited.add(cur)
        explored += 1
        if cur == target:
            break
        for nb in graph.neighbors(cur):
            if nb in visited:
                continue
            tg = g[cur] + graph[cur][nb].get('cost', 1)
            if tg < g.get(nb, float('inf')):
                g[nb] = tg
                prev[nb] = cur
                heapq.heappush(pq, (tg + h(nb), id(nb), nb))
    if target not in prev:
        return None, 0, explored
    path = []
    c = target
    while c is not None:
        path.append(c)
        c = prev.get(c)
    path.reverse()
    return path, g.get(target, 0), explored


# ========== BFS ==========
def bfs_search(graph, source, target):
    queue = deque([(source, [source])])
    visited = {source}
    explored = 0
    while queue:
        cur, path = queue.popleft()
        explored += 1
        if cur == target:
            return path, explored
        for nb in graph.neighbors(cur):
            if nb not in visited:
                visited.add(nb)
                queue.append((nb, path + [nb]))
    return None, explored


# ========== HELPERS ==========
def _path_cost(graph, path):
    total = 0
    for i in range(len(path) - 1):
        if graph.has_edge(path[i], path[i + 1]):
            total += graph[path[i]][path[i + 1]].get('cost', 1)
        else:
            return float('inf')
    return total


def _k_shortest_paths(graph, source, target, k=20):
    """Use Yen's K-shortest simple paths for genuinely different routes."""
    paths = []
    try:
        for path in nx.shortest_simple_paths(graph, source, target, weight='cost'):
            paths.append(list(path))
            if len(paths) >= k:
                break
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        pass
    return paths


def _random_walk_path(graph, source, target, max_steps=800):
    """Biased random walk towards target - produces genuinely different paths."""
    path = [source]
    visited = {source}
    cur = source
    tx = graph.nodes[target]['x']
    ty = graph.nodes[target]['y']

    for _ in range(max_steps):
        nbs = [n for n in graph.neighbors(cur) if n not in visited]
        if not nbs:
            # Backtrack
            if len(path) > 1:
                path.pop()
                cur = path[-1]
                continue
            break

        weights = []
        for n in nbs:
            nd = graph.nodes[n]
            dist_to_target = math.sqrt((nd['x'] - tx) ** 2 + (nd['y'] - ty) ** 2)
            # Bias towards target with significant randomness
            w = (1.0 / max(dist_to_target, 1e-8)) * random.uniform(0.01, 5.0)
            weights.append(w)

        total = sum(weights)
        weights = [w / total for w in weights]
        nxt = random.choices(nbs, weights=weights, k=1)[0]
        path.append(nxt)
        visited.add(nxt)

        if nxt == target:
            return path
        cur = nxt
    return None


def _generate_random_population(graph, source, target, pop_size):
    """Generate population using random walks; returns (paths, used_kshortest_fallback)."""
    paths = []
    used_fallback = False
    attempts = 0
    max_attempts = pop_size * 5
    while len(paths) < pop_size and attempts < max_attempts:
        rp = _random_walk_path(graph, source, target)
        if rp is not None:
            paths.append(rp)
        attempts += 1
    # Fallback: if random walks fail, use k-shortest as last resort
    if len(paths) < 2:
        used_fallback = True
        for kp in _k_shortest_paths(graph, source, target, k=pop_size):
            if kp not in paths:
                paths.append(kp)
            if len(paths) >= pop_size:
                break
    if not paths:
        return [], used_fallback
    while len(paths) < pop_size:
        paths.append(list(random.choice(paths)))
    return paths[:pop_size], used_fallback


def _tournament_select(population, fitness, k):
    """Tournament selection: pick k random, return the fittest."""
    indices = random.sample(range(len(population)), min(k, len(population)))
    winner = max(indices, key=lambda i: fitness[i])
    return list(population[winner])


# ========== GA STANDARD ==========
def genetic_algorithm(graph, source, target, params=None):
    p = {**DEFAULT_ALGO_PARAMS, **(params or {})}
    pop_size = p.get('ga_population', 50)
    max_gen = p.get('ga_generations', 100)
    crossover_rate = p.get('ga_crossover_rate', 0.8)
    mutation_rate = p.get('ga_mutation_rate', 0.05)
    tournament_k = p.get('ga_tournament_k', 3)
    elitism_count = p.get('ga_elitism', 2)

    population, fb = _generate_random_population(graph, source, target, pop_size)
    if not population:
        return None, 0, {"generations": 0, "fallback": fb}

    explored = 0

    for gen in range(max_gen):
        # Evaluate fitness = 1 / cost
        costs = [_path_cost(graph, pp) for pp in population]
        fitness = [1.0 / max(c, 0.01) for c in costs]

        # Sort by fitness descending (best first)
        ranked = sorted(range(len(population)), key=lambda i: fitness[i], reverse=True)

        new_pop = []

        # Elitism: copy top individuals unchanged
        for i in range(min(elitism_count, len(population))):
            new_pop.append(list(population[ranked[i]]))

        # Fill remaining via selection + crossover + mutation
        while len(new_pop) < pop_size:
            parent1 = _tournament_select(population, fitness, tournament_k)

            if random.random() < crossover_rate:
                parent2 = _tournament_select(population, fitness, tournament_k)
                child = _crossover_ga(parent1, parent2, graph, source, target)
            else:
                child = list(parent1)

            if random.random() < mutation_rate:
                child = _mutate_ga(child, graph, source, target)

            new_pop.append(child)

        population = new_pop[:pop_size]
        explored += pop_size

    best = min(population, key=lambda pp: _path_cost(graph, pp))
    best_cost = _path_cost(graph, best)
    return best, explored, {"generations": max_gen, "best_cost": round(best_cost, 2), "fallback": fb}


# ========== GA WITH EARLY STOPPING ==========
def genetic_algorithm_es(graph, source, target, params=None):
    p = {**DEFAULT_ALGO_PARAMS, **(params or {})}
    pop_size = p.get('ga_population', 50)
    max_gen = p.get('ga_generations', 100)
    crossover_rate = p.get('ga_crossover_rate', 0.8)
    mutation_rate = p.get('ga_mutation_rate', 0.05)
    tournament_k = p.get('ga_tournament_k', 3)
    elitism_count = p.get('ga_elitism', 2)
    stag_limit = p.get('ga_stagnation_limit', 10)

    population, fb = _generate_random_population(graph, source, target, pop_size)
    if not population:
        return None, 0, {"generations": 0, "stopped_early": False, "fallback": fb}

    explored = 0
    best_cost = float('inf')
    stagnation = 0
    gen_done = 0

    for gen in range(max_gen):
        gen_done = gen + 1

        costs = [_path_cost(graph, pp) for pp in population]
        fitness = [1.0 / max(c, 0.01) for c in costs]
        ranked = sorted(range(len(population)), key=lambda i: fitness[i], reverse=True)

        new_pop = []
        for i in range(min(elitism_count, len(population))):
            new_pop.append(list(population[ranked[i]]))

        while len(new_pop) < pop_size:
            parent1 = _tournament_select(population, fitness, tournament_k)
            if random.random() < crossover_rate:
                parent2 = _tournament_select(population, fitness, tournament_k)
                child = _crossover_ga(parent1, parent2, graph, source, target)
            else:
                child = list(parent1)
            if random.random() < mutation_rate:
                child = _mutate_ga(child, graph, source, target)
            new_pop.append(child)

        population = new_pop[:pop_size]
        explored += pop_size

        cur_best = min(costs)
        if cur_best < best_cost - 0.01:
            best_cost = cur_best
            stagnation = 0
        else:
            stagnation += 1

        if stagnation >= stag_limit:
            break

    best = min(population, key=lambda pp: _path_cost(graph, pp))
    return best, explored, {
        "generations": gen_done, "stopped_early": stagnation >= stag_limit,
        "stagnation_limit": stag_limit, "best_cost": round(_path_cost(graph, best), 2), "fallback": fb
    }


def _crossover_ga(p1, p2, graph, source, target):
    """Crossover two paths at a common intermediate node."""
    common = [n for n in set(p1) & set(p2) if n != source and n != target]
    if not common:
        return p1 if _path_cost(graph, p1) <= _path_cost(graph, p2) else p2

    cp = random.choice(common)
    idx1 = p1.index(cp)
    idx2 = p2.index(cp)
    child = p1[:idx1] + p2[idx2:]

    # Validate
    for i in range(len(child) - 1):
        if not graph.has_edge(child[i], child[i + 1]):
            return p1 if _path_cost(graph, p1) <= _path_cost(graph, p2) else p2
    if len(set(child)) != len(child):
        return p1 if _path_cost(graph, p1) <= _path_cost(graph, p2) else p2
    return child


def _mutate_ga(path, graph, source, target):
    """Mutate by replacing a random sub-segment with a random walk."""
    if len(path) <= 3:
        return path
    idx = random.randint(1, len(path) - 2)
    sub_s = path[idx - 1]
    sub_e = path[min(idx + 1, len(path) - 1)]

    # Try random walk for sub-segment
    rp = _random_walk_path(graph, sub_s, sub_e, max_steps=100)
    if rp and len(rp) >= 2:
        new_p = path[:idx - 1] + rp + path[min(idx + 1, len(path) - 1) + 1:]
        # Validate
        valid = len(set(new_p)) == len(new_p)
        for i in range(len(new_p) - 1):
            if not valid or not graph.has_edge(new_p[i], new_p[i + 1]):
                valid = False
                break
        if valid:
            return new_p
    return path


# ========== ACO STANDARD ==========
def aco_search(graph, source, target, params=None):
    p = {**DEFAULT_ALGO_PARAMS, **(params or {})}
    n_ants = p['aco_ants']
    n_iter = p['aco_iterations']
    alpha = p['aco_alpha']
    beta = p['aco_beta']
    evap = p['aco_evaporation']
    Q = 100.0
    explore_rate = 0.15  # 15% random exploration

    pheromones = {}
    for u, v in graph.edges():
        pheromones[(u, v)] = 1.0
        pheromones[(v, u)] = 1.0

    best_path, best_cost = None, float('inf')
    explored = 0

    for it in range(n_iter):
        paths, costs = [], []
        config = AntConfig(pheromones=pheromones, alpha=alpha, beta=beta, explore_rate=explore_rate)
        for _ in range(n_ants):
            path = _ant_walk_v2(graph, source, target, config)
            if path:
                cost = _path_cost(graph, path)
                paths.append(path)
                costs.append(cost)
                explored += len(path)
                if cost < best_cost:
                    best_cost = cost
                    best_path = list(path)

        # Evaporate
        for k in pheromones:
            pheromones[k] = max(pheromones[k] * (1 - evap), 0.1)

        # Deposit - only top 3 ants deposit pheromone (elitist)
        if paths:
            sorted_idx = sorted(range(len(costs)), key=lambda i: costs[i])
            top_n = min(3, len(sorted_idx))
            for idx in sorted_idx[:top_n]:
                dep = Q / max(costs[idx], 0.01)
                for i in range(len(paths[idx]) - 1):
                    pheromones[(paths[idx][i], paths[idx][i + 1])] = pheromones.get((paths[idx][i], paths[idx][i + 1]), 0.1) + dep
                    pheromones[(paths[idx][i + 1], paths[idx][i])] = pheromones.get((paths[idx][i + 1], paths[idx][i]), 0.1) + dep

        # Cap max pheromone (MAX-MIN system)
        max_pheromone = Q / max(best_cost, 0.01) * 5
        for k in pheromones:
            pheromones[k] = min(pheromones[k], max_pheromone)

    fallback = best_path is None
    if fallback:
        try:
            best_path = list(nx.shortest_path(graph, source, target, weight='cost'))
        except Exception:
            pass
    return best_path, explored, {"iterations": n_iter, "fallback": fallback}


# ========== ACO WITH EARLY STOPPING ==========
def aco_search_es(graph, source, target, params=None):
    p = {**DEFAULT_ALGO_PARAMS, **(params or {})}
    n_ants = p['aco_ants']
    n_iter = p['aco_iterations']
    alpha = p['aco_alpha']
    beta = p['aco_beta']
    evap = p['aco_evaporation']
    stag_limit = p['aco_stagnation_limit']
    Q = 100.0
    explore_rate = 0.15

    pheromones = {}
    for u, v in graph.edges():
        pheromones[(u, v)] = 1.0
        pheromones[(v, u)] = 1.0

    best_path, best_cost = None, float('inf')
    explored = 0
    stagnation = 0
    iter_done = 0

    for it in range(n_iter):
        iter_done = it + 1
        improved = False
        paths, costs = [], []
        config = AntConfig(pheromones=pheromones, alpha=alpha, beta=beta, explore_rate=explore_rate)
        for _ in range(n_ants):
            path = _ant_walk_v2(graph, source, target, config)
            if path:
                cost = _path_cost(graph, path)
                paths.append(path)
                costs.append(cost)
                explored += len(path)
                if cost < best_cost - 0.001:
                    best_cost = cost
                    best_path = list(path)
                    improved = True

        if not improved:
            stagnation += 1
        else:
            stagnation = 0

        for k in pheromones:
            pheromones[k] = max(pheromones[k] * (1 - evap), 0.1)
        if paths:
            sorted_idx = sorted(range(len(costs)), key=lambda i: costs[i])
            top_n = min(3, len(sorted_idx))
            for idx in sorted_idx[:top_n]:
                dep = Q / max(costs[idx], 0.01)
                for i in range(len(paths[idx]) - 1):
                    pheromones[(paths[idx][i], paths[idx][i + 1])] = pheromones.get((paths[idx][i], paths[idx][i + 1]), 0.1) + dep
                    pheromones[(paths[idx][i + 1], paths[idx][i])] = pheromones.get((paths[idx][i + 1], paths[idx][i]), 0.1) + dep

        max_pheromone = Q / max(best_cost, 0.01) * 5
        for k in pheromones:
            pheromones[k] = min(pheromones[k], max_pheromone)

        if stagnation >= stag_limit:
            break

    fallback = best_path is None
    if fallback:
        try:
            best_path = list(nx.shortest_path(graph, source, target, weight='cost'))
        except Exception:
            pass
    return best_path, explored, {"iterations": iter_done, "stopped_early": stagnation >= stag_limit,
                                 "stagnation_limit": stag_limit, "fallback": fallback}


@dataclass
class AntConfig:
    pheromones: dict
    alpha: float
    beta: float
    explore_rate: float = 0.15
    max_steps: int = 500


def _ant_walk_v2(graph, source, target, config: AntConfig):
    """Ant walk with epsilon-greedy exploration."""
    path = [source]
    visited = {source}
    cur = source

    for _ in range(config.max_steps):
        nbs = [n for n in graph.neighbors(cur) if n not in visited]
        if not nbs:
            break

        if random.random() < config.explore_rate:
            nxt = random.choice(nbs)
        else:
            probs = []
            for n in nbs:
                tau = config.pheromones.get((cur, n), 0.1)
                eta = 1.0 / max(graph[cur][n].get('cost', 1.0), 0.01)
                probs.append((tau ** config.alpha) * (eta ** config.beta))
            total = sum(probs)
            if total == 0:
                nxt = random.choice(nbs)
            else:
                probs = [p / total for p in probs]
                nxt = random.choices(nbs, weights=probs, k=1)[0]

        path.append(nxt)
        visited.add(nxt)
        if nxt == target:
            return path
        cur = nxt
    return None


# ========== SINGLE ROUTE RUNNER ==========
def run_single_route(graph_service, source_id, target_id, algorithm, algo_params=None):
    graph = graph_service.graph
    source, target = int(source_id), int(target_id)
    t0 = time.perf_counter()
    path, explored, meta = None, 0, {}

    if algorithm == 'dijkstra':
        path, _, explored = dijkstra_search(graph, source, target)
    elif algorithm == 'astar':
        path, _, explored = astar_search(graph, source, target, graph_service.nodes_data)
    elif algorithm == 'bfs':
        r = bfs_search(graph, source, target)
        path, explored = r[0], r[1]
    elif algorithm == 'ga':
        path, explored, meta = genetic_algorithm(graph, source, target, algo_params)
    elif algorithm == 'ga_es':
        path, explored, meta = genetic_algorithm_es(graph, source, target, algo_params)
    elif algorithm == 'aco':
        path, explored, meta = aco_search(graph, source, target, algo_params)
    elif algorithm == 'aco_es':
        path, explored, meta = aco_search_es(graph, source, target, algo_params)

    comp_time = round((time.perf_counter() - t0) * 1000, 2)
    if path is None:
        return {"algorithm": algorithm, "path_nodes": [], "path_coordinates": [], "route_geometry": [],
                "edges": [], "total_distance": 0, "total_cost": 0, "avg_risk": 0,
                "computation_time_ms": comp_time, "nodes_explored": explored, "meta": meta, "error": "No path found"}
    td, tc, ar = graph_service.get_path_metrics(path)
    return {"algorithm": algorithm, "path_nodes": [str(n) for n in path],
            "path_coordinates": graph_service.get_path_coordinates(path),
            "route_geometry": graph_service.get_route_geometry(path),
            "edges": graph_service.get_path_edges(path),
            "total_distance": td, "total_cost": tc, "avg_risk": ar,
            "computation_time_ms": comp_time, "nodes_explored": explored, "meta": meta}


# ========== VRP SOLVER ==========
def solve_vrp(graph_service, starts, destinations, algorithm, algo_params=None, force_distribution=False):
    if algorithm == 'hybrid':
        from hybrid import solve_hybrid
        return solve_hybrid(graph_service, starts, destinations, algo_params, force_distribution)
    graph = graph_service.graph
    t0 = time.perf_counter()

    # Build agent list
    agents = []
    for si, s in enumerate(starts):
        sid = int(s['node_id'])
        for ai in range(s.get('agents', 1)):
            agents.append({"start": sid, "start_label": f"S{si + 1}",
                           "agent_label": f"S{si + 1}-A{ai + 1}", "current": sid, "assigned": [], "cost": 0})

    dest_ids = [int(d['node_id']) for d in destinations]
    dest_labels = {int(destinations[i]['node_id']): f"E{i + 1}" for i in range(len(destinations))}

    # Pre-compute shortest path costs (one single-source Dijkstra per key node, used by the greedy allocation)
    all_src_nodes = list(set([a['start'] for a in agents]))
    dist_cache = {}
    for src in all_src_nodes + dest_ids:
        try:
            lengths = nx.single_source_dijkstra_path_length(graph, src, weight='cost')
            for tgt in all_src_nodes + dest_ids:
                if tgt in lengths:
                    dist_cache[(src, tgt)] = lengths[tgt]
        except Exception:
            pass

    t_matrix = time.perf_counter()
    if force_distribution and len(agents) > 1:
        _assign_forced(agents, dest_ids, dist_cache)
    else:
        _assign_greedy(agents, dest_ids, dist_cache)
    t_alloc = time.perf_counter()
    # fallback types: GA k-shortest seeding, ACO exact path, solver exact path for a missing baseline path
    fallbacks = {"ga_kshortest": 0, "aco_shortest_path": 0, "solver_shortest_path": 0}

    # Build routes for each agent using the selected algorithm
    routes = []
    for ag in agents:
        if not ag['assigned']:
            continue
        waypoints = [ag['start']] + ag['assigned']
        full_path = []
        full_geometry = []
        segments = []
        for j in range(len(waypoints) - 1):
            src, tgt = waypoints[j], waypoints[j + 1]
            seg_result = run_single_route(graph_service, str(src), str(tgt), algorithm, algo_params)
            seg_path = [int(n) for n in seg_result.get('path_nodes', [])] if seg_result.get('path_nodes') else []
            seg_geom = seg_result.get('route_geometry', [])
            if seg_result.get('meta', {}).get('fallback'):
                fallbacks['ga_kshortest' if algorithm.startswith('ga') else 'aco_shortest_path'] += 1
            if not seg_path:
                fallbacks['solver_shortest_path'] += 1
                try:
                    seg_path = list(nx.shortest_path(graph, src, tgt, weight='cost'))
                    seg_geom = graph_service.get_route_geometry(seg_path)
                except nx.NetworkXNoPath:
                    seg_path = [src, tgt]
                    seg_geom = graph_service.get_route_geometry(seg_path)
            sd, sc, sr = graph_service.get_path_metrics(seg_path)
            fl = ag['start_label'] if j == 0 else dest_labels.get(waypoints[j], f"P{j}")
            tl = dest_labels.get(tgt, f"P{j + 1}")
            segments.append({"from_label": fl, "to_label": tl, "route_label": f"{fl} -> {tl}",
                             "distance": sd, "cost": sc, "avg_risk": sr})
            if full_path:
                full_path.extend(seg_path[1:])
                full_geometry.extend(seg_geom[1:] if seg_geom else [])
            else:
                full_path = list(seg_path)
                full_geometry = list(seg_geom)

        dv = [dest_labels.get(d, "?") for d in ag['assigned']]
        routes.append(build_route_entry(graph_service, ag['agent_label'], ag['start_label'], dv,
                                        full_path, full_geometry, segments))

    t_end = time.perf_counter()
    comp_time = round((t_end - t0) * 1000, 2)
    used = {k: v for k, v in fallbacks.items() if v}
    meta = {"matrix_ms": round((t_matrix - t0) * 1000, 2), "allocation_ms": round((t_alloc - t_matrix) * 1000, 2),
            "routing_ms": round((t_end - t_alloc) * 1000, 2), "fallback_counts": fallbacks,
            "fallback_used": bool(used), "fallback_type": '+'.join(sorted(used)) or None,
            "fallback_count": sum(fallbacks.values())}
    return {"routes": routes, "algorithm": algorithm,
            "summary": build_summary(routes, comp_time, len(destinations)), "meta": meta}


def build_route_entry(graph_service, agent_label, start_label, dests_visited, full_path, full_geometry, segments):
    td, tc, ar = graph_service.get_path_metrics(full_path)
    prof = graph_service.get_path_risk_profile(full_path)
    dv_str = " -> ".join(dests_visited)
    return {"agent_id": agent_label, "start_label": start_label,
            "destinations_visited": dests_visited, "path_nodes": [str(n) for n in full_path],
            "route_geometry": full_geometry, "segments": segments,
            "total_distance": td, "total_cost": tc, "avg_risk": ar,
            "risk_exposure": round(prof["risk_weighted_sum"] / prof["distance"], 4) if prof["distance"] else 0.0,
            "max_risk": prof["max_risk"], "high_risk_distance": round(prof["high_risk_distance"], 2),
            "_risk_weighted_sum": prof["risk_weighted_sum"],
            "route_label": f"{agent_label}: {start_label} -> {dv_str}"}


def build_summary(routes, comp_time, total_destinations):
    """Aggregate per-route metrics. risk_exposure is length-weighted over all routes."""
    atd = sum(r['total_distance'] for r in routes)
    atc = sum(r['total_cost'] for r in routes)
    aar = sum(r['avg_risk'] for r in routes) / max(len(routes), 1) if routes else 0
    wsum = sum(r.pop('_risk_weighted_sum', 0.0) for r in routes)
    visits = [d for r in routes for d in r['destinations_visited']]
    return {"total_distance": round(atd, 2), "total_cost": round(atc, 2),
            "avg_risk": round(aar, 3),
            "risk_exposure": round(wsum / atd, 4) if atd else 0.0,
            "max_risk": max((r['max_risk'] for r in routes), default=0.0),
            "high_risk_distance": round(sum(r['high_risk_distance'] for r in routes), 2),
            "makespan_cost": round(max((r['total_cost'] for r in routes), default=0.0), 2),
            "computation_time_ms": comp_time,
            "agents_used": len(routes),
            "destinations_covered": len(set(visits)),  # unique destinations served
            "service_visits": len(visits),  # visits by all vehicles (MA-SD: every vehicle visits the one destination)
            "total_destinations": total_destinations}


def _assign_greedy(agents, dest_ids, dist_cache):
    """Greedy nearest-neighbor: assign each dest to closest agent."""
    unassigned = list(dest_ids)
    while unassigned:
        best_ai, best_d, best_c = None, None, float('inf')
        for d in unassigned:
            for i, ag in enumerate(agents):
                c = dist_cache.get((ag['current'], d), float('inf'))
                if c < best_c:
                    best_c = c
                    best_ai = i
                    best_d = d
        if best_ai is None:
            break
        agents[best_ai]['assigned'].append(best_d)
        agents[best_ai]['current'] = best_d
        agents[best_ai]['cost'] += best_c
        unassigned.remove(best_d)


def _assign_forced(agents, dest_ids, dist_cache):
    """Force distribution: every agent MUST get at least 1 destination.
    If agents > destinations, multiple agents share the same destinations."""
    if not dest_ids:
        return

    # Case: more agents than destinations → each agent gets nearest destination (shared)
    if len(agents) > len(dest_ids):
        for ag in agents:
            best_d, best_c = None, float('inf')
            for d in dest_ids:
                c = dist_cache.get((ag['start'], d), float('inf'))
                if c < best_c:
                    best_c = c
                    best_d = d
            if best_d is not None:
                ag['assigned'].append(best_d)
                ag['current'] = best_d
                ag['cost'] += best_c
        return

    # Case: destinations >= agents → round-robin nearest, then greedy remainder
    unassigned = list(dest_ids)

    # Phase 1: Each agent gets their nearest unassigned destination
    for ag in agents:
        if not unassigned:
            break
        best_d, best_c = None, float('inf')
        for d in unassigned:
            c = dist_cache.get((ag['start'], d), float('inf'))
            if c < best_c:
                best_c = c
                best_d = d
        if best_d is not None:
            ag['assigned'].append(best_d)
            ag['current'] = best_d
            ag['cost'] += best_c
            unassigned.remove(best_d)

    # Phase 2: Remaining destinations go to nearest agent (greedy)
    while unassigned:
        best_ai, best_d, best_c = None, None, float('inf')
        for d in unassigned:
            for i, ag in enumerate(agents):
                c = dist_cache.get((ag['current'], d), float('inf'))
                if c < best_c:
                    best_c = c
                    best_ai = i
                    best_d = d
        if best_ai is None:
            break
        agents[best_ai]['assigned'].append(best_d)
        agents[best_ai]['current'] = best_d
        agents[best_ai]['cost'] += best_c
        unassigned.remove(best_d)


def run_comparison_vrp(graph_service, starts, destinations, algorithms, algo_params=None, force_distribution=False):
    results = []
    for algo in algorithms:
        r = solve_vrp(graph_service, starts, destinations, algo, algo_params, force_distribution)
        results.append(r)
    return results


def run_benchmark(graph_service, starts, destinations, algorithms, runs_per_algo, algo_params=None, force_distribution=False):
    benchmark = []
    for algo in algorithms:
        algo_runs = []
        for run_idx in range(runs_per_algo):
            r = solve_vrp(graph_service, starts, destinations, algo, algo_params, force_distribution)
            algo_runs.append({
                "run": run_idx + 1,
                "total_distance": r["summary"]["total_distance"],
                "total_cost": r["summary"]["total_cost"],
                "avg_risk": r["summary"]["avg_risk"],
                "risk_exposure": r["summary"]["risk_exposure"],
                "makespan_cost": r["summary"]["makespan_cost"],
                "computation_time_ms": r["summary"]["computation_time_ms"],
                "agents_used": r["summary"]["agents_used"],
                "destinations_covered": r["summary"]["destinations_covered"],
            })
        costs = [x["total_cost"] for x in algo_runs]
        times = [x["computation_time_ms"] for x in algo_runs]
        dists = [x["total_distance"] for x in algo_runs]
        risks = [x["avg_risk"] for x in algo_runs]

        def safe_stdev(vals):
            return round(statistics.stdev(vals), 4) if len(vals) > 1 else 0.0

        benchmark.append({
            "algorithm": algo, "runs": algo_runs, "total_runs": runs_per_algo,
            "stats": {
                "cost_min": round(min(costs), 2), "cost_max": round(max(costs), 2),
                "cost_avg": round(sum(costs) / len(costs), 2), "cost_stdev": safe_stdev(costs),
                "time_min": round(min(times), 2), "time_max": round(max(times), 2),
                "time_avg": round(sum(times) / len(times), 2), "time_stdev": safe_stdev(times),
                "dist_min": round(min(dists), 2), "dist_max": round(max(dists), 2),
                "dist_avg": round(sum(dists) / len(dists), 2), "dist_stdev": safe_stdev(dists),
                "risk_min": round(min(risks), 3), "risk_max": round(max(risks), 3),
                "risk_avg": round(sum(risks) / len(risks), 3), "risk_stdev": safe_stdev(risks),
            }
        })
    return benchmark
