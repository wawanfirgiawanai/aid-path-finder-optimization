"""Experiments of the conference paper (vConfrence): one road network, 40 documented test cases.

Every test case is read from dataset/test_cases/test_cases.json (build it with build_dataset.py).

Phases (run all, or pick with --phase):
  tune     random search of GA, ACO and the hybrid on the tuning cases TUNE-A..D
  main     20 main cases (SA-SD, SA-MD, MA-SD, MA-MD x 5)  x 6 algorithms x 30 runs
  scale    20 scalability cases (5/10/20/30 destinations x 5) x 6 algorithms x 10 runs
  report   tables, statistics (Friedman, Wilcoxon-Holm, A12) and figures

  python experiments/run_experiments.py --phase all --jobs 12
  python experiments/run_experiments.py --phase all --params-file dataset/tuned_params.json --out experiments/runs/x
"""
import argparse
import itertools
import json
import os
import random
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
BACKEND = PROJECT / 'backend'
DATASET = PROJECT / 'dataset'
RESULTS = ROOT / 'results'
FIGURES = ROOT / 'figures'
PARAMS_FILE = None
sys.path.insert(0, str(BACKEND))

NETWORK = 'mamuju_r1500'
CENTER = (-2.692, 118.898)
ALGOS = ['dijkstra', 'astar', 'bfs', 'ga', 'aco', 'hybrid']
NAMES = {'dijkstra': 'Dijkstra', 'astar': 'A*', 'bfs': 'BFS', 'ga': 'GA', 'aco': 'ACO', 'hybrid': 'Hybrid A*-GA'}
PROPOSED = 'hybrid'
MAIN_GROUPS = ['SA-SD', 'SA-MD', 'MA-SD', 'MA-MD']
SCALE_GROUPS = ['SC-05', 'SC-10', 'SC-20', 'SC-30']
MAIN_RUNS = 30
SCALE_RUNS = 10
TUNE_RUNS = 5
TUNE_CONFIGS = 24

SEARCH_SPACE = {
    'ga': {'ga_population': [30, 50, 100, 120], 'ga_generations': [50, 100, 200, 250],
           'ga_crossover_rate': [0.7, 0.8, 0.9], 'ga_mutation_rate': [0.02, 0.05, 0.1, 0.2],
           'ga_tournament_k': [2, 3, 4], 'ga_elitism': [1, 2, 5]},
    'aco': {'aco_ants': [10, 20, 40], 'aco_iterations': [30, 50, 100],
            'aco_alpha': [0.5, 1.0, 2.0], 'aco_beta': [1.0, 2.0, 3.0, 5.0],
            'aco_evaporation': [0.1, 0.3, 0.5, 0.7]},
    'hybrid': {'hga_population': [30, 60, 100], 'hga_generations': [100, 200, 400],
               'hga_crossover_rate': [0.7, 0.8, 0.9], 'hga_mutation_rate': [0.1, 0.3, 0.5],
               'hga_tournament_k': [2, 3, 5], 'hga_elitism': [1, 2, 4],
               'hga_stagnation_limit': [30, 50, 100]},
}
TUNE_CASES = {'ga': ['TUNE-A', 'TUNE-B'], 'aco': ['TUNE-A', 'TUNE-B'], 'hybrid': ['TUNE-C', 'TUNE-D']}
# computational budget used to break ties between configurations of equal quality (deterministic)
BUDGET = {'ga': lambda c: c['ga_population'] * c['ga_generations'],
          'aco': lambda c: c['aco_ants'] * c['aco_iterations'],
          'hybrid': lambda c: c['hga_population'] * c['hga_generations']}

_GS = None
_CASES = None


def cases():
    global _CASES
    if _CASES is None:
        _CASES = {c['id']: c for c in json.loads((DATASET / 'test_cases' / 'test_cases.json').read_text())}
    return _CASES


def get_graph():
    global _GS
    if _GS is None:
        os.chdir(BACKEND)
        from graph_service import GraphService
        gs = GraphService()
        gs.load_from_csv(DATASET / 'network' / f'{NETWORK}_nodes.csv', DATASET / 'network' / f'{NETWORK}_edges.csv',
                         *CENTER)
        _GS = gs
    return _GS


