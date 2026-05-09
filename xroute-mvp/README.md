# XRoute MVP — High-Performance Road Routing Engine

A full-stack routing system combining C++ performance algorithms with Python/ML for accurate ETAs. Features multiple pathfinding algorithms (Dijkstra, A*, Contraction Hierarchies), graph preprocessing, and ML-based travel time prediction.

**Key Features:**
- ⚡ C++ routing algorithms (Dijkstra, A*, Contraction Hierarchies) compiled via pybind11
- 🤖 ML-based ETA model (XGBoost) for realistic travel time prediction
- 🗺️ Interactive web frontend for route visualization
- 🐘 PostgreSQL/PostGIS integration for road network storage
- 🐳 Docker Compose for instant setup

---

## Quick Start (Docker — 2 minutes)

**Prerequisites:** Docker & Docker Compose

```bash
# Start database and backend
docker-compose up -d

# Open frontend in browser
open xroute-mvp/frontend/index.html
# OR: drag the file into Chrome/Firefox
```

Backend will be available at `http://localhost:8000`  
API docs: `http://localhost:8000/docs`

---

## Manual Setup (Build from Source)

### Prerequisites
- **macOS/Linux** (developed on macOS; Windows WSL2 supported)
- **Python 3.11+**
- **CMake 3.18+** (for C++ build)
- **C++17 compiler** (clang/gcc)
- **PostgreSQL** (or use Docker: `docker-compose up -d db`)

### 1. Build C++ Routing Engine

```bash
cd xroute-mvp
mkdir build && cd build
cmake -DCMAKE_BUILD_TYPE=Release ..
cmake --build . -j$(nproc)
cd ..
```

This compiles the C++ algorithms into `backend/xroute_cpp.cpython-313-darwin.so` (or equivalent for your Python version).

### 2. Setup Python Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Start API server
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Backend runs on `http://localhost:8000`

### 3. Open Frontend

```bash
# In a new terminal from xroute-mvp/
open frontend/index.html
# OR: drag file into browser
```

---

## 60-Second Demo

1. **Ensure backend is running** — See "Setup Python Backend" above
2. **Open frontend** — `open frontend/index.html`
3. **Click map** — First click = green marker (origin), second click = red marker (destination)
4. **Select algorithm** — Choose from Dijkstra, A*, or Contraction Hierarchies
5. **Route** — Click "Route" button
6. **Results** — Polyline appears with distance, ETA, and algorithm stats
7. **Compare** — Change algorithm and route again to see performance differences

---

## API Reference

### POST `/route`

Compute a shortest path and estimate travel time.

**Request:**
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

**Parameters:**
- `algo`: `"dijkstra"`, `"astar"`, or `"ch"` (Contraction Hierarchies)
- `profile`: `"baseline"` (default) or other profiles from database

**Response:**
```json
{
  "geojson": {
    "type": "LineString",
    "coordinates": [[lon, lat], [lon, lat], ...]
  },
  "distance_m": 1234.5,
  "eta_sec": 120.3,
  "algo": "astar",
  "profile": "baseline",
  "n_nodes": 42,
  "time_ms": 45.2
}
```

### GET `/docs`

Interactive Swagger UI for all endpoints.

---

## Architecture

```
xroute-mvp/
├── backend/                    # Python FastAPI application
│   ├── app.py                 # FastAPI server, endpoints, CORS
│   ├── routing.py             # Python routing orchestration
│   ├── graph.py               # OSMnx graph loading & caching
│   ├── graph_loader.py        # Graph initialization
│   ├── ch.py                  # Contraction Hierarchy preprocessing
│   ├── eta_model.py           # XGBoost ETA prediction
│   ├── db.py                  # PostgreSQL/PostGIS connection
│   ├── benchmark.py           # Algorithm performance testing
│   └── requirements.txt
│
├── cpp/                        # C++ routing algorithms
│   ├── include/
│   │   └── graph.h            # Graph data structure
│   └── src/
│       ├── graph.cpp          # Road network representation
│       ├── dijkstra.cpp       # Dijkstra's algorithm
│       ├── astar.cpp          # A* with heuristics
│       ├── ch.cpp             # Contraction Hierarchies
│       └── bindings.cpp       # pybind11 Python bindings
│
├── frontend/
│   └── index.html             # Leaflet.js interactive map UI
│
├── sql/
│   └── schema.sql             # PostgreSQL schema (road network)
│
├── CMakeLists.txt             # C++ build configuration
├── docker-compose.yml         # Database + service orchestration
└── README.md
```

