# RouteX

Routing engine for the SF Bay Area road network. C++ core (A*, Dijkstra, contraction hierarchies) over OSM data, PostGIS for spatial queries, XGBoost for ETA prediction. Python bindings via pybind11.

**Stack:** C++, Python (pybind11), PostgreSQL + PostGIS, XGBoost

## What it does

Loads the Bay Area OSM extract into a graph (~400K road segments), preprocesses it with contraction hierarchies, and serves point-to-point routing queries in sub-millisecond time. PostGIS sits underneath for spatial extraction, bounding-box joins, and geofencing. An XGBoost model predicts per-segment ETA from OSM road metadata.

## Routing

Three algorithms, same graph:

| Algorithm | Avg query | Use case |
|---|---|---|
| Dijkstra | 45ms | baseline / correctness check |
| A* (haversine heuristic) | ~12ms | one-off queries, no preprocessing |
| CH bidirectional | **<1ms** | production path |

CH preprocessing:

- Edge-difference node ordering — contract the node that adds the fewest shortcuts first
- 40K+ shortcuts generated over the full Bay Area graph
- Bidirectional search from source and target, meet in the middle on contracted graph
- Shortcut unpacking on the returned path to recover the real road sequence

**45x speedup** over vanilla Dijkstra on 1000 random OD queries. Measured average and p95; p95 holds the same shape.

## Spatial layer

PostgreSQL + PostGIS holds 150K+ road geometries. Three query patterns:

- **Network extraction** — `ST_Intersects` with a bounding box pulls the subgraph for a region
- **Spatial joins** — match GPS pings or POIs to nearest road segment
- **Geofencing** — `ST_Contains` / `ST_Within` for point-in-polygon checks against service-area polygons

Loaded via `osm2pgsql` from the Geofabrik norcal extract.

## ETA model

XGBoost regressor over OSM segment features:

- Speed tag (`maxspeed`)
- Highway class (motorway, trunk, primary, secondary, tertiary, residential, ...)  — 12 types
- Lane count
- Surface type
- Segment length

Target: per-segment travel time derived from length and observed speed data.

Train/test 80/20 split, 5K held-out routes for validation. **<15% MAPE** on held-out set.

## Build

```bash
# C++ core
mkdir build && cd build
cmake .. && make -j

# Python bindings
pip install -e .

# DB
createdb routex
psql routex -c "CREATE EXTENSION postgis;"
osm2pgsql -d routex norcal-latest.osm.pbf
```

## Use

```python
from routex import Graph, CHRouter

g = Graph.from_postgis("postgresql://localhost/routex")
router = CHRouter(g)
router.preprocess()  # one-time, ~minutes

path, eta = router.query(start=(37.7749, -122.4194), end=(37.3382, -121.8863))
```

## Layout

```
src/
  graph.cpp           # adjacency representation
  dijkstra.cpp        # baseline + bidirectional
  astar.cpp           # haversine heuristic
  ch/
    preprocess.cpp    # node ordering, shortcut generation
    query.cpp         # bidirectional CH search
    unpack.cpp        # shortcut unpacking
  bindings.cpp        # pybind11
python/
  routex/
    __init__.py
    eta.py            # XGBoost wrapper
    postgis.py        # spatial query helpers
sql/
  schema.sql
  geofence.sql
bench/
  query_latency.py    # 1000 OD queries, Dijkstra vs CH
  eta_eval.py         # MAPE on held-out routes
```

## Data

Bay Area OSM extract from [Geofabrik](https://download.geofabrik.de/north-america/us/california/norcal.html) (`norcal-latest.osm.pbf`). ~400K road segments after filtering to the drive network.
