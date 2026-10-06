"""Build the test cases of the conference study on ONE road network and document every case.

Dataset  : OpenStreetMap drive network of Mamuju (radius 1,500 m, 455 nodes, 516 edges), risk seed 42
           -> dataset/network/mamuju_r1500_{nodes,edges}.csv (frozen)
Test cases: different start (depot) and destination points on that network
           main        SA-SD, SA-MD, MA-SD, MA-MD   x 5 point sets  = 20 cases
           scalability SC-05, SC-10, SC-20, SC-30   x 5 point sets  = 20 cases
           tuning      TUNE-A .. TUNE-D (used only to tune GA, ACO and the hybrid)

Outputs (dataset/test_cases/):
  test_cases.json         every case: depots (agents), destinations, node ids, coordinates, seeds
  test_cases_points.csv   one row per point (case_id, role, label, node_id, lat, lng, agents)
  test_cases_summary.csv  one row per case
  test_cases.geojson      all points for GIS
  app_sessions/<ID>.json  ready-to-import sessions for the web app
  maps/<ID>.png           map of the points of every case

  python experiments/build_dataset.py
"""
import csv
import hashlib
import json
import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
DATASET = PROJECT / 'dataset'
OUT = DATASET / 'test_cases'
sys.path.insert(0, str(PROJECT / 'backend'))

NETWORK = 'mamuju_r1500'
CENTER = (-2.692, 118.898)
RISK_SEED = 42
MIN_SEP_M = 150.0

# group: (depots, agents per depot, destinations, force distribution, purpose)
GROUPS = {
    'SA-SD': (1, 1, 1, False, 'main'),
    'SA-MD': (1, 1, 4, False, 'main'),
    'MA-SD': (2, 2, 1, True, 'main'),
    'MA-MD': (2, 2, 4, True, 'main'),
    'SC-05': (2, 2, 5, True, 'scalability'),
    'SC-10': (2, 2, 10, True, 'scalability'),
    'SC-20': (2, 2, 20, True, 'scalability'),
    'SC-30': (2, 2, 30, True, 'scalability'),
}
CASES_PER_GROUP = 5
MAIN_SEEDS = [2026, 2027, 2028, 2029, 2030]          # case 01 = the instance of the first paper version
TUNING = {'TUNE-A': (1, 1, 4, False, 9001), 'TUNE-B': (2, 2, 4, True, 9002),
          'TUNE-C': (2, 2, 20, True, 9003), 'TUNE-D': (2, 2, 30, True, 9004)}


def load_network():
    from graph_service import GraphService
    gs = GraphService()
    gs.load_from_csv(DATASET / 'network' / f'{NETWORK}_nodes.csv', DATASET / 'network' / f'{NETWORK}_edges.csv',
                     *CENTER)
    return gs


def pick_points(gs, n_points, seed):
    """Seeded choice of network nodes at least MIN_SEP_M apart (spacing relaxed only if impossible)."""
    from graph_service import haversine
    rng = random.Random(seed)
    nodes = sorted(gs.graph.nodes())
    chosen, sep, tries = [], MIN_SEP_M, 0
    while len(chosen) < n_points:
        c = rng.choice(nodes)
        tries += 1
        if tries % 2000 == 0:
            sep *= 0.7
        if c not in chosen and all(haversine(gs.nodes_data[str(c)]['lat'], gs.nodes_data[str(c)]['lng'],
                                             gs.nodes_data[str(x)]['lat'], gs.nodes_data[str(x)]['lng']) >= sep
                                   for x in chosen):
            chosen.append(c)
    return chosen, sep


def make_case(gs, case_id, group, depots, apd, n_dest, force, seed, purpose):
    nodes, sep = pick_points(gs, depots + n_dest, seed)
    nd = gs.nodes_data
    return {
        'id': case_id, 'group': group, 'purpose': purpose, 'network': NETWORK, 'point_seed': seed,
        'min_spacing_m': round(sep, 1), 'force_distribution': force,
        'n_depots': depots, 'agents_per_depot': apd, 'n_agents': depots * apd, 'n_destinations': n_dest,
        'depots': [{'label': f'S{i + 1}', 'node_id': int(n), 'agents': apd, 'lat': nd[str(n)]['lat'],
                    'lng': nd[str(n)]['lng']} for i, n in enumerate(nodes[:depots])],
        'destinations': [{'label': f'E{i + 1}', 'node_id': int(n), 'lat': nd[str(n)]['lat'],
                          'lng': nd[str(n)]['lng']} for i, n in enumerate(nodes[depots:])],
    }


def build_cases(gs):
    cases = []
    for group, (dep, apd, nd, force, purpose) in GROUPS.items():
        for k in range(CASES_PER_GROUP):
            seed = MAIN_SEEDS[k] if purpose == 'main' else 3000 + 100 * nd + k
            cases.append(make_case(gs, f'{group}-{k + 1:02d}', group, dep, apd, nd, force, seed, purpose))
    for cid, (dep, apd, nd, force, seed) in TUNING.items():
        cases.append(make_case(gs, cid, 'TUNE', dep, apd, nd, force, seed, 'tuning'))
    return cases


