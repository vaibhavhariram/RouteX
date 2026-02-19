"""
Contraction Hierarchies: preprocessing and query.
Preprocess: assign contraction order, contract nodes (add shortcuts), build upward graphs.
Query: bidirectional Dijkstra on upward graphs, then unpack shortcuts to get path.
"""
import heapq
import json
import random
from pathlib import Path

import networkx as nx

DATA_DIR = Path(__file__).resolve().parent / "data"


def _contraction_order(D: nx.DiGraph, seed: int = 42) -> list:
    """Assign contraction order: random order (seeded for reproducibility)."""
    nodes = list(D.nodes())
    random.seed(seed)
    random.shuffle(nodes)
    return nodes


def _shortest_path_avoiding(D: nx.DiGraph, u: int, w: int, avoid: int, limit: float) -> float:
    """
    Shortest path from u to w in D without node avoid. Stops when distance exceeds limit.
    Returns distance or inf if no path or path > limit.
    """
    dist = {u: 0.0}
    heap = [(0.0, u)]
    while heap:
        d, x = heapq.heappop(heap)
        if x == w:
            return d
        if d > limit:
            return float("inf")
        if d > dist.get(x, float("inf")):
            continue
        for _, y, data in D.out_edges(x, data=True):
            if y == avoid:
                continue
            wt = float(data.get("weight", 1.0))
            new_d = d + wt
            if new_d > limit:
                continue
            if new_d < dist.get(y, float("inf")):
                dist[y] = new_d
                heapq.heappush(heap, (new_d, y))
    return float("inf")


def _contract_node(D: nx.DiGraph, v: int, order: dict) -> list:
    """
    Contract node v: for each (u,v) and (v,w), if shortest u->w without v > w(u,v)+w(v,w),
    add shortcut (u,w). Uses limited Dijkstra (stop when distance exceeds c) for speed.
    Returns list of shortcuts added: (u, w, weight, middle).
    """
    shortcuts = []
    in_edges = list(D.in_edges(v, data=True))
    out_edges = list(D.out_edges(v, data=True))
    if not in_edges or not out_edges:
        return shortcuts

    for (u, _, d_in) in in_edges:
        w_uv = float(d_in.get("weight", 1.0))
        for (_, w, d_out) in out_edges:
            w_vw = float(d_out.get("weight", 1.0))
            if u == w:
                continue
            c = w_uv + w_vw
            dist = _shortest_path_avoiding(D, u, w, v, c)
            if c < dist:
                shortcuts.append((u, w, c, v))
                if D.has_edge(u, w):
                    if c < D[u][w].get("weight", float("inf")):
                        D.add_edge(u, w, weight=c)
                else:
                    D.add_edge(u, w, weight=c)
    return shortcuts


def preprocess(D: nx.DiGraph, profile: str) -> tuple[dict, dict, dict, dict]:
    """
    Run CH preprocessing on digraph D (must have edge attribute 'weight').
    Returns (levels, forward_adj, backward_adj, shortcuts).
    - levels: node -> int (lower = contracted first)
    - forward_adj: node -> [(neighbor, weight), ...] (only edges to higher level)
    - backward_adj: node -> [(neighbor, weight), ...] (only edges to higher level in reverse)
    - shortcuts: (u, w) -> (weight, middle) for unpacking
    """
    order = _contraction_order(D)
    levels = {node: i for i, node in enumerate(order)}
    all_shortcuts = {}  # (u,w) -> (weight, middle)

    # Contract nodes in order (work on copy so we don't mutate original for upward build)
    D_work = D.copy()
    for v in order:
        for (u, w, weight, middle) in _contract_node(D_work, v, levels):
            key = (u, w)
            if key not in all_shortcuts or weight < all_shortcuts[key][0]:
                all_shortcuts[key] = (weight, middle)

    # Build upward graphs from D_work (original + shortcuts) and levels
    forward_adj = {n: [] for n in D_work.nodes()}
    backward_adj = {n: [] for n in D_work.nodes()}
    for (u, v, data) in D_work.edges(data=True):
        w = float(data.get("weight", 1.0))
        if levels[u] < levels[v]:
            forward_adj[u].append((v, w))
            backward_adj[v].append((u, w))

    return levels, forward_adj, backward_adj, all_shortcuts


def _dijkstra_upward(adj: dict, levels: dict, start: int, weight_attr: str = "weight") -> dict:
    """Run Dijkstra in the upward graph (only follow edges to higher level). Returns dist dict."""
    dist = {start: 0.0}
    # heap: (d, node)
    heap = [(0.0, start)]
    while heap:
        d, u = heapq.heappop(heap)
        if d > dist.get(u, float("inf")):
            continue
        for (v, w) in adj.get(u, []):
            if levels.get(v, -1) <= levels.get(u, -1):
                continue
            new_d = d + w
            if new_d < dist.get(v, float("inf")):
                dist[v] = new_d
                heapq.heappush(heap, (new_d, v))
    return dist


