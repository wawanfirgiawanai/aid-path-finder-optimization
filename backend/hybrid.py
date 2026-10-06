"""Two-level hybrid A*-GA for multi-agent, multi-destination relief routing.

  Level 1 (routing)    A* computes the exact least-cost road path between every pair of key
                       nodes (depots + destinations) under the risk-aware cost
                           Cost_ij = d_ij * (1 + r_ij)
                       The haversine heuristic is admissible because Cost_ij >= d_ij.

  Level 2 (allocation) A genetic algorithm decides which agent serves which destination and
                       in what order (an NP-hard multi-depot open VRP), using the level-1
                       cost matrix. Chromosome = permutation of destination tokens and
                       K-1 agent separators. Order crossover (OX1), multi-domain inversion
                       mutation (Xin et al., Sensors 2019), tournament selection, elitism,
                       greedy warm start and stagnation-based early stopping.
"""
import heapq
import itertools
import math
import random
import time

from algorithms import (DEFAULT_ALGO_PARAMS, haversine, _assign_greedy, _assign_forced,
                        build_route_entry, build_summary)

EMPTY_ROUTE_PENALTY = 1e9


# ========== LEVEL 1: A* ON THE RISK-AWARE COST ==========
def astar_cost(graph, source, target, coords):
    """A* on the stored edge cost d*(1+r) with an admissible haversine heuristic."""
    if source == target:
        return [source], 0.0, 0
    tlat, tlng = coords[target]

    def h(n):
        lat, lng = coords[n]
        return haversine(lat, lng, tlat, tlng)

    g = {source: 0.0}
    prev = {source: None}
    counter = itertools.count()
    pq = [(h(source), next(counter), source)]
    closed = set()
    explored = 0
    while pq:
        _, _, cur = heapq.heappop(pq)
        if cur in closed:
            continue
        closed.add(cur)
        explored += 1
        if cur == target:
            break
        for nb in graph.neighbors(cur):
            if nb in closed:
                continue
            tg = g[cur] + graph[cur][nb].get('cost', 1.0)
            if tg < g.get(nb, math.inf):
                g[nb] = tg
                prev[nb] = cur
                heapq.heappush(pq, (tg + h(nb), next(counter), nb))
    if target not in g:
        return None, math.inf, explored
    path = []
    c = target
    while c is not None:
        path.append(c)
        c = prev[c]
    path.reverse()
    return path, g[target], explored


def build_cost_matrix(graph, key_nodes):
    """Pairwise A* between key nodes. Graph is undirected, so i<j suffices."""
    coords = {n: (d['y'], d['x']) for n, d in graph.nodes(data=True)}
    n = len(key_nodes)
    M = [[0.0] * n for _ in range(n)]
    paths = {}
    explored = 0
    for i in range(n):
        for j in range(i + 1, n):
            p, c, e = astar_cost(graph, key_nodes[i], key_nodes[j], coords)
            explored += e
            M[i][j] = M[j][i] = c
            paths[(i, j)] = p
            paths[(j, i)] = list(reversed(p)) if p else None
    for i in range(n):
        paths[(i, i)] = [key_nodes[i]]
    return M, paths, explored


# ========== LEVEL 2: ALLOCATION + SEQUENCING GA ==========
class AllocationProblem:
    """Open multi-depot VRP on the level-1 matrix.

    Tokens 0..n-1 are destinations; tokens n..n+K-2 are separators between agents.
    Agent k serves the k-th group of destinations in order, starting from its depot.
    """

    def __init__(self, M, agent_key_idx, dest_key_idx, force_distribution=False, makespan_weight=0.0):
        self.M = M
        self.agent_key = agent_key_idx
        self.dest_key = dest_key_idx
        self.n = len(dest_key_idx)
        self.K = len(agent_key_idx)
        self.force = force_distribution and self.n >= self.K
        self.w_ms = makespan_weight
        self.evals = 0

    def tokens(self):
        return list(range(self.n + self.K - 1))

    def decode(self, chrom):
        groups = [[] for _ in range(self.K)]
        k = 0
        for t in chrom:
            if t >= self.n:
                k += 1
            else:
                groups[k].append(t)
        return groups

    def route_costs(self, chrom):
        costs = [0.0] * self.K
        k = 0
        prev = self.agent_key[0]
        for t in chrom:
            if t >= self.n:
                k += 1
                prev = self.agent_key[k]
            else:
                nxt = self.dest_key[t]
                costs[k] += self.M[prev][nxt]
                prev = nxt
        return costs

    def fitness(self, chrom):
        """Objective to minimise: total cost (+ optional makespan term, + penalty)."""
        self.evals += 1
        costs = self.route_costs(chrom)
        f = sum(costs)
        if self.w_ms:
            f += self.w_ms * max(costs)
        if self.force:
            empty = sum(1 for g in self.decode(chrom) if not g)
            f += EMPTY_ROUTE_PENALTY * empty
        return f

    def encode(self, groups):
        chrom = []
        sep = self.n
        for k, g in enumerate(groups):
            chrom.extend(g)
            if k < self.K - 1:
                chrom.append(sep)
                sep += 1
        return chrom


