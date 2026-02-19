"""
Routing logic: nearest-node lookup and shortest-path computation.
Supports A*, Dijkstra, and Contraction Hierarchies (CH).
"""
import math
from typing import Optional

import networkx as nx
import osmnx as ox

from ch import get_ch, query as ch_query, unpack_path as ch_unpack_path

# m/s (~50 km/h) for heuristic and fallback travel time from length
DEFAULT_SPEED_MPS = 13.9


def haversine_m(node_a: tuple, node_b: tuple) -> float:
    """Approximate straight-line distance in meters between (lat, lon) pairs."""
    lat1, lon1 = node_a
    lat2, lon2 = node_b
    R = 6_371_000  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def heuristic_func(u, v, G: nx.MultiDiGraph) -> float:
    """
    A* heuristic: straight-line distance / speed.
    Returns travel time (seconds) as lower bound.
    """
    try:
        u_data = G.nodes[u]
        v_data = G.nodes[v]
        lat1 = u_data.get("y") or u_data.get("lat")
        lon1 = u_data.get("x") or u_data.get("lon")
        lat2 = v_data.get("y") or v_data.get("lat")
        lon2 = v_data.get("x") or v_data.get("lon")
        if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
            return 0.0
        dist_m = haversine_m((lat1, lon1), (lat2, lon2))
        return dist_m / DEFAULT_SPEED_MPS
    except (KeyError, TypeError):
        return 0.0


def _weight_key(profile: str) -> str:
    return "travel_time"


def _edge_weight_sec(d: dict, weight_key: str) -> float:
    """
    Edge weight in seconds. Fallback: travel_time -> length/speed -> 1.0.
    Ensures routing works even if some edges lack speed/travel_time.
    """
    w = d.get(weight_key)
    if w is not None and w != "":
        try:
            return float(w)
        except (TypeError, ValueError):
            pass
    w = d.get("travel_time")
    if w is not None and w != "":
        try:
            return float(w)
        except (TypeError, ValueError):
            pass
    length = d.get("length")
    if length is not None and length != "":
        try:
            return float(length) / DEFAULT_SPEED_MPS
        except (TypeError, ValueError):
            pass
    return 1.0


def _best_edge(G: nx.MultiDiGraph, u: int, v: int, weight_key: str) -> tuple:
    """
    Choose the best edge between u and v when multiple edges exist.
    Returns (u, v, key) with minimum weight.
    """
    edges = [(e[0], e[1], e[2], e[3]) for e in G.edges(keys=True, data=True) if e[0] == u and e[1] == v]
    if not edges:
        raise ValueError(f"No edge between {u} and {v}")
    best = min(edges, key=lambda e: _edge_weight_sec(e[3], weight_key))
    return (best[0], best[1], best[2])


def _to_digraph_with_profile(G: nx.MultiDiGraph, profile: str) -> nx.DiGraph:
    """
    Convert MultiDiGraph to DiGraph, choosing best edge per (u,v).
    """
    weight_key = _weight_key(profile)
    D = nx.DiGraph()
    for u in G.nodes():
        D.add_node(u, **dict(G.nodes[u]))
    for u, v in set((e[0], e[1]) for e in G.edges()):
        _, _, best_k = _best_edge(G, u, v, weight_key)
        d = dict(G[u][v][best_k])
        w = _edge_weight_sec(d, weight_key)
        D.add_edge(u, v, weight=w, **d)
    return D


def _nearest_node(G: nx.MultiDiGraph, lon: float, lat: float):
    """
    Nearest node to (lon, lat). Uses OSMnx if available; else haversine over all nodes.
    OSMnx convention: nearest_nodes(G, X, Y) with X=longitude, Y=latitude.
    """
    try:
        return ox.nearest_nodes(G, lon, lat)
    except ImportError:
        pass
    best_node = None
    best_d = float("inf")
    for n in G.nodes():
        d = G.nodes[n]
        ny = d.get("y") or d.get("lat")
        nx_ = d.get("x") or d.get("lon")
        if ny is None or nx_ is None:
            continue
        dist = haversine_m((lat, lon), (ny, nx_))
        if dist < best_d:
            best_d = dist
            best_node = n
    if best_node is None:
        raise ValueError("Graph has no nodes with coordinates")
    return best_node


def route(
    G: nx.MultiDiGraph,
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
    algo: str = "astar",
    profile: str = "baseline",
) -> tuple[list[tuple[float, float]], float, float, int]:
    """
    Compute route from (origin_lat, origin_lon) to (dest_lat, dest_lon).
    Returns (line_coords, distance_m, eta_sec, n_nodes).
    line_coords: list of (lon, lat) for GeoJSON LineString.
    """
    # X = longitude, Y = latitude
    orig_node = _nearest_node(G, origin_lon, origin_lat)
    dest_node = _nearest_node(G, dest_lon, dest_lat)

    print(f"[route] graph_nodes={G.number_of_nodes()}, origin_node={orig_node}, dest_node={dest_node}")

    weight_key = _weight_key(profile)
    D = _to_digraph_with_profile(G, profile)

    if algo == "ch":
        levels, forward_adj, backward_adj, shortcuts = get_ch(profile, D)
        dist_ch, path_edges = ch_query(levels, forward_adj, backward_adj, shortcuts, orig_node, dest_node)
        if dist_ch == float("inf") or not path_edges:
            path = []
        else:
            path = ch_unpack_path(path_edges, shortcuts)
        if not path:
            # No path found (disconnected); fall back to empty path / single node
            path = [orig_node]
    elif algo == "astar":
        # Temporarily use zero heuristic for reliability (admissible, Dijkstra-like)
        path = nx.astar_path(D, orig_node, dest_node, heuristic=lambda u, v: 0.0, weight="weight")
    else:
        path = nx.shortest_path(D, orig_node, dest_node, weight="weight")

    line_coords = []
    distance_m = 0.0
    travel_time_sec = 0.0

    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        try:
            best_u, best_v, best_k = _best_edge(G, u, v, weight_key)
        except ValueError:
            continue
        edge_data = G[best_u][best_v][best_k]
        length = edge_data.get("length")
        length_m = float(length) if length is not None and length != "" else 0.0
        tt = _edge_weight_sec(edge_data, weight_key)
        distance_m += length_m
        travel_time_sec += tt

        node_data = G.nodes[v]
        lat = node_data.get("y") or node_data.get("lat")
        lon = node_data.get("x") or node_data.get("lon")
        if lat is not None and lon is not None:
            line_coords.append((float(lon), float(lat)))

    # Include origin point
    orig_data = G.nodes[orig_node]
    olat = orig_data.get("y") or orig_data.get("lat")
    olon = orig_data.get("x") or orig_data.get("lon")
    if olat is not None and olon is not None:
        line_coords.insert(0, (float(olon), float(olat)))

    print(f"[route] path_length={len(path)}")
    return (line_coords, distance_m, travel_time_sec, len(path))
