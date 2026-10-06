import networkx as nx
import numpy as np
import random
import math
import logging
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)


def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class GraphService:
    def __init__(self):
        self.graph: Optional[nx.Graph] = None
        self.nodes_data: Dict = {}
        self.edges_data: Dict = {}
        self.geojson_edges: Optional[Dict] = None
        self.geojson_nodes: Optional[Dict] = None
        self.nodes_list: List[Dict] = []
        self.is_initialized: bool = False
        self.center_lat: float = -6.175
        self.center_lng: float = 106.827
        self.removed_edges: List[Dict] = []
        self.risk_thresholds = {"low_max": 0.33, "medium_max": 0.66}
        self.seed: Optional[int] = None
        self.rng = random.Random()

    def initialize(self, lat=-6.175, lng=106.827, radius=1500, seed=None, prefer_cache=False):
        self.center_lat = lat
        self.center_lng = lng
        self.removed_edges = []
        # Seeded RNG so the risk field (and therefore every experiment) is reproducible
        self.seed = seed
        self.rng = random.Random(seed)
        # The paper's network is shipped in dataset/network, so the default request works offline
        dataset = self._matching_dataset(lat, lng, radius, seed) if prefer_cache else None
        if dataset is not None:
            logger.info(f"Loading frozen dataset network {dataset[0].name}")
            return self.load_from_csv(dataset[0], dataset[1], lat, lng)
        sources = [True, False] if prefer_cache else [False, True]
        for from_cache in sources:
            try:
                return self._fetch_osm_data(lat, lng, radius, from_cache=from_cache)
            except Exception as e:
                logger.warning(f"OSM load failed (from_cache={from_cache}): {e}")
            self.rng = random.Random(seed)
        logger.warning("No OSM data available. Using synthetic graph.")
        return self._generate_synthetic_graph(lat, lng, radius)

    @staticmethod
    def _matching_dataset(lat, lng, radius, seed):
        """(nodes_csv, edges_csv) of the frozen dataset network if the request matches it, else None."""
        import json
        from pathlib import Path
        net_dir = Path(__file__).resolve().parent.parent / 'dataset' / 'network'
        try:
            meta = json.loads((net_dir.parent / 'metadata.json').read_text(encoding='utf-8'))
        except Exception:
            return None
        nodes, edges = net_dir / f"{meta['network']}_nodes.csv", net_dir / f"{meta['network']}_edges.csv"
        same = (abs(lat - meta['center'][0]) < 1e-6 and abs(lng - meta['center'][1]) < 1e-6
                and int(radius) == int(meta['radius_m']) and seed == meta['risk_seed'])
        return (nodes, edges) if same and nodes.exists() and edges.exists() else None

    def load_from_csv(self, nodes_csv, edges_csv, lat=None, lng=None):
        """Load a frozen network exported by experiments/export_dataset.py.
        Node and edge order are preserved so results are bit-for-bit reproducible."""
        import csv
        import json
        G = nx.Graph()
        order = {}
        with open(nodes_csv, newline='', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                G.add_node(int(row['node_id']), y=float(row['lat']), x=float(row['lng']))
                if row.get('neighbor_order'):
                    order[int(row['node_id'])] = json.loads(row['neighbor_order'])
        with open(edges_csv, newline='', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                geom = json.loads(row['geometry']) if row.get('geometry') else None
                G.add_edge(int(row['u']), int(row['v']), distance=float(row['distance_m']),
                           risk=float(row['risk']), cost=float(row['cost']), geom=geom)
        # Restore the original adjacency order (GA/ACO draw random moves over it)
        for n, nbs in order.items():
            G._adj[n] = {nb: G._adj[n][nb] for nb in nbs}
        self.graph = G
        self.removed_edges = []
        if lat is not None:
            self.center_lat, self.center_lng = lat, lng
        self._process_graph()
        return {"nodes_count": len(self.nodes_data), "edges_count": len(self.edges_data),
                "center": {"lat": self.center_lat, "lng": self.center_lng}, "source": "dataset"}

    @staticmethod
    def find_cached_overpass(lat, lng, radius, cache_dir='cache'):
        """Largest cached Overpass response whose nodes cover the requested bounding box.
        Returns (filename, response_json, bbox) or raises ValueError."""
        import glob
        import json
        import osmnx as ox
        west, south, east, north = ox.utils_geo.bbox_from_point((lat, lng), dist=radius)
        best = None
        for fn in glob.glob(f'{cache_dir}/*.json'):
            try:
                with open(fn, encoding='utf-8') as f:
                    data = json.load(f)
            except Exception:
                continue
            pts = [(e['lat'], e['lon']) for e in data.get('elements', []) if e.get('type') == 'node' and 'lat' in e]
            if not pts or not any(e.get('type') == 'way' for e in data['elements']):
                continue
            ys = [p[0] for p in pts]
            xs = [p[1] for p in pts]
            if min(ys) <= south and max(ys) >= north and min(xs) <= west and max(xs) >= east:
                if best is None or len(pts) > best[0]:
                    best = (len(pts), fn, data)
        if best is None:
            raise ValueError("no cached response covers the requested area")
        return best[1], best[2], (west, south, east, north)

    @classmethod
    def _graph_from_cached_overpass(cls, lat, lng, radius, cache_dir='cache'):
        """Rebuild a drive network from a cached Overpass response that covers the
        requested bounding box (same truncate/simplify steps as graph_from_point)."""
        import osmnx as ox
        from osmnx import graph as ox_graph
        fn, data, (west, south, east, north) = cls.find_cached_overpass(lat, lng, radius, cache_dir)
        logger.info(f"Using cached Overpass response {fn}")
        G = ox_graph._create_graph([data], bidirectional=False)
        G = ox.truncate.truncate_graph_bbox(G, (west, south, east, north))
        G = ox.simplify_graph(G)
        return ox.truncate.largest_component(G, strongly=False)

    def _fetch_osm_data(self, lat, lng, radius, from_cache=False):
        import osmnx as ox
        logger.info(f"Fetching OSM data for ({lat}, {lng}), radius={radius}m")
        if from_cache:
            G = self._graph_from_cached_overpass(lat, lng, radius)
        else:
            G = ox.graph_from_point((lat, lng), dist=radius, network_type='drive')
        G_simple = nx.Graph()
        for node, data in G.nodes(data=True):
            G_simple.add_node(node, y=data['y'], x=data['x'])
        # Fixed edge order so a given seed always yields the same risk per edge
        for u, v, key, data in sorted(G.edges(keys=True, data=True), key=lambda e: (e[0], e[1], e[2])):
            if not G_simple.has_edge(u, v):
                distance = data.get('length', 100.0)
                risk = round(self.rng.uniform(0, 1), 2)
                cost = round(distance * (1 + risk), 2)
                geom = None
                if 'geometry' in data:
                    try:
                        geom = [[c[0], c[1]] for c in data['geometry'].coords]
                    except Exception:
                        geom = None
                G_simple.add_edge(u, v, distance=round(distance, 2), risk=risk, cost=cost, geom=geom)
        if not nx.is_connected(G_simple):
            largest_cc = max(nx.connected_components(G_simple), key=len)
            G_simple = G_simple.subgraph(largest_cc).copy()
        self.graph = G_simple
        self._process_graph()
        logger.info(f"Graph loaded: {len(self.nodes_data)} nodes, {len(self.edges_data)} edges")
        return {"nodes_count": len(self.nodes_data), "edges_count": len(self.edges_data),
                "center": {"lat": lat, "lng": lng}, "radius": radius, "source": "osm"}

    def _generate_synthetic_graph(self, lat, lng, radius):
        logger.info("Generating synthetic graph")
        grid_size = 15
        spacing = (radius * 2) / (grid_size - 1)
        deg_lat = 1.0 / 111320.0
        deg_lng = 1.0 / (111320.0 * math.cos(math.radians(lat)))
        G = nx.Graph()
        node_id = 0
        grid = {}
        for i in range(grid_size):
            for j in range(grid_size):
                n_lat = lat + (i - grid_size // 2) * spacing * deg_lat + self.rng.uniform(-0.3, 0.3) * spacing * deg_lat
                n_lng = lng + (j - grid_size // 2) * spacing * deg_lng + self.rng.uniform(-0.3, 0.3) * spacing * deg_lng
                G.add_node(node_id, y=n_lat, x=n_lng)
                grid[(i, j)] = node_id
                node_id += 1
        for i in range(grid_size):
            for j in range(grid_size):
                neighbors = []
                if i + 1 < grid_size: neighbors.append((i + 1, j))
                if j + 1 < grid_size: neighbors.append((i, j + 1))
                if i + 1 < grid_size and j + 1 < grid_size and self.rng.random() < 0.3: neighbors.append((i + 1, j + 1))
                for ni, nj in neighbors:
                    u, v = grid[(i, j)], grid[(ni, nj)]
                    dist = haversine(G.nodes[u]['y'], G.nodes[u]['x'], G.nodes[v]['y'], G.nodes[v]['x'])
                    risk = round(self.rng.uniform(0, 1), 2)
                    G.add_edge(u, v, distance=round(dist, 2), risk=risk, cost=round(dist * (1 + risk), 2), geom=None)
        if not nx.is_connected(G):
            largest_cc = max(nx.connected_components(G), key=len)
            G = G.subgraph(largest_cc).copy()
        self.graph = G
        self._process_graph()
        return {"nodes_count": len(self.nodes_data), "edges_count": len(self.edges_data),
                "center": {"lat": lat, "lng": lng}, "radius": radius, "source": "synthetic"}

    def _process_graph(self):
        self.nodes_data = {}
        self.edges_data = {}
        self.nodes_list = []
        for node, data in self.graph.nodes(data=True):
            info = {"id": str(node), "lat": data['y'], "lng": data['x']}
            self.nodes_data[str(node)] = info
            self.nodes_list.append(info)
        for u, v, data in self.graph.edges(data=True):
            self.edges_data[f"{u}-{v}"] = {"source": str(u), "target": str(v),
                "distance": data.get('distance', 100), "risk": data.get('risk', 0.5), "cost": data.get('cost', 150)}
        self._generate_geojson()
        self.is_initialized = True

    def _generate_geojson(self):
        edge_features = []
        for u, v, data in self.graph.edges(data=True):
            geom = data.get('geom')
            coords = geom if geom else [[self.graph.nodes[u]['x'], self.graph.nodes[u]['y']],
                                         [self.graph.nodes[v]['x'], self.graph.nodes[v]['y']]]
            edge_features.append({"type": "Feature",
                "geometry": {"type": "LineString", "coordinates": coords},
                "properties": {"source": str(u), "target": str(v),
                    "distance": data.get('distance', 100), "risk": data.get('risk', 0.5), "cost": data.get('cost', 150)}})
        self.geojson_edges = {"type": "FeatureCollection", "features": edge_features}
        node_features = [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [d['x'], d['y']]},
                          "properties": {"id": str(n)}} for n, d in self.graph.nodes(data=True)]
        self.geojson_nodes = {"type": "FeatureCollection", "features": node_features}

    def get_nearest_node(self, lat, lng):
        min_dist, nearest = float('inf'), None
        for nid, nd in self.nodes_data.items():
            d = haversine(lat, lng, nd['lat'], nd['lng'])
            if d < min_dist:
                min_dist = d
                nearest = {**nd, "snap_distance": round(d, 2)}
        return nearest

    def update_risks(self, mode='random', manual_risks=None, seed=None):
        if seed is not None:
            self.seed = seed
            self.rng = random.Random(seed)
        for u, v, data in self.graph.edges(data=True):
            ek = f"{u}-{v}"
            data['risk'] = manual_risks[ek] if mode == 'manual' and manual_risks and ek in manual_risks else round(self.rng.uniform(0, 1), 2)
            data['cost'] = round(data['distance'] * (1 + data['risk']), 2)
        self._process_graph()

    def remove_edges(self, edge_keys):
        removed = []
        for ek in edge_keys:
            parts = ek.split('-')
            if len(parts) == 2:
                u, v = int(parts[0]), int(parts[1])
                if self.graph.has_edge(u, v):
                    data = dict(self.graph[u][v])
                    self.graph.remove_edge(u, v)
                    removed.append({"source": str(u), "target": str(v), "data": data})
        self.removed_edges.extend(removed)
        self._process_graph()
        return len(removed)

    def remove_nearest_edge(self, lat, lng):
        min_dist, best_edge = float('inf'), None
        for u, v, data in self.graph.edges(data=True):
            mid_lat = (self.graph.nodes[u]['y'] + self.graph.nodes[v]['y']) / 2
            mid_lng = (self.graph.nodes[u]['x'] + self.graph.nodes[v]['x']) / 2
            d = haversine(lat, lng, mid_lat, mid_lng)
            if d < min_dist:
                min_dist = d
                best_edge = (u, v, dict(data), mid_lat, mid_lng)
        if best_edge:
            u, v, data, mlat, mlng = best_edge
            self.graph.remove_edge(u, v)
            self.removed_edges.append({"source": str(u), "target": str(v), "data": data})
            self._process_graph()
            return {"removed": f"{u}-{v}", "distance": min_dist,
                    "removed_midpoint": {"lat": mlat, "lng": mlng}}
        return None

    def restore_edges(self):
        count = 0
        for edge in self.removed_edges:
            u, v = int(edge['source']), int(edge['target'])
            if not self.graph.has_edge(u, v):
                self.graph.add_edge(u, v, **edge['data'])
                count += 1
        self.removed_edges = []
        self._process_graph()
        return count

    def get_path_coordinates(self, path_nodes):
        return [[self.nodes_data[str(n)]['lat'], self.nodes_data[str(n)]['lng']]
                for n in path_nodes if str(n) in self.nodes_data]

    def get_route_geometry(self, path_nodes):
        coordinates = []
        for i in range(len(path_nodes) - 1):
            u, v = path_nodes[i], path_nodes[i + 1]
            if not self.graph.has_edge(u, v):
                continue
            data = self.graph[u][v]
            geom = data.get('geom')
            if geom and len(geom) >= 2:
                ux, uy = self.graph.nodes[u]['x'], self.graph.nodes[u]['y']
                d_first = (geom[0][0] - ux) ** 2 + (geom[0][1] - uy) ** 2
                d_last = (geom[-1][0] - ux) ** 2 + (geom[-1][1] - uy) ** 2
                ordered = list(reversed(geom)) if d_last < d_first else list(geom)
                segment = [[c[1], c[0]] for c in ordered]
            else:
                segment = [[self.graph.nodes[u]['y'], self.graph.nodes[u]['x']],
                           [self.graph.nodes[v]['y'], self.graph.nodes[v]['x']]]
            coordinates.extend(segment[1:] if coordinates else segment)
        return coordinates

    def get_path_edges(self, path_nodes):
        edges = []
        for i in range(len(path_nodes) - 1):
            u, v = path_nodes[i], path_nodes[i + 1]
            if self.graph.has_edge(u, v):
                d = self.graph[u][v]
                edges.append({"source": str(u), "target": str(v),
                    "distance": d.get('distance', 0), "risk": d.get('risk', 0), "cost": d.get('cost', 0)})
        return edges

    def get_path_metrics(self, path_nodes):
        total_dist, total_cost, total_risk, ec = 0.0, 0.0, 0.0, 0
        for i in range(len(path_nodes) - 1):
            u, v = path_nodes[i], path_nodes[i + 1]
            if self.graph.has_edge(u, v):
                total_dist += self.graph[u][v].get('distance', 0)
                total_cost += self.graph[u][v].get('cost', 0)
                total_risk += self.graph[u][v].get('risk', 0)
                ec += 1
        return round(total_dist, 2), round(total_cost, 2), round(total_risk / max(ec, 1), 3)

    def get_path_risk_profile(self, path_nodes):
        """Length-weighted risk statistics of a path.

        avg_risk (get_path_metrics) is an unweighted mean over edges, so a short risky
        edge counts as much as a long one. The exposure below weights risk by distance,
        which is consistent with the cost function d * (1 + r).
        """
        high = self.risk_thresholds.get("medium_max", 0.66)
        dist, weighted, max_r, high_dist = 0.0, 0.0, 0.0, 0.0
        for i in range(len(path_nodes) - 1):
            u, v = path_nodes[i], path_nodes[i + 1]
            if self.graph.has_edge(u, v):
                d = self.graph[u][v].get('distance', 0)
                r = self.graph[u][v].get('risk', 0)
                dist += d
                weighted += d * r
                max_r = max(max_r, r)
                if r > high:
                    high_dist += d
        return {"distance": dist, "risk_weighted_sum": weighted, "max_risk": max_r,
                "high_risk_distance": high_dist}

    def export_session(self):
        nodes = [{"id": str(n), "lat": d['y'], "lng": d['x']} for n, d in self.graph.nodes(data=True)]
        edges = [{"source": str(u), "target": str(v), "distance": d.get('distance', 0),
                  "risk": d.get('risk', 0), "cost": d.get('cost', 0)}
                 for u, v, d in self.graph.edges(data=True)]
        return {"nodes": nodes, "edges": edges, "center": {"lat": self.center_lat, "lng": self.center_lng},
                "removed_edges": self.removed_edges, "risk_thresholds": self.risk_thresholds}