def order_crossover(p1, p2, rng):
    """OX1: copy a slice of p1, fill the rest in p2 order."""
    L = len(p1)
    if L < 3:
        return list(p1)
    a, b = sorted(rng.sample(range(L), 2))
    child = [None] * L
    child[a:b + 1] = p1[a:b + 1]
    used = set(p1[a:b + 1])
    fill = [g for g in p2 if g not in used]
    idx = 0
    for i in range(L):
        if child[i] is None:
            child[i] = fill[idx]
            idx += 1
    return child


def multi_domain_inversion(chrom, problem, rng):
    """Xin et al. (2019): 4 random cut points a<b<c<d give 6 single-domain inversions
    (a-b, a-c, a-d, b-c, b-d, c-d) plus a double inversion (a-b & c-d). The fittest of
    the 7 offspring replaces the chromosome."""
    L = len(chrom)
    if L < 2:
        return list(chrom)
    if L < 4:
        a, b = sorted(rng.sample(range(L), 2))
        return chrom[:a] + chrom[a:b + 1][::-1] + chrom[b + 1:]
    a, b, c, d = sorted(rng.sample(range(L), 4))

    def inv(x, i, j):
        return x[:i] + x[i:j + 1][::-1] + x[j + 1:]

    children = [inv(chrom, i, j) for i, j in ((a, b), (a, c), (a, d), (b, c), (b, d), (c, d))]
    children.append(inv(inv(chrom, a, b), c, d))
    return min(children, key=problem.fitness)


def allocation_ga(problem, warm_starts, p, rng):
    pop_size = p['hga_population']
    max_gen = p['hga_generations']
    pc = p['hga_crossover_rate']
    pm = p['hga_mutation_rate']
    k_tour = p['hga_tournament_k']
    elit = p['hga_elitism']
    stag_limit = p['hga_stagnation_limit']

    base = problem.tokens()
    population = [list(w) for w in warm_starts]
    while len(population) < pop_size:
        c = list(base)
        rng.shuffle(c)
        population.append(c)
    population = population[:pop_size]
    fit = [problem.fitness(c) for c in population]

    best_i = min(range(len(population)), key=fit.__getitem__)
    best, best_f = list(population[best_i]), fit[best_i]
    history = [best_f]
    stagnation, gen_done = 0, 0
    if len(base) <= 1:
        return best, best_f, history, 0, False

    def tournament():
        idx = rng.sample(range(len(population)), min(k_tour, len(population)))
        return population[min(idx, key=fit.__getitem__)]

    for gen in range(max_gen):
        gen_done = gen + 1
        ranked = sorted(range(len(population)), key=fit.__getitem__)
        new_pop = [list(population[i]) for i in ranked[:elit]]
        new_fit = [fit[i] for i in ranked[:elit]]
        while len(new_pop) < pop_size:
            p1 = tournament()
            child = order_crossover(p1, tournament(), rng) if rng.random() < pc else list(p1)
            if rng.random() < pm:
                child = multi_domain_inversion(child, problem, rng)
            new_pop.append(child)
            new_fit.append(problem.fitness(child))
        population, fit = new_pop, new_fit

        gi = min(range(len(population)), key=fit.__getitem__)
        if fit[gi] < best_f - 1e-6:
            best, best_f = list(population[gi]), fit[gi]
            stagnation = 0
        else:
            stagnation += 1
        history.append(best_f)
        if stagnation >= stag_limit:
            break
    return best, best_f, history, gen_done, stagnation >= stag_limit


def exact_allocation(problem, max_tokens=10):
    """Brute-force optimum of the level-2 problem (used only to report optimality gaps)."""
    toks = problem.tokens()
    if len(toks) > max_tokens:
        return None, None
    best, best_f = None, math.inf
    for perm in itertools.permutations(toks):
        f = problem.fitness(perm)
        if f < best_f:
            best, best_f = list(perm), f
    return best, best_f


