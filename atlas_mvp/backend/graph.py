"""
Graph loading and caching for Berkeley road network.
Uses OSMnx to download drivable roads; caches to graph.graphml for fast subsequent runs.
"""
from pathlib import Path

import networkx as nx
import osmnx as ox

GRAPH_PATH = Path(__file__).resolve().parent / "data" / "graph.graphml"
PLACE = "Berkeley, California, USA"


def get_graph() -> nx.MultiDiGraph:
    """
    Load Berkeley road graph from cache if exists; otherwise download and save.
    Adds edge speeds and travel times via OSMnx.
    """
    data_dir = GRAPH_PATH.parent
    data_dir.mkdir(parents=True, exist_ok=True)

    if GRAPH_PATH.exists():
        G = ox.load_graphml(str(GRAPH_PATH))
        # Ensure travel times exist (they're saved in graphml)
        first_edge = next(iter(G.edges(data=True)), None)
        if first_edge is not None:
            # MultiDiGraph edges(data=True) -> (u, v, key, data); data is last
            edge_data = first_edge[-1]
            if not isinstance(edge_data, dict) or "travel_time" not in edge_data:
                G = ox.add_edge_speeds(G)
                G = ox.add_edge_travel_times(G)
        return G

    G = ox.graph_from_place(PLACE, network_type="drive")
    G = ox.add_edge_speeds(G)
    G = ox.add_edge_travel_times(G)
    ox.save_graphml(G, str(GRAPH_PATH))
    return G
