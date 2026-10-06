from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import logging
import asyncio
import json
import csv
import io
from pathlib import Path
from pydantic import BaseModel
from typing import List, Optional, Dict

from graph_service import GraphService
from algorithms import solve_vrp, run_comparison_vrp, run_single_route, run_benchmark
from experiment_runner import ExperimentRunner, load_results, figure_path, excel_path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

app = FastAPI()
api_router = APIRouter(prefix="/api")
graph_service = GraphService()
experiment_runner = ExperimentRunner()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class InitRequest(BaseModel):
    lat: float = -2.692   # Mamuju, the paper's study area
    lng: float = 118.898
    radius: int = 1500
    seed: Optional[int] = 42          # same risk field as the paper; None = new random risks
    prefer_cache: bool = True         # use cached OSM responses before calling Overpass

class StartPoint(BaseModel):
    node_id: str
    agents: int = 1

class DestPoint(BaseModel):
    node_id: str

class OptimizeRequest(BaseModel):
    starts: List[StartPoint]
    destinations: List[DestPoint]
    algorithm: str
    algo_params: Optional[Dict] = None
    force_distribution: bool = False

class CompareRequest(BaseModel):
    starts: List[StartPoint]
    destinations: List[DestPoint]
    algorithms: List[str]
    algo_params: Optional[Dict] = None
    force_distribution: bool = False

class BenchmarkRequest(BaseModel):
    starts: List[StartPoint]
    destinations: List[DestPoint]
    algorithms: List[str]
    runs_per_algo: int = 5
    algo_params: Optional[Dict] = None
    force_distribution: bool = False

class RiskUpdateRequest(BaseModel):
    mode: str = "random"
    risks: Optional[Dict[str, float]] = None
    seed: Optional[int] = None

class EdgeRemoveRequest(BaseModel):
    lat: float
    lng: float

class ExperimentRunRequest(BaseModel):
    jobs: Optional[int] = None

class RiskThresholdRequest(BaseModel):
    low_max: float = 0.33
    medium_max: float = 0.66


@api_router.get("/")
async def root():
    return {"message": "OptiRoute - Disaster Relief Route Optimization API"}


@api_router.post("/graph/init")
async def init_graph(req: InitRequest):
    try:
        result = await asyncio.to_thread(graph_service.initialize, req.lat, req.lng, req.radius, req.seed,
                                          req.prefer_cache)
        return result
    except Exception as e:
        logger.error(f"Graph init error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/graph/data")
async def get_graph_data():
    if not graph_service.is_initialized:
        raise HTTPException(status_code=400, detail="Graph not initialized")
    return {"edges": graph_service.geojson_edges, "nodes": graph_service.geojson_nodes,
            "nodes_list": graph_service.nodes_list}


@api_router.get("/graph/nearest")
async def get_nearest_node(lat: float, lng: float):
    if not graph_service.is_initialized:
        raise HTTPException(status_code=400, detail="Graph not initialized")
    node = graph_service.get_nearest_node(lat, lng)
    if not node: raise HTTPException(status_code=404, detail="No node found")
    return node


@api_router.get("/graph/summary")
async def get_graph_summary():
    if not graph_service.is_initialized:
        return {"initialized": False}
    return {"initialized": True, "nodes_count": len(graph_service.nodes_data),
            "edges_count": len(graph_service.edges_data),
            "removed_edges": len(graph_service.removed_edges)}


@api_router.post("/graph/reset")
async def reset_graph():
    graph_service.graph = None
    graph_service.nodes_data = {}
    graph_service.edges_data = {}
    graph_service.geojson_edges = None
    graph_service.geojson_nodes = None
    graph_service.nodes_list = []
    graph_service.is_initialized = False
    graph_service.removed_edges = []
    return {"status": "reset"}


@api_router.post("/route/optimize")
async def optimize_route(req: OptimizeRequest):
    if not graph_service.is_initialized:
        raise HTTPException(status_code=400, detail="Graph not initialized")
    try:
        starts = [{"node_id": s.node_id, "agents": s.agents} for s in req.starts]
        dests = [{"node_id": d.node_id} for d in req.destinations]
        result = await asyncio.to_thread(solve_vrp, graph_service, starts, dests, req.algorithm,
                                          req.algo_params, req.force_distribution)
        return result
    except Exception as e:
        logger.error(f"Optimize error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/route/compare")
async def compare_algorithms(req: CompareRequest):
    if not graph_service.is_initialized:
        raise HTTPException(status_code=400, detail="Graph not initialized")
    try:
        starts = [{"node_id": s.node_id, "agents": s.agents} for s in req.starts]
        dests = [{"node_id": d.node_id} for d in req.destinations]
        results = await asyncio.to_thread(run_comparison_vrp, graph_service, starts, dests,
                                           req.algorithms, req.algo_params, req.force_distribution)
        return {"results": results}
    except Exception as e:
        logger.error(f"Compare error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/route/benchmark")