def draw_map(gs, case, path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    risk_colors = {'low': '#86EFAC', 'medium': '#FCD34D', 'high': '#FCA5A5'}
    G = gs.graph
    fig, ax = plt.subplots(figsize=(4.2, 4.0))
    for u, v, d in G.edges(data=True):
        cls = 'low' if d['risk'] <= 0.33 else 'medium' if d['risk'] <= 0.66 else 'high'
        coords = d.get('geom') or [[G.nodes[u]['x'], G.nodes[u]['y']], [G.nodes[v]['x'], G.nodes[v]['y']]]
        ax.plot([c[0] for c in coords], [c[1] for c in coords], color=risk_colors[cls], lw=0.7, zorder=1)
    for p in case['depots']:
        ax.scatter(p['lng'], p['lat'], marker='s', s=40, c='#1E3A8A', zorder=3, edgecolors='white', linewidths=0.7)
        ax.annotate(f"{p['label']} ({p['agents']})", (p['lng'], p['lat']), xytext=(4, 3), textcoords='offset points',
                    fontsize=7, fontweight='bold', color='#1E3A8A')
    for p in case['destinations']:
        ax.scatter(p['lng'], p['lat'], marker='^', s=36, c='#DC2626', zorder=3, edgecolors='white', linewidths=0.7)
        ax.annotate(p['label'], (p['lng'], p['lat']), xytext=(3, -8), textcoords='offset points', fontsize=6.5,
                    color='#991B1B')
    lat0 = sum(d['y'] for _, d in G.nodes(data=True)) / G.number_of_nodes()
    ax.set_aspect(1 / math.cos(math.radians(lat0)))
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(f"{case['id']}: {case['n_agents']} agent(s), {case['n_destinations']} destination(s)", fontsize=8)
    fig.tight_layout(pad=0.3)
    fig.savefig(path, dpi=200)
    plt.close(fig)


def main():
    gs = load_network()
    cases = build_cases(gs)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'app_sessions').mkdir(exist_ok=True)
    (OUT / 'maps').mkdir(exist_ok=True)
    (OUT / 'test_cases.json').write_text(json.dumps(cases, indent=2), encoding='utf-8')

    with open(OUT / 'test_cases_points.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['case_id', 'group', 'role', 'label', 'node_id', 'lat', 'lng', 'agents'])
        for c in cases:
            for p in c['depots']:
                w.writerow([c['id'], c['group'], 'depot', p['label'], p['node_id'], p['lat'], p['lng'], p['agents']])
            for p in c['destinations']:
                w.writerow([c['id'], c['group'], 'destination', p['label'], p['node_id'], p['lat'], p['lng'], ''])
    with open(OUT / 'test_cases_summary.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['case_id', 'group', 'purpose', 'n_depots', 'agents_per_depot', 'n_agents', 'n_destinations',
                    'force_distribution', 'point_seed', 'min_spacing_m'])
        for c in cases:
            w.writerow([c['id'], c['group'], c['purpose'], c['n_depots'], c['agents_per_depot'], c['n_agents'],
                        c['n_destinations'], c['force_distribution'], c['point_seed'], c['min_spacing_m']])
    feats = []
    for c in cases:
        for role, pts in (('depot', c['depots']), ('destination', c['destinations'])):
            for p in pts:
                feats.append({'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [p['lng'], p['lat']]},
                              'properties': {'case_id': c['id'], 'role': role, 'label': p['label'],
                                             'node_id': p['node_id'], 'agents': p.get('agents')}})
    (OUT / 'test_cases.geojson').write_text(json.dumps({'type': 'FeatureCollection', 'features': feats}),
                                            encoding='utf-8')
    for c in cases:
        session = {'case_id': c['id'], 'network': NETWORK,
                   'note': f'Initialize the network at {CENTER[0]}, {CENTER[1]} with radius 1500 m first, then Import.',
                   'startNodes': [{'id': str(p['node_id']), 'lat': p['lat'], 'lng': p['lng'], 'agents': p['agents'],
                                   'label': p['label']} for p in c['depots']],
                   'endNodes': [{'id': str(p['node_id']), 'lat': p['lat'], 'lng': p['lng'], 'label': p['label']}
                                for p in c['destinations']],
                   'forceDistribution': c['force_distribution'],
                   'riskThresholds': {'low_max': 0.33, 'medium_max': 0.66}}
        (OUT / 'app_sessions' / f"{c['id']}.json").write_text(json.dumps(session, indent=2), encoding='utf-8')
        draw_map(gs, c, OUT / 'maps' / f"{c['id']}.png")

    meta = {'network': NETWORK, 'center': CENTER, 'radius_m': 1500, 'nodes': gs.graph.number_of_nodes(),
            'edges': gs.graph.number_of_edges(), 'risk_seed': RISK_SEED, 'min_spacing_m': MIN_SEP_M,
            'groups': {g: {'depots': v[0], 'agents_per_depot': v[1], 'destinations': v[2],
                           'force_distribution': v[3], 'purpose': v[4], 'cases': CASES_PER_GROUP}
                       for g, v in GROUPS.items()},
            'tuning_cases': list(TUNING),
            'note': 'Simulation dataset: road geometry from OpenStreetMap; depots, destinations, agents and risk '
                    'values are simulated.'}
    (DATASET / 'metadata.json').write_text(json.dumps(meta, indent=2), encoding='utf-8')
    print(f'{len(cases)} test cases written to {OUT}')


def checksums():
    sums = {}
    for p in sorted(DATASET.rglob('*')):
        if p.is_file() and p.name not in ('SHA256SUMS', 'README.md'):
            sums[str(p.relative_to(DATASET)).replace('\\', '/')] = hashlib.sha256(p.read_bytes()).hexdigest()
    (DATASET / 'SHA256SUMS').write_text(''.join(f'{h}  {f}\n' for f, h in sums.items()), encoding='utf-8',
                                        newline='\n')


if __name__ == '__main__':
    if '--checksums' in sys.argv:
        checksums()
    else:
        main()
        checksums()
