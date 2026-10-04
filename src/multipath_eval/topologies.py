"""Topology generators, a GML loader and seeded edge attribute assignment."""

from __future__ import annotations

import math
from pathlib import Path

import networkx as nx
import numpy as np

from .config import Config, TopologySpec

_UNIT_TO_GBPS = {"K": 1e-6, "M": 1e-3, "G": 1.0, "T": 1e3}


def _largest_component(g: nx.Graph) -> nx.Graph:
    if nx.is_connected(g):
        return g
    nodes = max(nx.connected_components(g), key=len)
    return g.subgraph(nodes).copy()


def load_gml(path: str | Path) -> nx.Graph:
    """Load a Topology Zoo style GML file as a simple connected undirected graph."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"GML file not found: {path}")
    raw = nx.read_gml(path, label="id")
    simple = nx.Graph()
    simple.add_nodes_from(raw.nodes(data=True))
    for u, v, data in raw.edges(data=True):
        if u == v:
            continue
        if not simple.has_edge(u, v):
            simple.add_edge(u, v, **data)
    return _largest_component(simple)


def build_topology(spec: TopologySpec, seed: int, base_dir: Path, rng: np.random.Generator) -> nx.Graph:
    p = spec.params
    if spec.family == "erdos_renyi":
        g = nx.gnp_random_graph(int(p["nodes"]), float(p["p"]), seed=int(rng.integers(2**31)))
        g = _largest_component(g)
    elif spec.family == "grid":
        g = nx.convert_node_labels_to_integers(nx.grid_2d_graph(int(p["rows"]), int(p["cols"])))
    elif spec.family == "barabasi_albert":
        g = nx.barabasi_albert_graph(int(p["nodes"]), int(p["m"]), seed=int(rng.integers(2**31)))
    elif spec.family == "gml":
        g = load_gml(base_dir / p["path"])
    else:  # pragma: no cover - validated in config
        raise ValueError(spec.family)
    return nx.Graph(g)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _speed_gbps(data: dict) -> float | None:
    speed = data.get("LinkSpeed")
    if speed is None:
        return None
    try:
        value = float(speed)
    except (TypeError, ValueError):
        return None
    unit = str(data.get("LinkSpeedUnits", "G")).upper()[:1]
    factor = _UNIT_TO_GBPS.get(unit)
    return value * factor if factor and value > 0 else None


def assign_attributes(g: nx.Graph, cfg: Config, rng: np.random.Generator) -> dict:
    """Set cost, delay, capacity and fail on every edge. Real GML values are used when present.

    Returns counts of how many edges got real versus sampled delay and capacity.
    """
    used = {"delay_real": 0, "capacity_real": 0, "edges": g.number_of_edges()}
    for u, v, data in g.edges(data=True):
        data["cost"] = float(rng.uniform(cfg.cost.low, cfg.cost.high))
        data["fail"] = float(rng.uniform(cfg.fail_prob.low, cfg.fail_prob.high))

        a, b = g.nodes[u], g.nodes[v]
        if all(key in n for n in (a, b) for key in ("Latitude", "Longitude")):
            km = haversine_km(a["Latitude"], a["Longitude"], b["Latitude"], b["Longitude"])
            data["delay"] = max(km / cfg.km_per_ms, cfg.min_delay_ms)
            used["delay_real"] += 1
        else:
            data["delay"] = float(rng.uniform(cfg.delay_ms.low, cfg.delay_ms.high))

        speed = _speed_gbps(data)
        if speed is not None:
            data["capacity"] = speed
            used["capacity_real"] += 1
        else:
            data["capacity"] = float(rng.uniform(cfg.capacity.low, cfg.capacity.high))
    return used
