"""Recompute Tables III-V and the statistics of the ICITISEE 2026 paper from the raw runs.

The paper reports five methods (A*, BFS, GA, ACO, hybrid A*-GA); Dijkstra was run as a reference
method (800 extra runs) and is excluded here. Every baseline combines its path algorithm with the
greedy allocation, so "A*" below is the A*-based greedy baseline.

Definitions
    Best        distance, risk exposure and cost of the minimum-cost run of a test case
                (ties: lowest seed), i.e. all three values come from the same run
    Average/Std mean and sample standard deviation over the runs of a test case
    Time        mean and standard deviation of the wall-clock time over the runs of a test case
    Opt. hits   runs whose cost is within 0.05 of the verified optimum (enumeration, 15 cases)
    Scenario values are the mean over its five test cases.
    Friedman    five methods, per-case mean cost, 40 cases
    Wilcoxon    hybrid vs each of the four baselines (zero_method='zsplit'), Holm over the four tests
    A12         P(C_hybrid < C_baseline) + 0.5 P(C_hybrid = C_baseline) over the runs of a case,
                averaged over the 40 cases

usage: python experiments/paper_tables.py [--results experiments/results]
"""
import argparse
import json
from pathlib import Path

import pandas as pd
from scipy.stats import friedmanchisquare, wilcoxon

ROOT = Path(__file__).resolve().parent
METHODS = ['astar', 'bfs', 'ga', 'aco', 'hybrid']
BASELINES = METHODS[:-1]
NAMES = {'astar': 'A*', 'bfs': 'BFS', 'ga': 'GA', 'aco': 'ACO', 'hybrid': 'Hybrid A*-GA'}
MAIN = ['SA-SD', 'SA-MD', 'MA-SD', 'MA-MD']
OPT_TOL = 0.05


def holm(ps):
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    adj, run = [0.0] * len(ps), 0.0
    for rank, i in enumerate(order):
        run = max(run, min(1.0, (len(ps) - rank) * ps[i]))
        adj[i] = run
    return adj


def a12(x, y):
    return sum(1.0 if a < b else 0.5 if a == b else 0.0 for a in x for b in y) / (len(x) * len(y))


def per_case(runs, opt):
    rows = []
    for (cid, algo), d in runs.groupby(['case_id', 'algo']):
        best = d.sort_values(['cost', 'seed']).iloc[0]
        o = opt.get(cid)
        rows.append({'group': d.group.iloc[0], 'case_id': cid, 'algo': algo, 'runs': len(d),
                     'dist_best': best.distance, 'dist_mean': d.distance.mean(), 'dist_std': d.distance.std(),
                     'risk_best': best.risk_exposure, 'risk_mean': d.risk_exposure.mean(),
                     'risk_std': d.risk_exposure.std(),
                     'cost_best': best.cost, 'cost_mean': d.cost.mean(), 'cost_std': d.cost.std(),
                     'time_mean': d.time_ms.mean(), 'time_std': d.time_ms.std(),
                     'opt_hits': int((d.cost <= o + OPT_TOL).sum()) if pd.notna(o) else None})
    return pd.DataFrame(rows)


def paired(piv, cases):
    p_ = piv.loc[cases]
    rows, ps = [], []
    for a in BASELINES:
        d = (p_['hybrid'] - p_[a]).dropna()
        rel = 100 * d / p_[a]
        ps.append(1.0 if (d.abs() < 1e-6).all() else wilcoxon(d, zero_method='zsplit').pvalue)
        rows.append({'vs': NAMES[a], 'better': int((d < -1e-6).sum()), 'tie': int((d.abs() <= 1e-6).sum()),
                     'worse': int((d > 1e-6).sum()), 'mean_change_pct': rel.mean(), 'max_saving_pct': rel.min()})
    for r, p in zip(rows, holm(ps)):
        r['p_holm'] = p
    return pd.DataFrame(rows)


