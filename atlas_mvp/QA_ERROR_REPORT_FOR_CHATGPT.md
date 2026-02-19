# Manual QA Error Report & Bug Report (for ChatGPT diagnosis)

**Project:** Atlas MVP backend — Berkeley road routing + ETA  
**QA run:** Manual steps 0–6 (server: uvicorn from `atlas_mvp/backend`)  
**Date:** 2026-02-11  

---

## 0) Server start

- **Command:** `source venv/bin/activate` then `python -m uvicorn app:app`
- **Result:** Server started successfully. Uvicorn bound to port 8000.

---

## 1) Sanity: FastAPI /docs

- **Command:** `curl -i http://127.0.0.1:8000/docs`
- **Result:** PASS
- **Observed:** `HTTP/1.1 200 OK`, HTML for Swagger UI returned.

---

## 2) Critical: POST /route returns 200 and JSON

- **Command:**
  ```bash
  curl -i -X POST http://127.0.0.1:8000/route \
    -H "Content-Type: application/json" \
    -d '{"origin_lat":37.8715,"origin_lon":-122.2730,"dest_lat":37.8699,"dest_lon":-122.2595,"algo":"astar","profile":"baseline"}'
  ```
- **Result:** PASS
- **Observed:** `HTTP/1.1 200 OK`, JSON body with `geometry`, `distance_m`, `eta_sec`, `algo`, `profile`, `n_nodes`. Coordinates are `[lon, lat]`.

---

## 3) Response shape (keys + coords)

- **Command:**
  ```bash
  curl -s -X POST ... | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.keys()); print('n_coords', len(d['geometry']['coordinates'])); print('first', d['geometry']['coordinates'][0]);"
  ```
- **Result:** PASS
- **Observed:**
  - `keys: ['geometry', 'distance_m', 'eta_sec', 'algo', 'profile', 'n_nodes']`
  - `n_coords 17`
  - `first [-122.273015, 37.8715634]` (lon first, lat second)

---

## 4) Dijkstra returns 200

- **Command:** Same as step 2 with `"algo":"dijkstra","profile":"baseline"`.
- **Result:** PASS
- **Observed:** HTTP 200.

---

## 5) Rushhour increases ETA

- **Step 5a (baseline ETA):** PASS — `eta_sec` = 167.74.
- **Step 5b (rushhour ETA):** **FAIL**
  - **Command:**
    ```bash
    curl -s -X POST http://127.0.0.1:8000/route \
      -H "Content-Type: application/json" \
      -d '{"origin_lat":37.8715,"origin_lon":-122.2730,"dest_lat":37.8699,"dest_lon":-122.2595,"algo":"dijkstra","profile":"rushhour"}' \
      | python3 -c "import sys,json; print(json.load(sys.stdin)['eta_sec'])"
    ```
  - **Observed:** Python got empty/invalid JSON; `json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)`.
  - **Actual HTTP response:** `500 Internal Server Error` with body `Internal Server Error` (no JSON).

---

## 6) Same origin/dest (weird input)

- **Command:** POST /route with `dest_lat`/`dest_lon` identical to `origin_lat`/`origin_lon`.
- **Result:** PASS (acceptable for demo)
- **Observed:** `HTTP/1.1 200 OK`, JSON with single-point LineString, `distance_m`: 0.0, `eta_sec`: 0.0, `n_nodes`: 1.

---

# Bug report: 500 when `profile=rushhour`

## Summary

- **Endpoint:** `POST /route`
- **Failing case:** Any request with `"profile": "rushhour"`. Same request with `"profile": "baseline"` returns 200.
- **HTTP:** 500 Internal Server Error; body is plain text "Internal Server Error", not JSON.

## Server traceback (Terminal 1 — uvicorn)

```
INFO:     127.0.0.1:53960 - "POST /route HTTP/1.1" 500 Internal Server Error
ERROR:    Exception in ASGI application
Traceback (most recent call last):
  File ".../uvicorn/protocols/http/httptools_impl.py", line 416, in run_asgi
    result = await app(...)
  ...
  File "/Users/vaibhavh/Atlas/atlas_mvp/backend/app.py", line 40, in compute_route
    line_coords, distance_m, eta_sec, n_nodes = route(
        G,
        req.origin_lat,
        req.origin_lon,
        req.dest_lat,
        req.dest_lon,
        algo=req.algo,
        profile=req.profile,
    )
  File "/Users/vaibhavh/Atlas/atlas_mvp/backend/routing.py", line 166, in route
    D = _to_digraph_with_profile(G, profile)
  File "/Users/vaibhavh/Atlas/atlas_mvp/backend/routing.py", line 101, in _to_digraph_with_profile
    sample = next(G.edges(keys=True, data=True), None)
TypeError: 'OutMultiEdgeDataView' object is not an iterator
```

## Root cause (for ChatGPT to fix)

- **File:** `atlas_mvp/backend/routing.py`
- **Function:** `_to_digraph_with_profile`
- **Line:** ~101 (the line that does `sample = next(G.edges(keys=True, data=True), None)` when `profile == "rushhour"`).

In NetworkX, `G.edges(keys=True, data=True)` returns a **view**, not an iterator. Passing it to `next(..., None)` raises:

`TypeError: 'OutMultiEdgeDataView' object is not an iterator`

The same pattern was already fixed in `graph.py` for `G.edges(data=True)` by using `next(iter(G.edges(data=True)), None)`.

## Required fix (already applied in repo)

Change the line from:

```python
sample = next(G.edges(keys=True, data=True), None)
```

to:

```python
sample = next(iter(G.edges(keys=True, data=True)), None)
```

so that the view is turned into an iterator before calling `next`.

## Verification after fix

- Run:  
  `curl -s -w "\n%{http_code}" -X POST http://127.0.0.1:8000/route -H "Content-Type: application/json" -d '{"origin_lat":37.8715,"origin_lon":-122.2730,"dest_lat":37.8699,"dest_lon":-122.2595,"algo":"dijkstra","profile":"rushhour"}'`
- Expect: HTTP 200 and JSON with `eta_sec` **greater than** the baseline (167.74 for the same coords).

---

## QA summary table

| Step | Description              | Result |
|------|--------------------------|--------|
| 0    | Server start             | PASS   |
| 1    | GET /docs 200            | PASS   |
| 2    | POST /route 200 + JSON   | PASS   |
| 3    | Response shape + coords | PASS   |
| 4    | Dijkstra 200             | PASS   |
| 5    | Rushhour ETA > baseline | **FAIL** (500 on profile=rushhour) |
| 6    | Same origin/dest         | PASS   |

Only failure: **profile=rushhour** triggers the `TypeError` above; fix is one line in `routing.py` as specified.
