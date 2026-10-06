"""Single-column (3.4 in) figures for the IEEE conference paper -> experiments/figures/paper/.

  fig1_scenarios.png    hybrid A*-GA routes in test cases SA-SD-01, SA-MD-01, MA-SD-01, MA-MD-01
  fig2_framework.png    two-level hybrid A*-GA framework
  fig3_main_cost.png    mean cost per scenario over its 5 test cases (from results/table_cases.csv)
  fig4_scalability.png  cost vs. Dijkstra and time vs. number of destinations (from results/table_scale.csv)
  fig5_algorithm_maps.png  routes of all six algorithms on one test case of each scenario (double column)

  --lang id             Indonesian labels -> experiments/figures/paper_id/
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent / 'backend'))

import matplotlib  # noqa: E402
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

import make_scenario_maps as maps  # noqa: E402

RESULTS = ROOT / 'results'
OUT = ROOT / 'figures' / 'paper'
W = 3.4
ALGOS = ['dijkstra', 'astar', 'bfs', 'ga', 'aco', 'hybrid']
NAMES = {'dijkstra': 'Dijkstra', 'astar': 'A*', 'bfs': 'BFS', 'ga': 'GA', 'aco': 'ACO', 'hybrid': 'Hybrid A*-GA'}
COLORS = {'dijkstra': '#3B82F6', 'astar': '#8B5CF6', 'bfs': '#F97316', 'ga': '#22C55E', 'aco': '#EF4444',
          'hybrid': '#B45309'}
GROUPS = ['SA-SD', 'SA-MD', 'MA-SD', 'MA-MD']
LANG = 'id' if '--lang' in sys.argv and sys.argv[sys.argv.index('--lang') + 1] == 'id' else 'en'
if LANG == 'id':
    OUT = ROOT / 'figures' / 'paper_id'
ID = {
    'Input': 'Masukan',
    'OSM road network (d, r); depots with K agents; destinations D': 'jaringan jalan OSM (d, r); depot dengan K agen; tujuan D',
    'Level 1 — A* on the risk-aware cost (exact)': 'Level 1 — A* pada biaya sadar risiko (eksak)',
    'Cost = d (1 + r), haversine heuristic (admissible)': 'Cost = d (1 + r), heuristik haversine (admissible)',
    'least-cost paths between all depots and destinations': 'jalur biaya terkecil antarsemua depot dan tujuan',
    'cost matrix M + stored paths': 'matriks biaya M + jalur tersimpan',
    'Level 2 — Allocation GA (NP-hard part)': 'Level 2 — GA alokasi (bagian NP-hard)',
    'chromosome = destinations + (K − 1) agent separators': 'kromosom = tujuan + (K − 1) pemisah agen',
    'fitness = total cost from M (+ penalty for idle agents)': 'fitness = total biaya dari M (+ penalti agen menganggur)',
    'greedy warm start · tournament · elitism · OX1 crossover': 'warm start greedy · turnamen · elitisme · crossover OX1',
    'multi-domain inversion mutation · early stopping': 'mutasi inversi multi-domain · penghentian dini',
    'best allocation and visiting order': 'alokasi dan urutan kunjungan terbaik',
    'Output': 'Keluaran',
    'one road route per agent; distance, cost, risk exposure': 'satu rute jalan per agen; jarak, biaya, paparan risiko',
    'cost': 'biaya', 'low risk': 'risiko rendah', 'medium risk': 'risiko sedang', 'high risk': 'risiko tinggi',
    'agent routes': 'rute agen', 'agent': 'agen', 'depot (agents)': 'depot (agen)', 'destination': 'tujuan',
    'Cost vs. Dijkstra (%)\nmean of 5 cases, bars = range': 'Biaya vs. Dijkstra (%)\nrerata 5 kasus, garis = rentang',
    'BFS ranges clipped (up to +166 %)': 'rentang BFS dipotong (hingga +166 %)',
    'Cost vs. Dijkstra (%)': 'Biaya vs. Dijkstra (%)', 'Mean time (ms)': 'Waktu rerata (ms)',
    'Number of destinations (4 agents, 5 cases each)': 'Jumlah tujuan (4 agen, masing-masing 5 kasus)',
    'Hybrid A*-GA': 'Hibrida A*-GA',
}


def T(s):
    return ID.get(s, s) if LANG == 'id' else s


# --merge-exact: Dijkstra and A* return identical routes and costs, so they are drawn as one series
MERGE = '--merge-exact' in sys.argv
PLOT = [a for a in ALGOS if not (MERGE and a == 'astar')]
if MERGE:
    OUT = OUT.parent / (OUT.name + '_merged')
    NAMES = dict(NAMES, dijkstra='Dijkstra / A*')
# --astar-only: Dijkstra returns the same routes as A*, so only A* is drawn (reference = A*)
ASTAR_ONLY = '--astar-only' in sys.argv
if ASTAR_ONLY:
    PLOT = [a for a in ALGOS if a != 'dijkstra']
    OUT = OUT.parent / (OUT.name + '_astar')
    COLORS = dict(COLORS, astar=COLORS['dijkstra'])
REF = 'A*' if ASTAR_ONLY else ('Dijkstra/A*' if MERGE else 'Dijkstra')


plt.rcParams.update({'font.family': 'serif', 'font.size': 7, 'axes.titlesize': 7, 'legend.fontsize': 6.5,
                     'axes.labelsize': 7, 'xtick.labelsize': 6.5, 'ytick.labelsize': 6.5})


def framework():
    fig, ax = plt.subplots(figsize=(W, 2.6))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')
    edge, accent, tint = '#374151', '#B45309', '#FEF3C7'

    def box(y, h, title, lines, hi=False):
        ax.add_patch(FancyBboxPatch((2, y), 96, h, boxstyle='round,pad=0.3,rounding_size=1.5',
                                    fc=tint if hi else 'white', ec=accent if hi else edge, lw=1.1 if hi else 0.7))
        ax.text(50, y + h - 2.6, title, ha='center', va='top', fontweight='bold', fontsize=7)
        for i, ln in enumerate(lines):
            ax.text(50, y + h - 8.6 - 5.2 * i, ln, ha='center', va='top', fontsize=6.3)

    def arrow(y1, y2, label):
        ax.add_patch(FancyArrowPatch((50, y1), (50, y2), arrowstyle='-|>', mutation_scale=6, lw=0.7, color=edge))
        if label:
            ax.text(52, (y1 + y2) / 2, label, ha='left', va='center', fontsize=5.8, style='italic', color='#4B5563')

    box(86, 13, T('Input'), [T('OSM road network (d, r); depots with K agents; destinations D')])
    arrow(86, 81, '')
    box(61, 19.5, T('Level 1 — A* on the risk-aware cost (exact)'),
        [T('Cost = d (1 + r), haversine heuristic (admissible)'),
         T('least-cost paths between all depots and destinations')], hi=True)
    arrow(61, 55, T('cost matrix M + stored paths'))
    box(21, 33.5, T('Level 2 — Allocation GA (NP-hard part)'),
        [T('chromosome = destinations + (K − 1) agent separators'),
         T('fitness = total cost from M (+ penalty for idle agents)'),
         T('greedy warm start · tournament · elitism · OX1 crossover'),
         T('multi-domain inversion mutation · early stopping')], hi=True)
    arrow(21, 15, T('best allocation and visiting order'))
    box(1.5, 12.5, T('Output'), [T('one road route per agent; distance, cost, risk exposure')])
    fig.tight_layout(pad=0.05)
    fig.savefig(OUT / 'fig2_framework.png', dpi=300)
    plt.close(fig)


def scenarios():
    os.chdir(ROOT.parent / 'backend')
    cases, params, gs = maps.load_cases(), maps.load_params(), maps.load_network()
    fig, axes = plt.subplots(2, 2, figsize=(W, 3.9))
    lims = []
    for ax, cid in zip(axes.flat, [f'{g}-01' for g in GROUPS]):
        res = maps.solve(gs, cases[cid], 'hybrid', params)
        maps.draw(ax, gs, cases[cid], res, cid)
        tc = f"{res['summary']['total_cost']:,.0f}"
        ax.set_title(f"{cid}: {T('cost')} {tc.replace(',', '.') if LANG == 'id' else tc}", fontsize=6.8)
        lims.append((ax.get_xlim(), ax.get_ylim()))
        for t in ax.texts:
            t.set_fontsize(5.5)
        for ln in ax.lines:
            ln.set_linewidth(ln.get_linewidth() * (0.55 if ln.get_zorder() == 1 else 0.6))
        for c in ax.collections:
            c.set_sizes([16])
    x0, x1 = min(l[0][0] for l in lims), max(l[0][1] for l in lims)
    y0, y1 = min(l[1][0] for l in lims), max(l[1][1] for l in lims)
    for ax in axes.flat:
        ax.set_xlim(x0, x1)
        ax.set_ylim(y0, y1)
    handles = [Line2D([], [], color=maps.RISK_COLORS[k], lw=1.5, label=T(f'{k} risk')) for k in ('low', 'medium', 'high')]
    handles += [Line2D([], [], color=maps.AGENT_COLORS[0], lw=1.6, label=T('agent routes')),
                Line2D([], [], marker='s', ls='', ms=3.5, color='#111827', label=T('depot (agents)')),
                Line2D([], [], marker='^', ls='', ms=3.8, color='#DC2626', label=T('destination'))]
    fig.legend(handles=handles, ncol=3, frameon=False, loc='lower center', fontsize=5.8, handlelength=1.6)
    fig.tight_layout(rect=(0, 0.07, 1, 1), pad=0.2, h_pad=0.8, w_pad=0.4)
    fig.savefig(OUT / 'fig1_scenarios.png', dpi=300)
    plt.close(fig)


MAP_RATIO = 1.3   # width / height of every map panel
MAP_CASES =['SA-SD-01', 'SA-MD-05', 'MA-SD-01', 'MA-MD-01']


def algorithm_maps():
    """Double-column grid: rows = scenarios (one test case each), columns = the six algorithms."""
    os.chdir(ROOT.parent / 'backend')
    cases, params, gs = maps.load_cases(), maps.load_params(), maps.load_network()
    fig, axes = plt.subplots(len(MAP_CASES), len(PLOT), figsize=(7.16, 4.2 if len(PLOT) == 6 else 4.75))
    for r, cid in enumerate(MAP_CASES):
        lims = []
        for c, a in enumerate(PLOT):
            ax = axes[r, c]
            res = maps.solve(gs, cases[cid], a, params)   # seed 1 for the stochastic algorithms
            maps.draw(ax, gs, cases[cid], res, cid)
            ax.set_title('')
            for t in list(ax.texts):
                t.remove()
            for ln in ax.lines:
                ln.set_linewidth(ln.get_linewidth() * (0.45 if ln.get_zorder() == 1 else 0.6))
            for col in ax.collections:
                col.set_sizes([9])
            for s in ax.spines.values():
                s.set_linewidth(0.4)
                s.set_color('#9CA3AF')
            cost = f"{res['summary']['total_cost']:,.0f}"
            cost = cost.replace(',', '.') if LANG == 'id' else cost
            ax.text(0.03, 0.03, f"{T('cost')} {cost}", transform=ax.transAxes, fontsize=5.6, va='bottom',
                    bbox=dict(boxstyle='round,pad=0.15', fc='white', ec='none', alpha=0.85), zorder=10,
                    fontweight='bold' if a == 'hybrid' else 'normal')
            if r == 0:
                ax.set_title(T(NAMES[a]), fontsize=7, fontweight='bold' if a == 'hybrid' else 'normal', pad=3)
            if c == 0:
                ax.set_ylabel(cid, fontsize=6.8)
            lims.append((ax.get_xlim(), ax.get_ylim()))
        x0, x1 = min(l[0][0] for l in lims), max(l[0][1] for l in lims)
        y0, y1 = min(l[1][0] for l in lims), max(l[1][1] for l in lims)
        # same panel shape in every row: pad the shorter side to a fixed width/height ratio (true distance)
        import math
        k = math.cos(math.radians((y0 + y1) / 2))
        w, h = (x1 - x0) * k, (y1 - y0)
        if w / h < MAP_RATIO:
            pad = (MAP_RATIO * h / k - (x1 - x0)) / 2
            x0, x1 = x0 - pad, x1 + pad
        else:
            pad = (w / MAP_RATIO - h) / 2
            y0, y1 = y0 - pad, y1 + pad
        for ax in axes[r]:
            ax.set_xlim(x0, x1)
            ax.set_ylim(y0, y1)
    handles = [Line2D([], [], color=maps.RISK_COLORS[k], lw=1.5, label=T(f'{k} risk')) for k in ('low', 'medium', 'high')]
    handles += [Line2D([], [], color=maps.AGENT_COLORS[i], lw=1.6, label=f"{T('agent')} {i + 1}") for i in range(4)]
    handles += [Line2D([], [], marker='s', ls='', ms=3.5, color='#111827', label=T('depot (agents)')),
                Line2D([], [], marker='^', ls='', ms=3.8, color='#DC2626', label=T('destination'))]
    fig.legend(handles=handles, ncol=9, frameon=False, loc='lower center', fontsize=5.8, handlelength=1.4,
               columnspacing=0.9)
    fig.tight_layout(rect=(0, 0.035, 1, 1), pad=0.2, h_pad=0.3, w_pad=0.2)
    fig.savefig(OUT / 'fig5_algorithm_maps.png', dpi=300, bbox_inches='tight', pad_inches=0.02)
    plt.close(fig)


def main_cost():
    t = pd.read_csv(RESULTS / 'table_cases.csv')
    fig, ax = plt.subplots(figsize=(W, 2.3))
    w = 0.13
    for i, a in enumerate(PLOT):
        means, lo, hi = [], [], []
        for g in GROUPS:
            d = t[(t.group == g) & (t.algo == a)].vs_dijkstra_pct   # per case, so cases are comparable
            means.append(d.mean())
            lo.append(d.mean() - d.min())
            hi.append(d.max() - d.mean())
        ax.bar([x + (i - (len(PLOT) - 1) / 2) * w for x in range(4)], means, w, yerr=[lo, hi], capsize=1.2, color=COLORS[a],
               label=T(NAMES[a]), error_kw={'lw': 0.5})
    ax.axhline(0, color='grey', lw=0.5)
    ax.set_xticks(range(4))
    ax.set_xticklabels(GROUPS)
    ax.set_ylabel(T('Cost vs. Dijkstra (%)\nmean of 5 cases, bars = range').replace('Dijkstra', REF))
    h, lab = ax.get_legend_handles_labels()
    fig.legend(h, lab, ncol=6, frameon=False, loc='upper center', fontsize=5.6, handlelength=1.2, columnspacing=0.8)
    ax.set_ylim(-26, 48)   # BFS whiskers reach +166 % and are clipped; full values are in the tables
    ax.text(-0.45, -24.5, T('BFS ranges clipped (up to +166 %)'), ha='left', va='bottom', fontsize=5.5, color='#6B7280')
    fig.tight_layout(rect=(0, 0, 1, 0.93), pad=0.2)
    fig.savefig(OUT / 'fig3_main_cost.png', dpi=300)
    plt.close(fig)


def scalability():
    s = pd.read_csv(RESULTS / 'table_scale.csv')
    fig, axes = plt.subplots(2, 1, figsize=(W, 3.4), sharex=True)
    for a in PLOT:
        d = s[s.algo == a]
        axes[0].plot(d.n_dest, d.vs_dijkstra_pct, marker='o', ms=2.5, lw=0.9, color=COLORS[a], label=T(NAMES[a]))
        axes[1].plot(d.n_dest, d.time_mean_ms, marker='o', ms=2.5, lw=0.9, color=COLORS[a])
    if MERGE:   # times differ slightly: A* dashed in the time panel
        d = s[s.algo == 'astar']
        axes[1].plot(d.n_dest, d.time_mean_ms, marker='s', ms=2.2, lw=0.8, ls='--', mfc='white',
                     color=COLORS['dijkstra'])
    axes[0].axhline(0, color='grey', lw=0.5)
    axes[0].set_ylabel(T('Cost vs. Dijkstra (%)').replace('Dijkstra', REF))
    axes[1].set_yscale('log')
    axes[1].set_ylabel(T('Mean time (ms)'))
    axes[1].set_xlabel(T('Number of destinations (4 agents, 5 cases each)'))
    axes[1].set_xticks([5, 10, 20, 30])
    h, lab = axes[0].get_legend_handles_labels()
    fig.legend(h, lab, ncol=6, frameon=False, loc='upper center', fontsize=5.6, handlelength=1.4, columnspacing=0.8)
    fig.tight_layout(rect=(0, 0, 1, 0.95), pad=0.2, h_pad=0.4)
    fig.savefig(OUT / 'fig4_scalability.png', dpi=300)
    plt.close(fig)


if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    framework()
    main_cost()
    scalability()
    scenarios()
    algorithm_maps()
    print('saved paper figures in', OUT)