def instance(case):
    starts = [{'node_id': str(p['node_id']), 'agents': p['agents']} for p in case['depots']]
    dests = [{'node_id': str(p['node_id'])} for p in case['destinations']]
    return starts, dests


def run_one(task):
    from algorithms import solve_vrp
    gs = get_graph()
    case = cases()[task['case_id']]
    starts, dests = instance(case)
    random.seed(task['seed'])
    r = solve_vrp(gs, starts, dests, task['algo'], task.get('params'), case['force_distribution'])
    s = r['summary']
    out = {'phase': task['phase'], 'case_id': case['id'], 'group': case['group'], 'n_dest': case['n_destinations'],
           'algo': task['algo'], 'seed': task['seed'], 'config_id': task.get('config_id'),
           'cost': s['total_cost'], 'distance': s['total_distance'], 'risk_exposure': s['risk_exposure'],
           'max_risk': s['max_risk'], 'high_risk_distance': s['high_risk_distance'],
           'makespan_cost': s['makespan_cost'], 'time_ms': s['computation_time_ms'],
           'agents_used': s['agents_used'], 'covered': s['destinations_covered']}
    meta = r.get('meta')
    if meta:
        out.update({'generations': meta.get('generations'), 'level1_ms': meta.get('level1_ms'),
                    'level2_ms': meta.get('level2_ms')})
        if task.get('keep_convergence'):
            out['convergence'] = json.dumps(meta.get('convergence', []))
    return out


def exact_optimum(case_id):
    """Proven optimum: exact A* paths + enumeration of all allocations/orders (small cases only)."""
    from hybrid import solve_hybrid, exact_allocation
    gs = get_graph()
    case = cases()[case_id]
    if case['force_distribution'] and case['n_agents'] > case['n_destinations']:
        return None  # every agent goes to its nearest destination: no allocation decision
    starts, dests = instance(case)
    _, prob = solve_hybrid(gs, starts, dests, {'hga_generations': 0}, case['force_distribution'], seed=0,
                           return_problem=True)
    _, f = exact_allocation(prob, max_tokens=9)
    return f