def _greedy_groups(agents_spec, dest_nodes, M, key_index, force):
    """Run the same greedy/forced assignment the baselines use, on the level-1 matrix."""
    agents = [{"start": s, "current": s, "assigned": [], "cost": 0} for s in agents_spec]
    cache = {}
    nodes = list(dict.fromkeys(agents_spec + dest_nodes))
    for a in nodes:
        for b in nodes:
            cache[(a, b)] = M[key_index[a]][key_index[b]]
    if force and len(agents) > 1:
        _assign_forced(agents, dest_nodes, cache)
    else:
        _assign_greedy(agents, dest_nodes, cache)
    pos = {d: i for i, d in enumerate(dest_nodes)}
    return [[pos[d] for d in ag['assigned']] for ag in agents]


# ========== SOLVER ==========
def solve_hybrid(graph_service, starts, destinations, algo_params=None, force_distribution=False,
               seed=None, return_problem=False):
    p = {**DEFAULT_ALGO_PARAMS, **(algo_params or {})}
    rng = random.Random(seed) if seed is not None else random.Random(random.random())
    graph = graph_service.graph
    t0 = time.perf_counter()

    agents = []
    for si, s in enumerate(starts):
        for ai in range(s.get('agents', 1)):
            agents.append({"start": int(s['node_id']), "start_label": f"S{si + 1}",
                           "agent_label": f"S{si + 1}-A{ai + 1}"})
    dest_nodes = [int(d['node_id']) for d in destinations]
    dest_labels = [f"E{i + 1}" for i in range(len(dest_nodes))]

    # ---- Level 1 ----
    key_nodes = list(dict.fromkeys([a['start'] for a in agents] + dest_nodes))
    key_index = {nd: i for i, nd in enumerate(key_nodes)}
    M, paths, explored = build_cost_matrix(graph, key_nodes)
    t1 = time.perf_counter()

    # ---- Level 2 ----
    agent_key = [key_index[a['start']] for a in agents]
    dest_key = [key_index[d] for d in dest_nodes]
    problem = AllocationProblem(M, agent_key, dest_key, force_distribution, p['hga_makespan_weight'])
    meta = {"level1_ms": round((t1 - t0) * 1000, 2), "key_nodes": len(key_nodes),
            "nodes_explored": explored}

    if force_distribution and len(agents) > len(dest_nodes):
        # More agents than destinations: every agent is dispatched to its nearest destination
        groups = _greedy_groups([a['start'] for a in agents], dest_nodes, M, key_index, True)
        history, gens, early = [], 0, False
    else:
        greedy = _greedy_groups([a['start'] for a in agents], dest_nodes, M, key_index, force_distribution)
        warm = [problem.encode(greedy)]
        best, _, history, gens, early = allocation_ga(problem, warm, p, rng)
        groups = problem.decode(best)
    t2 = time.perf_counter()
    meta.update({"level2_ms": round((t2 - t1) * 1000, 2), "generations": gens, "stopped_early": early,
                 "fitness_evals": problem.evals, "convergence": [round(h, 2) for h in history]})

    # ---- Assemble road-level routes from level-1 paths ----
    routes = []
    for k, ag in enumerate(agents):
        g = groups[k]
        if not g:
            continue
        seq = [agent_key[k]] + [dest_key[t] for t in g]
        full_path, segments = [], []
        for j in range(len(seq) - 1):
            seg = paths[(seq[j], seq[j + 1])] or [key_nodes[seq[j]], key_nodes[seq[j + 1]]]
            sd, sc, sr = graph_service.get_path_metrics(seg)
            fl = ag['start_label'] if j == 0 else dest_labels[g[j - 1]]
            tl = dest_labels[g[j]]
            segments.append({"from_label": fl, "to_label": tl, "route_label": f"{fl} -> {tl}",
                             "distance": sd, "cost": sc, "avg_risk": sr})
            full_path.extend(seg[1:] if full_path else seg)
        routes.append(build_route_entry(graph_service, ag['agent_label'], ag['start_label'],
                                        [dest_labels[t] for t in g], full_path,
                                        graph_service.get_route_geometry(full_path), segments))

    t3 = time.perf_counter()
    comp_time = round((t3 - t0) * 1000, 2)
    meta.update({"matrix_ms": meta["level1_ms"], "allocation_ms": meta["level2_ms"],
                 "routing_ms": round((t3 - t2) * 1000, 2),  # assembly of the stored Level-1 paths
                 "fallback_counts": {}, "fallback_used": False, "fallback_type": None, "fallback_count": 0})
    result = {"routes": routes, "algorithm": "hybrid",
              "summary": build_summary(routes, comp_time, len(destinations)), "meta": meta}
    if return_problem:
        return result, problem
    return result
