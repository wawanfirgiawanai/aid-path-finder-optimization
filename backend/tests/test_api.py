"""Backend API tests for OptiRoute"""
import os
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def graph_init(session):
    r = session.post(f"{API}/graph/init", json={"lat": -6.175, "lng": 106.827, "radius": 1500}, timeout=60)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["nodes_count"] > 0
    assert data["edges_count"] > 0
    return data


class TestRoot:
    def test_root(self, session):
        r = session.get(f"{API}/", timeout=10)
        assert r.status_code == 200


class TestGraph:
    def test_init(self, graph_init):
        assert "nodes_count" in graph_init
        assert "edges_count" in graph_init

    def test_data(self, session, graph_init):
        r = session.get(f"{API}/graph/data", timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert "edges" in data
        feats = data["edges"].get("features", [])
        assert len(feats) > 0
        assert "risk" in feats[0]["properties"]


class TestRisk:
    def test_update(self, session, graph_init):
        r = session.post(f"{API}/risk/update", json={}, timeout=30)
        assert r.status_code == 200

    def test_thresholds(self, session, graph_init):
        r = session.post(f"{API}/risk/thresholds", json={"low_max": 0.3, "medium_max": 0.7}, timeout=10)
        assert r.status_code == 200


class TestRouting:
    @pytest.fixture(scope="class")
    def points(self, session, graph_init):
        r1 = session.get(f"{API}/graph/nearest", params={"lat": -6.175, "lng": 106.827}, timeout=10)
        r2 = session.get(f"{API}/graph/nearest", params={"lat": -6.180, "lng": 106.830}, timeout=10)
        assert r1.status_code == 200 and r2.status_code == 200
        return r1.json(), r2.json()

    def test_optimize(self, session, points, graph_init):
        start, end = points
        payload = {
            "starts": [{"node_id": start["id"], "agents": 1}],
            "destinations": [{"node_id": end["id"]}],
            "algorithm": "dijkstra",
            "force_distribution": False,
        }
        r = session.post(f"{API}/route/optimize", json=payload, timeout=60)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "routes" in data
        assert len(data["routes"]) >= 1
        # verify route geometry present
        assert "route_geometry" in data["routes"][0] or "path" in data["routes"][0]

    def test_compare(self, session, points, graph_init):
        start, end = points
        payload = {
            "starts": [{"node_id": start["id"], "agents": 1}],
            "destinations": [{"node_id": end["id"]}],
            "algorithms": ["dijkstra", "astar", "bfs"],
            "force_distribution": False,
        }
        r = session.post(f"{API}/route/compare", json=payload, timeout=120)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data

    def test_benchmark(self, session, points, graph_init):
        start, end = points
        payload = {
            "starts": [{"node_id": start["id"], "agents": 1}],
            "destinations": [{"node_id": end["id"]}],
            "runs_per_algo": 2,
            "algorithms": ["dijkstra", "astar"],
        }
        r = session.post(f"{API}/route/benchmark", json=payload, timeout=120)
        assert r.status_code == 200, r.text


class TestEdges:
    def test_remove_restore(self, session, graph_init):
        # Remove a nearby edge
        r = session.post(f"{API}/graph/remove-edge", json={"lat": -6.175, "lng": 106.827}, timeout=15)
        assert r.status_code == 200, r.text
        r2 = session.post(f"{API}/graph/restore-edges", json={}, timeout=15)
        assert r2.status_code == 200