def pmap(fn, tasks, jobs, label='runs'):
    n, out = len(tasks), []
    step = max(1, n // 20)

    def report(i):
        if i % step == 0 or i == n:
            print(f'[progress] {label} {i}/{n}', flush=True)
    if jobs <= 1:
        for i, t in enumerate(tasks, 1):
            out.append(fn(t))
            report(i)
        return out
    with ProcessPoolExecutor(max_workers=jobs) as ex:
        for i, r in enumerate(ex.map(fn, tasks, chunksize=max(1, n // (jobs * 8))), 1):
            out.append(r)
            report(i)
    return out


def save(rows, name):
    import pandas as pd
    RESULTS.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(RESULTS / f'{name}.csv', index=False)
    return df


def load_params():
    fn = Path(PARAMS_FILE) if PARAMS_FILE else RESULTS / 'tuned_params.json'
    return json.loads(fn.read_text()) if fn.exists() else {}


def merged_params():
    p = {}
    for v in load_params().values():
        p.update(v)
    return p


# ---------------------------------------------------------------- phases
def phase_tune(jobs):
    import pandas as pd
    rng = random.Random(123)
    best_all, rows = {}, []
    for algo, space in SEARCH_SPACE.items():
        keys = list(space)
        cfgs = [dict(zip(keys, c)) for c in rng.sample(list(itertools.product(*[space[k] for k in keys])),
                                                          TUNE_CONFIGS)]
        tasks = [{'phase': 'tune', 'case_id': cid, 'algo': algo, 'params': cfg, 'seed': 1000 + run, 'config_id': ci}
                 for ci, cfg in enumerate(cfgs) for cid in TUNE_CASES[algo] for run in range(TUNE_RUNS)]
        t0 = time.time()
        df = pd.DataFrame(pmap(run_one, tasks, jobs, f'tune-{algo}'))
        print(f'[tune] {algo}: {len(tasks)} runs in {time.time() - t0:.0f}s', flush=True)
        df['norm_cost'] = df['cost'] / df.groupby('case_id')['cost'].transform('min')
        agg = df.groupby('config_id').agg(norm_cost=('norm_cost', 'mean'), time_ms=('time_ms', 'mean')).reset_index()
        agg['budget'] = [BUDGET[algo](cfgs[i]) for i in agg['config_id']]
        tol = agg['norm_cost'].min() * 1.005
        # deterministic: best quality, ties within 0.5 % broken by smallest budget, then quality, then id
        best_id = int(agg[agg['norm_cost'] <= tol].sort_values(['budget', 'norm_cost', 'config_id']).iloc[0]['config_id'])
        best_all[algo] = cfgs[best_id]
        for ci, cfg in enumerate(cfgs):
            a = agg[agg['config_id'] == ci].iloc[0]
            rows.append({'algo': algo, 'config_id': ci, **cfg, 'mean_norm_cost': round(a['norm_cost'], 5),
                         'mean_time_ms': round(a['time_ms'], 1), 'budget': int(a['budget']),
                         'selected': ci == best_id})
        print(f'[tune] {algo} selected: {cfgs[best_id]}', flush=True)
    save(rows, 'tuning')
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / 'tuned_params.json').write_text(json.dumps(best_all, indent=2))


def run_group(phase, groups, runs, jobs, keep_conv=None):
    params = merged_params()
    ids = [c['id'] for c in cases().values() if c['group'] in groups]
    tasks = [{'phase': phase, 'case_id': cid, 'algo': a, 'params': params, 'seed': s + 1,
              'keep_convergence': bool(keep_conv and a == PROPOSED and cases()[cid]['group'] == keep_conv)}
             for cid in ids for a in ALGOS for s in range(runs)]
    t0 = time.time()
    res = pmap(run_one, tasks, jobs, phase)
    print(f'[{phase}] {len(tasks)} runs in {time.time() - t0:.0f}s', flush=True)
    return res, ids


def phase_main(jobs):
    res, ids = run_group('main', MAIN_GROUPS, MAIN_RUNS, jobs)
    save(res, 'main_runs')
    save([{'case_id': cid, 'optimal_cost': exact_optimum(cid)} for cid in ids], 'optimum')


def phase_scale(jobs):
    res, _ = run_group('scale', SCALE_GROUPS, SCALE_RUNS, jobs, keep_conv='SC-30')
    save(res, 'scale_runs')


# ---------------------------------------------------------------- report
def holm(pvals):
    order = sorted(range(len(pvals)), key=lambda i: pvals[i])
    adj, running = [0.0] * len(pvals), 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (len(pvals) - rank) * pvals[i]))
        adj[i] = running
    return adj


def a12(x, y):
    """Vargha-Delaney A12: probability that a value of x is lower (better) than one of y."""
    return sum(1.0 if a < b else 0.5 if a == b else 0.0 for a in x for b in y) / (len(x) * len(y))


def case_table(runs, opt):
    import pandas as pd
    rows = []
    for (cid, algo), d in runs.groupby(['case_id', 'algo']):
        best = d.loc[d['cost'].idxmin()]
        o = opt.get(cid)
        rows.append({'case_id': cid, 'group': d['group'].iloc[0], 'n_dest': d['n_dest'].iloc[0],
                     'algo': algo, 'algorithm': NAMES[algo], 'runs': len(d),
                     'dist_best': best['distance'], 'dist_mean': d['distance'].mean(), 'dist_std': d['distance'].std(),
                     'risk_mean': d['risk_exposure'].mean(), 'cost_best': best['cost'],
                     'cost_mean': d['cost'].mean(), 'cost_std': d['cost'].std(),
                     'time_mean_ms': d['time_ms'].mean(), 'time_std_ms': d['time_ms'].std(),
                     'optimum': o, 'gap_pct': None if pd.isna(o) else 100 * (d['cost'].mean() - o) / o,
                     'hit_opt': None if pd.isna(o) else int((d['cost'] <= o + 0.05).sum())})
    t = pd.DataFrame(rows)
    dij = t[t.algo == 'dijkstra'].set_index('case_id')['cost_mean']
    t['vs_dijkstra_pct'] = [100 * (r.cost_mean - dij[r.case_id]) / dij[r.case_id] for r in t.itertuples()]
    return t


def paired(t, subset_label):
    """Wilcoxon signed-rank of the hybrid vs each algorithm over test cases (case-mean cost), Holm."""
    from scipy.stats import wilcoxon
    piv = t.pivot_table(index='case_id', columns='algo', values='cost_mean')
    rows, ps = [], []
    for algo in [a for a in ALGOS if a != PROPOSED]:
        d = (piv[PROPOSED] - piv[algo]).dropna()
        rel = 100 * d / piv[algo]
        p = 1.0 if (d.abs() < 1e-6).all() else wilcoxon(d, zero_method='zsplit').pvalue
        ps.append(p)
        rows.append({'subset': subset_label, 'vs': NAMES[algo], 'cases': len(d),
                     'hybrid_better': int((d < -1e-6).sum()), 'ties': int((d.abs() <= 1e-6).sum()),
                     'hybrid_worse': int((d > 1e-6).sum()), 'mean_change_pct': round(rel.mean(), 3),
                     'largest_saving_pct': round(rel.min(), 3), 'p': p})
    for r, pa in zip(rows, holm(ps)):
        r['p_holm'] = pa
    return rows


def per_case_stochastic(runs):
    """Run-level comparison of the hybrid with GA and ACO inside each case (30 or 10 runs)."""
    from scipy.stats import mannwhitneyu
    out = []
    for cid, d in runs.groupby('case_id'):
        h = d[d.algo == PROPOSED]['cost'].tolist()
        for algo in ('ga', 'aco'):
            x = d[d.algo == algo]['cost'].tolist()
            p = 1.0 if len(set(h + x)) == 1 else mannwhitneyu(h, x, alternative='two-sided').pvalue
            out.append({'case_id': cid, 'vs': NAMES[algo], 'A12': round(a12(h, x), 3), 'p': p})
    return out


def phase_report():
    import pandas as pd
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from scipy.stats import friedmanchisquare
    FIGURES.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({'font.family': 'serif', 'font.size': 7, 'legend.fontsize': 6.5, 'figure.dpi': 300})
    colors = {'dijkstra': '#3B82F6', 'astar': '#8B5CF6', 'bfs': '#F97316', 'ga': '#22C55E', 'aco': '#EF4444',
              'hybrid': '#B45309'}
    m = pd.read_csv(RESULTS / 'main_runs.csv')
    s = pd.read_csv(RESULTS / 'scale_runs.csv')
    opt = pd.read_csv(RESULTS / 'optimum.csv').set_index('case_id')['optimal_cost'].to_dict()
    tm, ts = case_table(m, opt), case_table(s, {})
    tcases = pd.concat([tm, ts])
    tcases.round(4).to_csv(RESULTS / 'table_cases.csv', index=False)

    # main scenarios: mean over the 5 cases of each group
    rows = []
    for g in MAIN_GROUPS:
        for a in ALGOS:
            d = tm[(tm.group == g) & (tm.algo == a)]
            rows.append({'scenario': g, 'algorithm': NAMES[a], 'cases': len(d),
                         'dist_mean': d.dist_mean.mean(), 'risk_mean': d.risk_mean.mean(),
                         'cost_mean': d.cost_mean.mean(), 'cost_std_runs': d.cost_std.mean(),
                         'vs_dijkstra_pct': d.vs_dijkstra_pct.mean(), 'best_vs_dijkstra_pct': d.vs_dijkstra_pct.min(),
                         'gap_pct': d.gap_pct.mean() if d.gap_pct.notna().any() else None,
                         'hit_opt': int(d.hit_opt.sum()) if d.hit_opt.notna().any() else None,
                         'runs': int(d.runs.sum()), 'time_mean_ms': d.time_mean_ms.mean()})
    tmain = pd.DataFrame(rows)
    tmain.round(4).to_csv(RESULTS / 'table_main.csv', index=False)

    # scalability
    rows = []
    for g in SCALE_GROUPS:
        for a in ALGOS:
            d = ts[(ts.group == g) & (ts.algo == a)]
            rows.append({'group': g, 'n_dest': int(d.n_dest.iloc[0]), 'algorithm': NAMES[a], 'algo': a,
                         'cost_mean': d.cost_mean.mean(), 'cost_std_runs': d.cost_std.mean(),
                         'vs_dijkstra_pct': d.vs_dijkstra_pct.mean(), 'best_vs_dijkstra_pct': d.vs_dijkstra_pct.min(),
                         'time_mean_ms': d.time_mean_ms.mean()})
    tscale = pd.DataFrame(rows)
    hyb = s[s.algo == PROPOSED].groupby('group')[['level1_ms', 'level2_ms']].mean()
    tscale = tscale.merge(hyb, left_on='group', right_index=True, how='left')
    tscale.loc[tscale.algo != PROPOSED, ['level1_ms', 'level2_ms']] = None
    tscale.round(4).to_csv(RESULTS / 'table_scale.csv', index=False)

    # hybrid gain per case
    piv = tcases.pivot_table(index='case_id', columns='algo', values='cost_mean')
    gain = pd.DataFrame({'case_id': piv.index, 'dijkstra': piv['dijkstra'].values, 'hybrid': piv[PROPOSED].values})
    gain['optimum'] = gain['case_id'].map(opt)
    gain['saving_vs_dijkstra_pct'] = 100 * (gain['dijkstra'] - gain['hybrid']) / gain['dijkstra']
    gain.round(3).to_csv(RESULTS / 'table_hybrid_gain.csv', index=False)

    # statistics over test cases
    stats = paired(tcases, 'all 40 cases') + paired(tm, 'main 20 cases') + paired(ts, 'scalability 20 cases')
    pd.DataFrame(stats).to_csv(RESULTS / 'stats_cases.csv', index=False)
    pc = pd.DataFrame(per_case_stochastic(pd.concat([m, s])))
    pc['p_holm'] = holm(pc['p'].tolist())
    pc.to_csv(RESULTS / 'stats_runs_per_case.csv', index=False)
    fr_all = friedmanchisquare(*[piv[a] for a in ALGOS])
    summary = {'friedman_all_cases': {'statistic': fr_all.statistic, 'p': fr_all.pvalue, 'cases': len(piv)},
               'runs': {'main': len(m), 'scalability': len(s)},
               'cases_hybrid_reached_optimum': int((tm[(tm.algo == PROPOSED) & tm.optimum.notna()].hit_opt
                                                     == tm[(tm.algo == PROPOSED) & tm.optimum.notna()].runs).sum()),
               'cases_with_optimum': int(tm[(tm.algo == PROPOSED)].optimum.notna().sum())}
    (RESULTS / 'summary.json').write_text(json.dumps(summary, indent=2, default=float))

    # figure: mean cost relative to Dijkstra per main scenario (bars) with case range
    fig, ax = plt.subplots(figsize=(3.4, 2.2))
    w = 0.13
    for i, a in enumerate(ALGOS):
        vals = [tm[(tm.group == g) & (tm.algo == a)].cost_mean.mean() for g in MAIN_GROUPS]
        lo = [vals[k] - tm[(tm.group == g) & (tm.algo == a)].cost_mean.min() for k, g in enumerate(MAIN_GROUPS)]
        hi = [tm[(tm.group == g) & (tm.algo == a)].cost_mean.max() - vals[k] for k, g in enumerate(MAIN_GROUPS)]
        ax.bar([x + (i - 2.5) * w for x in range(4)], vals, w, yerr=[lo, hi], capsize=1.2, color=colors[a],
               label=NAMES[a], error_kw={'lw': 0.5})
    ax.set_xticks(range(4))
    ax.set_xticklabels(MAIN_GROUPS)
    ax.set_ylabel('Mean total cost (5 cases)')
    ax.legend(ncol=3, frameon=False, loc='upper left', fontsize=6)
    ax.set_ylim(0, ax.get_ylim()[1] * 1.25)
    fig.tight_layout(pad=0.2)
    fig.savefig(FIGURES / 'fig_main_cost.png')
    plt.close(fig)

    # figure: scalability
    fig, axes = plt.subplots(2, 1, figsize=(3.4, 3.5), sharex=True)
    for a in ALGOS:
        d = tscale[tscale.algo == a]
        axes[0].plot(d.n_dest, d.vs_dijkstra_pct, marker='o', ms=2.5, lw=0.9, color=colors[a], label=NAMES[a])
        axes[1].plot(d.n_dest, d.time_mean_ms, marker='o', ms=2.5, lw=0.9, color=colors[a])
    axes[0].axhline(0, color='grey', lw=0.5)
    axes[0].set_ylabel('Cost vs. Dijkstra (%)')
    axes[1].set_yscale('log')
    axes[1].set_ylabel('Mean time (ms)')
    axes[1].set_xlabel('Number of destinations (4 agents)')
    axes[1].set_xticks([5, 10, 20, 30])
    h, lab = axes[0].get_legend_handles_labels()
    fig.legend(h, lab, ncol=3, frameon=False, loc='upper center', fontsize=6)
    fig.tight_layout(rect=(0, 0, 1, 0.92), pad=0.2, h_pad=0.4)
    fig.savefig(FIGURES / 'fig_scalability.png')
    plt.close(fig)

    # figure: hybrid convergence on SC-30
    conv = s[(s.algo == PROPOSED) & (s.group == 'SC-30')].dropna(subset=['convergence'])
    if len(conv):
        fig, ax = plt.subplots(figsize=(3.4, 2.1))
        for cid, d in conv.groupby('case_id'):
            for i, (_, row) in enumerate(d.iterrows()):
                h = json.loads(row['convergence'])
                ax.plot(range(len(h)), [v / h[0] * 100 for v in h], lw=0.5, alpha=0.6,
                        label=cid if i == 0 else None)
        ax.set_xlabel('Generation')
        ax.set_ylabel('Best fitness (% of greedy)')
        ax.legend(frameon=False, fontsize=5.5)
        fig.tight_layout(pad=0.2)
        fig.savefig(FIGURES / 'fig_convergence.png')
        plt.close(fig)
    print('[report] written to', RESULTS, 'and', FIGURES, flush=True)
    # one Excel workbook with every result (one sheet per experiment) + journal-quality figures
    try:
        sys.path.insert(0, str(ROOT))
        from export_excel import export
        export(RESULTS, FIGURES)
    except ImportError as e:  # openpyxl missing: CSV/figures are still complete
        print(f'[excel] skipped ({e}); pip install openpyxl', flush=True)


def main():
    global RESULTS, FIGURES, PARAMS_FILE
    ap = argparse.ArgumentParser()
    ap.add_argument('--phase', default='all', choices=['all', 'tune', 'main', 'scale', 'report'])
    ap.add_argument('--jobs', type=int, default=8)
    ap.add_argument('--out', default=None, help='write results/ and figures/ under this folder')
    ap.add_argument('--params-file', default=None,
                    help='evaluate with these parameters (e.g. dataset/tuned_params.json) instead of this run\'s tuning')
    a = ap.parse_args()
    if a.out:
        out = Path(a.out).resolve()   # absolute: get_graph() changes the working directory
        RESULTS, FIGURES = out / 'results', out / 'figures'
    if a.params_file:
        PARAMS_FILE = str(Path(a.params_file).resolve())
        print(f'[params] evaluating with parameters from {a.params_file}', flush=True)
    phases = ['tune', 'main', 'scale', 'report'] if a.phase == 'all' else [a.phase]
    for k, ph in enumerate(phases, 1):
        print(f'[phase] {k}/{len(phases)} {ph}', flush=True)
        t0 = time.time()
        if ph == 'report':
            phase_report()
        else:
            globals()[f'phase_{ph}'](a.jobs)
        print(f'== {ph} done in {time.time() - t0:.0f}s', flush=True)


if __name__ == '__main__':
    main()
