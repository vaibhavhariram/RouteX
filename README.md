# RouteX — High-Performance Road Routing Engine

> A full-stack system combining C++ performance algorithms with Python/ML for accurate ETAs and route optimization.

**Live Demo:** Open `xroute-mvp/frontend/index.html` in your browser after starting the backend.

---

## What's Inside

### [`xroute-mvp/`](xroute-mvp/) — Main Project

A complete routing system featuring:

- **C++ Routing Algorithms**: Dijkstra, A*, Contraction Hierarchies
- **ML-Based ETA**: XGBoost travel time prediction
- **FastAPI Backend**: RESTful routing service
- **PostgreSQL Integration**: Road network storage
- **Web Frontend**: Interactive Leaflet.js map
- **Docker Support**: One-command setup

**Quick start:**
```bash
cd xroute-mvp
docker-compose up -d          # Start database
python -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend:app --reload
```

Open `frontend/index.html` in your browser.

**Full documentation:** See [`xroute-mvp/README.md`](xroute-mvp/README.md)

---

## For Recruiters

This project demonstrates:
- **Full-stack development**: From C++ systems code to web UI
- **Performance optimization**: Algorithm design and benchmarking
- **ML integration**: Real-world ETA prediction
- **DevOps**: Docker, database management, CI/CD ready
- **Software architecture**: Clean separation of concerns

**To get started:**
1. Read [`xroute-mvp/README.md`](xroute-mvp/README.md) for full context
2. Follow the "Quick Start" section for Docker setup (2 minutes)
3. OR "Manual Setup" to build C++ from source (15 minutes)
4. Interact with the web frontend and API
5. Review source code in `xroute-mvp/{backend,cpp,frontend}`

---

## Stack at a Glance

| Component | Technology |
|-----------|-----------|
| Routing Engine | C++ 17 + pybind11 |
| Backend | FastAPI + Uvicorn |
| ETA Model | XGBoost + scikit-learn |
| Database | PostgreSQL 16 + PostGIS |
| Frontend | Leaflet.js + Vanilla JS |
| Build | CMake 3.18+ |
| Deployment | Docker & Docker Compose |

---

## Repository Structure

```
XRoute/
├── xroute-mvp/              # Main project (see details in its README)
│   ├── backend/             # FastAPI + routing logic
│   ├── cpp/                 # C++ algorithms (Dijkstra, A*, CH)
│   ├── frontend/            # Web UI
│   ├── sql/                 # Database schema
│   ├── CMakeLists.txt
│   ├── docker-compose.yml
│   └── README.md
└── README.md                # This file
```

---

## System Requirements

- **Python 3.11+**
- **CMake 3.18+** (for building C++)
- **C++17 compiler** (clang/gcc)
- **PostgreSQL 16** (or Docker)
- **4+ GB RAM** for large graphs

---

## Quick Links

- **Full README**: [`xroute-mvp/README.md`](xroute-mvp/README.md)
- **Quick Start**: Docker or manual setup instructions
- **API Docs**: After running backend, visit `http://localhost:8000/docs`
- **Contact**: vaibhavhariram@berkeley.edu

---

Start with [`xroute-mvp/README.md`](xroute-mvp/README.md) — it has everything you need!