---

## Algorithms Explained

### Dijkstra's Algorithm
- **Time:** O((V + E) log V)
- **Use case:** Guaranteed shortest path, good baseline
- **Trade-off:** Slower on large graphs

### A* Search
- **Time:** O((V + E) log V) with heuristic pruning
- **Use case:** Faster for long routes (uses straight-line distance heuristic)
- **Trade-off:** Slightly more memory, good balance of speed/accuracy

### Contraction Hierarchies (CH)
- **Preprocessing:** O(V log V) with space O(V)
- **Query:** O(log V) with careful shortcut management
- **Use case:** Ultra-fast routing for repeated queries
- **Trade-off:** Longer preprocessing, ideal for production systems

---

## ETA Model

The `eta_model.py` module uses **XGBoost** to predict travel time based on:
- Road type (highway, arterial, residential)
- Time of day
- Day of week
- Historical traffic patterns
- Segment length

Trained on real OSM data and traffic profiles. Accessible via `/route` response's `eta_sec` field.

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| **Routing Engine** | C++ 17 (Dijkstra, A*, Contraction Hierarchies) |
| **Python Bindings** | pybind11 |
| **Backend** | FastAPI, Uvicorn |
| **Graph Processing** | OSMnx, NetworkX, GeoPandas |
| **ML/ETA** | XGBoost, scikit-learn |
| **Database** | PostgreSQL 16 + PostGIS 3.4 |
| **Frontend** | Leaflet.js, vanilla HTML/CSS/JS |
| **Containerization** | Docker & Docker Compose |

---

## Development Notes

### Rebuild C++ After Changes
```bash
cd build
cmake --build . -j$(nproc)
cd ..
```

### Run Tests/Benchmarks
```bash
cd backend
python benchmark.py
```

### Debug Mode (with sanitizers)
```bash
cd build
cmake -DCMAKE_BUILD_TYPE=Debug ..
cmake --build . -j$(nproc)
```

---

## System Requirements

- **RAM:** 4+ GB (for large road graphs)
- **Disk:** 2+ GB (OSM data cache)
- **Network:** For initial OSM data download (~30–60 sec on first run)

---

## Troubleshooting

**"Segmentation fault" when importing xroute_cpp**
- Rebuild C++ module: `rm -rf build && mkdir build && cd build && cmake -DCMAKE_BUILD_TYPE=Release .. && cmake --build . -j$(nproc)`
- Ensure Python version matches build: Check output of `python --version` and rebuild if changed

**"Connection refused" on port 5432**
- Start database: `docker-compose up -d db` (or configure `POSTGRES_HOST` in `db.py`)

**Frontend shows "Cannot reach backend"**
- Check backend is running: `curl http://localhost:8000/docs`
- Verify CORS settings in `app.py` allow your origin

---

## For Recruiters

This project demonstrates:
- **Systems programming:** C++ graph algorithms with performance optimization
- **Full-stack development:** From low-level routing to web UI
- **ML engineering:** ETA prediction with real-world data
- **DevOps:** Docker containerization, database integration
- **Open-source:** Uses OSMnx, NetworkX, FastAPI, Leaflet
- **Testing & benchmarking:** Algorithm performance analysis

**To evaluate:**
1. Build & run: Follow "Manual Setup" above (15 min)
2. Interact with frontend, try different algorithms
3. Review API performance in Swagger UI (`/docs`)
4. Check code: C++ algorithms in `cpp/src/`, Python orchestration in `backend/app.py`

---

## License

[Add license here if applicable]

---

## Contact

For questions, open an issue or reach out to vaibhavhariram@berkeley.edu
