"""Route maps drawn from the frozen dataset and test cases.

  fig_scenarios.png        hybrid A*-GA routes in SA-SD-01, SA-MD-01, MA-SD-01, MA-MD-01
  fig_mamd_comparison.png  a multi-agent case: greedy allocation (Dijkstra/A*) vs. hybrid A*-GA

  python experiments/make_scenario_maps.py [CASE_ID for the comparison, default MA-MD-01]
"""
import json
import math
import os
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
sys.path.insert(0, str(PROJECT / 'backend'))

import matplotlib  # noqa: E402
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

DATASET = PROJECT / 'dataset'
FIGURES = ROOT / 'figures'
RISK_COLORS = {'low': '#86EFAC', 'medium': '#FCD34D', 'high': '#FCA5A5'}
AGENT_COLORS = ['#1D4ED8', '#B45309', '#7C3AED', '#0F766E']
plt.rcParams.update({'font.family': 'serif', 'font.size': 7})


def load_network(name='mamuju_r1500'):
    from graph_service import GraphService
    gs = GraphService()
    gs.load_from_csv(DATASET / 'network' / f'{name}_nodes.csv', DATASET / 'network' / f'{name}_edges.csv')
    return gs


def load_cases():
    return {c['id']: c for c in json.loads((DATASET / 'test_cases' / 'test_cases.json').read_text())}


def load_params():
    p = {}
    fn = DATASET / 'tuned_params.json'
    if fn.exists():
        for v in json.loads(fn.read_text()).values():
            p.update(v)
    return p


def solve(gs, case, algo, params):
    from algorithms import solve_vrp
    starts = [{'node_id': str(d['node_id']), 'agents': d['agents']} for d in case['depots']]
    dests = [{'node_id': str(d['node_id'])} for d in case['destinations']]
    random.seed(1)
    return solve_vrp(gs, starts, dests, algo, params, case['force_distribution'])


def draw(ax, gs, case, result, title):
    pts = [(d['lat'], d['lng']) for d in case['depots'] + case['destinations']]
    for r in result['routes']:
        pts += [tuple(c) for c in r['route_geometry']]
    lat0, lat1 = min(p[0] for p in pts), max(p[0] for p in pts)
    lng0, lng1 = min(p[1] for p in pts), max(p[1] for p in pts)
    pad = 0.0025
    G = gs.graph
    low, med = gs.risk_thresholds['low_max'], gs.risk_thresholds['medium_max']
    for u, v, d in G.edges(data=True):
        cls = 'low' if d['risk'] <= low else 'medium' if d['risk'] <= med else 'high'
        coords = d.get('geom') or [[G.nodes[u]['x'], G.nodes[u]['y']], [G.nodes[v]['x'], G.nodes[v]['y']]]
        ax.plot([c[0] for c in coords], [c[1] for c in coords], color=RISK_COLORS[cls], lw=0.9, zorder=1,
                solid_capstyle='round')
    for i, r in enumerate(result['routes']):
        g = r['route_geometry']
        ax.plot([c[1] for c in g], [c[0] for c in g], color=AGENT_COLORS[i % len(AGENT_COLORS)], lw=2.0,
                alpha=0.9, zorder=3, solid_capstyle='round')
    for d in case['depots']:
        ax.scatter(d['lng'], d['lat'], marker='s', s=42, c='#111827', zorder=5, edgecolors='white', linewidths=0.8)
        ax.annotate(f"{d['label']} ({d['agents']})", (d['lng'], d['lat']), xytext=(4, 4), textcoords='offset points',
                    fontsize=6.5, fontweight='bold', zorder=6)
    for d in case['destinations']:
        ax.scatter(d['lng'], d['lat'], marker='^', s=46, c='#DC2626', zorder=5, edgecolors='white', linewidths=0.8)
        ax.annotate(d['label'], (d['lng'], d['lat']), xytext=(4, -9), textcoords='offset points', fontsize=6.5,
                    color='#991B1B', fontweight='bold', zorder=6)
    ax.set_xlim(lng0 - pad, lng1 + pad)
    ax.set_ylim(lat0 - pad, lat1 + pad)
    ax.set_aspect(1 / math.cos(math.radians((lat0 + lat1) / 2)))
    ax.set_xticks([])
    ax.set_yticks([])
    s = result['summary']
    ax.set_title(f"{title}\ncost {s['total_cost']:,.1f} · distance {s['total_distance']:,.0f} m", fontsize=7.5)


def legend(fig, n_agents):
    handles = [Line2D([], [], color=RISK_COLORS[k], lw=2, label=f'{k} risk road') for k in ('low', 'medium', 'high')]
    handles += [Line2D([], [], color=AGENT_COLORS[i], lw=2.2, label=f'agent {i + 1} route') for i in range(n_agents)]
    handles += [Line2D([], [], marker='s', ls='', color='#111827', label='depot (agents)'),
                Line2D([], [], marker='^', ls='', color='#DC2626', label='destination')]
    fig.legend(handles=handles, ncol=5, frameon=False, loc='lower center', fontsize=6.5)


def main():
    os.chdir(PROJECT / 'backend')
    FIGURES.mkdir(exist_ok=True)
    cases, params, gs = load_cases(), load_params(), load_network()
    fig, axes = plt.subplots(2, 2, figsize=(7.0, 6.6))
    for ax, cid in zip(axes.flat, ['SA-SD-01', 'SA-MD-01', 'MA-SD-01', 'MA-MD-01']):
        draw(ax, gs, cases[cid], solve(gs, cases[cid], 'hybrid', params), f'{cid} (hybrid A*-GA)')
    legend(fig, 4)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(FIGURES / 'fig_scenarios.png', dpi=300)
    plt.close(fig)

    cid = sys.argv[1] if len(sys.argv) > 1 else 'MA-MD-01'
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.7))
    draw(axes[0], gs, cases[cid], solve(gs, cases[cid], 'dijkstra', params), f'{cid}, greedy allocation (Dijkstra / A*)')
    draw(axes[1], gs, cases[cid], solve(gs, cases[cid], 'hybrid', params), f'{cid}, hybrid A*-GA')
    legend(fig, 4)
    fig.tight_layout(rect=(0, 0.1, 1, 0.96))
    fig.savefig(FIGURES / 'fig_mamd_comparison.png', dpi=300)
    plt.close(fig)
    print('saved fig_scenarios.png and fig_mamd_comparison.png in', FIGURES)


if __name__ == '__main__':
    main()
