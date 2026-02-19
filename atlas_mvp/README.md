# Atlas MVP — Berkeley Road Routing + ETA Prototype

Minimal Berkeley-scope routing prototype: click map → get route polyline + ETA. Backend: FastAPI + OSMnx + NetworkX. Frontend: single HTML + Leaflet.

---

## Quick Start

### 1. Backend

```bash
cd atlas_mvp/backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --reload
```

### 2. Frontend

Open `frontend/index.html` in a browser (e.g. drag into Chrome, or `open frontend/index.html`).

> **Note:** First backend run downloads OSM data for Berkeley (~30–60 s). Subsequent runs load from `data/graph.graphml` and start instantly.

---

## Run Commands Summary

| Step | Command |
|------|---------|
| Create venv | `cd atlas_mvp/backend && python -m venv venv` |
| Activate | `source venv/bin/activate` (macOS/Linux) |
| Install deps | `pip install -r requirements.txt` |
| Start API | `uvicorn app:app --reload` |
| Open frontend | `open ../frontend/index.html` (or drag file into browser) |

---

## API

**POST** `/route`

```json
{
  "origin_lat": 37.8715,
  "origin_lon": -122.2730,
  "dest_lat": 37.8688,
  "dest_lon": -122.2605,
  "algo": "astar",
  "profile": "baseline"
}
```

Response:

```json
{
  "geojson": { "type": "LineString", "coordinates": [[lon, lat], ...] },
  "distance_m": 1234.5,
  "eta_sec": 120.3,
  "algo": "astar",
  "profile": "baseline",
  "n_nodes": 42
}
```

---

## 60-Second Demo Script

1. **Start backend** — `uvicorn app:app --reload`; wait for "Uvicorn running".
2. **Open frontend** — Open `frontend/index.html` in a browser.
3. **Click map** — First click = Origin (green marker), second click = Destination (red marker).
4. **Route** — Click "Route"; polyline appears and info box shows distance (km), ETA (min), nodes, algo/profile.
5. **Compare profiles** — Change to "Rush hour", click Route again; ETA increases.
6. **Clear** — Click "Clear" to reset markers and route.

---

## Repo Structure

```
atlas_mvp/
  backend/
    app.py          # FastAPI app, CORS, /route
    routing.py      # A*/Dijkstra, heuristic, best-edge selection
    graph.py        # OSMnx load, cache to data/graph.graphml
    requirements.txt
    data/           # graph.graphml (created on first run)
  frontend/
    index.html      # Leaflet map, click-to-route UI
  README.md
```

---

## Requirements

- Python 3.11+
- macOS / Linux (developed on macOS)