async def benchmark_algorithms(req: BenchmarkRequest):
    if not graph_service.is_initialized:
        raise HTTPException(status_code=400, detail="Graph not initialized")
    try:
        starts = [{"node_id": s.node_id, "agents": s.agents} for s in req.starts]
        dests = [{"node_id": d.node_id} for d in req.destinations]
        results = await asyncio.to_thread(
            run_benchmark, graph_service, starts, dests,
            req.algorithms, req.runs_per_algo, req.algo_params, req.force_distribution
        )
        return {"results": results}
    except Exception as e:
        logger.error(f"Benchmark error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/risk/update")
async def update_risk(req: RiskUpdateRequest):
    if not graph_service.is_initialized:
        raise HTTPException(status_code=400, detail="Graph not initialized")
    await asyncio.to_thread(graph_service.update_risks, req.mode, req.risks, req.seed)
    return {"status": "updated", "edges_count": len(graph_service.edges_data),
            "edges": graph_service.geojson_edges, "nodes": graph_service.geojson_nodes}


@api_router.post("/risk/thresholds")
async def update_thresholds(req: RiskThresholdRequest):
    graph_service.risk_thresholds = {"low_max": req.low_max, "medium_max": req.medium_max}
    return {"status": "updated", "thresholds": graph_service.risk_thresholds}


@api_router.post("/graph/remove-edge")
async def remove_edge(req: EdgeRemoveRequest):
    if not graph_service.is_initialized:
        raise HTTPException(status_code=400, detail="Graph not initialized")
    result = await asyncio.to_thread(graph_service.remove_nearest_edge, req.lat, req.lng)
    if not result: raise HTTPException(status_code=404, detail="No edge found nearby")
    return {"status": "removed", **result, "edges": graph_service.geojson_edges,
            "removed_count": len(graph_service.removed_edges)}


@api_router.post("/graph/restore-edges")
async def restore_edges():
    if not graph_service.is_initialized:
        raise HTTPException(status_code=400, detail="Graph not initialized")
    count = await asyncio.to_thread(graph_service.restore_edges)
    return {"status": "restored", "restored_count": count, "edges": graph_service.geojson_edges}


@api_router.get("/export/session")
async def export_session():
    if not graph_service.is_initialized:
        raise HTTPException(status_code=400, detail="Graph not initialized")
    data = graph_service.export_session()
    return data


@api_router.get("/export/results/csv")
async def export_csv(results_json: str = ""):
    try:
        results = json.loads(results_json) if results_json else []
    except (json.JSONDecodeError, TypeError):
        results = []
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Algorithm", "Agent", "Route", "Distance (m)", "Avg Risk", "Cost", "Time (ms)"])
    for r in results:
        algo = r.get("algorithm", "")
        for route in r.get("routes", []):
            writer.writerow([algo, route.get("agent_id", ""), route.get("route_label", ""),
                             route.get("total_distance", 0), route.get("avg_risk", 0),
                             route.get("total_cost", 0), r.get("summary", {}).get("computation_time_ms", 0)])
    output.seek(0)
    return StreamingResponse(output, media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=optiroute_results.csv"})


@api_router.post("/import/session")
async def import_session(data: Dict):
    return {"status": "imported", "message": "Session data received"}


# ---------- Paper experiments (one-button full pipeline) ----------
@api_router.post("/experiments/run")
async def run_experiments(req: ExperimentRunRequest):
    try:
        return experiment_runner.start(req.jobs)
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))


@api_router.get("/experiments/status")
async def experiments_status():
    return experiment_runner.status()


@api_router.post("/experiments/cancel")
async def cancel_experiments():
    return {"cancelled": experiment_runner.cancel()}


@api_router.get("/experiments/results")
async def experiments_results(run_id: Optional[str] = None):
    try:
        return await asyncio.to_thread(load_results, run_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@api_router.get("/experiments/figure/{run_id}/{name:path}")
async def experiments_figure(run_id: str, name: str):
    try:
        return FileResponse(figure_path(run_id, name), media_type="image/png")
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@api_router.get("/experiments/excel/{run_id}")
async def experiments_excel(run_id: str):
    try:
        return FileResponse(excel_path(run_id), filename=f"OptiRoute_Results_{run_id}.xlsx",
                            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


app.include_router(api_router)
app.add_middleware(CORSMiddleware, allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"], allow_headers=["*"])