def _dijkstra_upward_with_parents(adj: dict, levels: dict, start: int, forward: bool = True) -> tuple[dict, dict]:
    """
    Run Dijkstra from start. forward=True: only go to higher level (forward search).
    forward=False: only go to lower level (backward search). Returns (dist, parent).
    """
    dist = {start: 0.0}
    parent = {}
    heap = [(0.0, start)]
    while heap:
        d, u = heapq.heappop(heap)
        if d > dist.get(u, float("inf")):
            continue
        for (v, w) in adj.get(u, []):
            if forward:
                if levels.get(v, -1) <= levels.get(u, -1):
                    continue
            else:
                if levels.get(v, -1) >= levels.get(u, -1):
                    continue
            new_d = d + w
            if new_d < dist.get(v, float("inf")):
                dist[v] = new_d
                parent[v] = u
                heapq.heappush(heap, (new_d, v))
    return dist, parent


def query(
    levels: dict,
    forward_adj: dict,
    backward_adj: dict,
    shortcuts: dict,
    origin: int,
    dest: int,
) -> tuple[float, list]:
    """
    CH query: bidirectional Dijkstra on upward graphs.
    Returns (distance, path_edges) where path_edges is list of (u, v) that may include shortcuts.
    """
    dist_f, parent_f = _dijkstra_upward_with_parents(forward_adj, levels, origin, forward=True)
    dist_b, parent_b = _dijkstra_upward_with_parents(backward_adj, levels, dest, forward=False)

    best_dist = float("inf")
    meeting = None
    for v in dist_f:
        if v in dist_b:
            d = dist_f[v] + dist_b[v]
            if d < best_dist:
                best_dist = d
                meeting = v
    if meeting is None:
        return float("inf"), []

    # Reconstruct edge sequence: origin -> ... -> meeting -> ... -> dest
    path_forward = []
    u = meeting
    while u in parent_f:
        p = parent_f[u]
        path_forward.append((p, u))
        u = p
    path_forward.reverse()

    path_backward = []
    u = meeting
    while u in parent_b:
        p = parent_b[u]
        path_backward.append((u, p))
        u = p

    path_edges = path_forward + path_backward
    return best_dist, path_edges


def unpack_path(path_edges: list, shortcuts: dict) -> list:
    """
    Replace shortcut edges by (u, middle, w). Returns list of original nodes.
    path_edges: list of (u, v). If (u,v) is a shortcut, expand to u, middle, v.
    """
    out = []
    for (u, v) in path_edges:
        if (u, v) in shortcuts:
            _, middle = shortcuts[(u, v)]
            out.extend(unpack_path([(u, middle), (middle, v)], shortcuts))
        else:
            if not out or out[-1] != u:
                out.append(u)
            out.append(v)
    # Deduplicate consecutive
    dedup = [out[0]] if out else []
    for i in range(1, len(out)):
        if out[i] != dedup[-1]:
            dedup.append(out[i])
    return dedup


def save_ch(profile: str, levels: dict, forward_adj: dict, backward_adj: dict, shortcuts: dict):
    """Persist CH data to data/ch_<profile>.json (simplified: adj as dict of list of [v, w])."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / f"ch_{profile}.json"
    # shortcuts: (u,w) -> [weight, middle] with keys as "u,w"
    shortcuts_ser = {f"{u},{w}": [weight, middle] for (u, w), (weight, middle) in shortcuts.items()}
    forward_ser = {str(k): [[v, w] for v, w in vlist] for k, vlist in forward_adj.items()}
    backward_ser = {str(k): [[v, w] for v, w in vlist] for k, vlist in backward_adj.items()}
    levels_ser = {str(k): v for k, v in levels.items()}
    with open(path, "w") as f:
        json.dump(
            {
                "levels": levels_ser,
                "forward_adj": forward_ser,
                "backward_adj": backward_ser,
                "shortcuts": shortcuts_ser,
            },
            f,
            indent=0,
        )


def get_ch(profile: str, D: nx.DiGraph) -> tuple[dict, dict, dict, dict]:
    """
    Get CH data for profile: load from disk if present, else preprocess (and save) then return.
    D must have edge attribute 'weight'.
    """
    loaded = load_ch(profile)
    if loaded is not None:
        return loaded
    levels, forward_adj, backward_adj, shortcuts = preprocess(D, profile)
    save_ch(profile, levels, forward_adj, backward_adj, shortcuts)
    return levels, forward_adj, backward_adj, shortcuts


def load_ch(profile: str) -> tuple[dict, dict, dict, dict] | None:
    """Load CH data from data/ch_<profile>.json. Returns (levels, forward_adj, backward_adj, shortcuts) or None."""
    path = DATA_DIR / f"ch_{profile}.json"
    if not path.exists():
        return None
    with open(path) as f:
        data = json.load(f)
    levels = {int(k): v for k, v in data["levels"].items()}
    forward_adj = {int(k): [(int(v), float(w)) for v, w in vlist] for k, vlist in data["forward_adj"].items()}
    backward_adj = {int(k): [(int(v), float(w)) for v, w in vlist] for k, vlist in data["backward_adj"].items()}
    shortcuts = {}
    for k, (weight, middle) in data["shortcuts"].items():
        u, w = k.split(",")
        shortcuts[(int(u), int(w))] = (float(weight), int(middle))
    return levels, forward_adj, backward_adj, shortcuts
