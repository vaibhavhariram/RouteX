"""
FastAPI app for Atlas MVP: Berkeley road routing + ETA.
POST /route accepts origin/dest lat/lon and returns GeoJSON + ETA.
"""
import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from graph import get_graph
from routing import route

app = FastAPI(title="Atlas MVP", description="Berkeley road routing + ETA prototype")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RouteRequest(BaseModel):
    origin_lat: float
    origin_lon: float
    dest_lat: float
    dest_lon: float
    algo: str = "astar"


@app.on_event("startup")
def load_graph():
    G = get_graph()
    app.state.G = G
    print(f"Graph loaded: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")


@app.post("/route")
def compute_route(req: RouteRequest):
    t0 = time.perf_counter()
    G = app.state.G
    line_coords, distance_m, eta_sec, n_nodes = route(
        G,
        req.origin_lat,
        req.origin_lon,
        req.dest_lat,
        req.dest_lon,
        algo=req.algo,
        profile="baseline",
    )
    compute_ms = round((time.perf_counter() - t0) * 1000, 1)
    geometry = {
        "type": "LineString",
        "coordinates": line_coords,
    }
    return {
        "geometry": geometry,
        "distance_m": round(distance_m, 2),
        "eta_sec": round(eta_sec, 2),
        "algo": req.algo,
        "n_nodes": n_nodes,
        "compute_ms": compute_ms,
        "graph_nodes": G.number_of_nodes(),
        "graph_edges": G.number_of_edges(),
    }