def main(results):
    results = Path(results)
    runs = pd.concat([pd.read_csv(results / 'main_runs.csv'), pd.read_csv(results / 'scale_runs.csv')])
    runs = runs[runs.algo.isin(METHODS)]
    opt = pd.read_csv(results / 'optimum.csv').set_index('case_id').optimal_cost.to_dict()
    pc = per_case(runs, opt)
    out = results / 'paper'
    out.mkdir(exist_ok=True)

    # Table III
    t3 = pc[pc.group.isin(MAIN)].groupby(['group', 'algo']).mean(numeric_only=True).reset_index()
    hits = pc[pc.group.isin(MAIN)].groupby(['group', 'algo']).opt_hits.sum(min_count=1).reset_index()
    t3 = t3.drop(columns='opt_hits').merge(hits, on=['group', 'algo'])
    t3.loc[t3.group == 'MA-SD', 'opt_hits'] = None  # no allocation decision, no optimum enumerated
    t3['group'] = pd.Categorical(t3.group, MAIN, ordered=True)
    t3['algo'] = pd.Categorical(t3.algo, METHODS, ordered=True)
    t3 = t3.sort_values(['group', 'algo'])
    t3.to_csv(out / 'table3_main.csv', index=False)

    # Table IV + Friedman + A12
    piv = pc.pivot_table(index='case_id', columns='algo', values='cost_mean')
    allc = list(piv.index)
    t4 = paired(piv, allc)
    t4.to_csv(out / 'table4_hybrid_vs_baselines.csv', index=False)
    fr = friedmanchisquare(*[piv[a] for a in METHODS])
    main_p = paired(piv, [c for c in allc if not c.startswith('SC')]).set_index('vs').p_holm
    scale_p = paired(piv, [c for c in allc if c.startswith('SC')]).set_index('vs').p_holm
    a12s = {}
    for b in ('ga', 'aco'):
        vals, strict = [], []
        for cid, d in runs.groupby('case_id'):
            h, x = d[d.algo == 'hybrid'].cost.tolist(), d[d.algo == b].cost.tolist()
            vals.append(a12(h, x))
            strict.append(sum(a < c for a in h for c in x) / (len(h) * len(x)))
        a12s[NAMES[b]] = {'A12': sum(vals) / len(vals), 'P_strictly_lower': sum(strict) / len(strict)}

    # Table V
    sc = pc[pc.group.str.startswith('SC')].copy()
    sc['n_dest'] = sc.group.str[3:].astype(int)
    ref = sc[sc.algo == 'astar'].set_index('case_id').cost_mean
    sc['vs_astar_pct'] = 100 * (sc.cost_mean - sc.case_id.map(ref)) / sc.case_id.map(ref)
    t5 = sc.groupby(['n_dest', 'algo']).agg(vs_astar_pct=('vs_astar_pct', 'mean'),
                                           time_mean=('time_mean', 'mean')).reset_index()
    t5.to_csv(out / 'table5_scalability.csv', index=False)
    l1 = runs[(runs.algo == 'hybrid') & (runs.n_dest == 30)]

    stats = {'friedman_chi2': fr.statistic, 'friedman_p': fr.pvalue, 'methods': [NAMES[a] for a in METHODS],
             'holm_main_20_vs_astar': main_p['A*'], 'holm_scale_20_vs_astar': scale_p['A*'], 'A12': a12s,
             'level1_share_30dest': l1.level1_ms.mean() / l1.time_ms.mean(), 'runs': int(len(runs))}
    (out / 'stats.json').write_text(json.dumps(stats, indent=2))

    pd.set_option('display.width', 200)
    print(t3.round(3).to_string(index=False))
    print(t4.to_string(index=False))
    print(t5.pivot(index='n_dest', columns='algo').round(1).to_string())
    print(json.dumps(stats, indent=2))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--results', default=str(ROOT / 'results'))
    main(ap.parse_args().results)
