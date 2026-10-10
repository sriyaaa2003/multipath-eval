"""Loader for Internet Topology Zoo networks (GML or GraphML) and edge attribute assignment."""

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


def load_network(path: str | Path) -> nx.Graph:
    """Load a Topology Zoo GML or GraphML file as a simple connected undirected graph."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"topology file not found: {path}")
    if path.suffix.lower() == ".graphml":
        raw = nx.read_graphml(path)
    else:
        text = path.read_text(encoding="utf-8", errors="replace")
        if "multigraph" not in text:  # some Zoo files list parallel links; read them as a multigraph
            text = text.replace("graph [", "graph [ multigraph 1", 1)
        raw = nx.parse_gml(text, label="id")
    simple = nx.Graph()
    simple.add_nodes_from(raw.nodes(data=True))
    for u, v, data in raw.edges(data=True):
        if u == v:
            continue
        if not simple.has_edge(u, v):
            simple.add_edge(u, v, **data)
    return _largest_component(simple)


def has_coordinates(g: nx.Graph, share: float = 0.95) -> bool:
    ok = sum(1 for _, d in g.nodes(data=True) if "Latitude" in d and "Longitude" in d)
    return ok >= share * g.number_of_nodes()


def build_topology(spec: TopologySpec, base_dir: Path) -> nx.Graph:
    if spec.family != "gml":  # pragma: no cover - validated in config
        raise ValueError(spec.family)
    return load_network(base_dir / spec.params["path"])


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
    """Set cost, delay, capacity and fail on every edge from the real network.

    Delay is distance / propagation speed. Cost and failure probability are proportional to link length
    (longer fibre costs more and is cut more often), scaled so that the mean over the network equals the
    midpoint of the configured range. Capacity is the published link speed where the file has one and a
    sample from the configured range otherwise. Returns counts of real versus sampled delay and capacity.
    """
    used = {"delay_real": 0, "capacity_real": 0, "edges": g.number_of_edges()}
    km = {}
    for u, v in g.edges():
        a, b = g.nodes[u], g.nodes[v]
        if all(key in n for n in (a, b) for key in ("Latitude", "Longitude")):
            km[(u, v)] = max(haversine_km(a["Latitude"], a["Longitude"], b["Latitude"], b["Longitude"]), 1.0)
    mean_km = float(np.mean(list(km.values()))) if km else 1.0
    cost_mid = (cfg.cost.low + cfg.cost.high) / 2
    fail_mid = (cfg.fail_prob.low + cfg.fail_prob.high) / 2

    for u, v, data in g.edges(data=True):
        if (u, v) in km:
            rel = km[(u, v)] / mean_km
            data["cost"] = cost_mid * rel
            data["fail"] = min(fail_mid * rel, 0.5)
            data["delay"] = max(km[(u, v)] / cfg.km_per_ms, cfg.min_delay_ms)
            used["delay_real"] += 1
        else:
            data["cost"] = float(rng.uniform(cfg.cost.low, cfg.cost.high))
            data["fail"] = float(rng.uniform(cfg.fail_prob.low, cfg.fail_prob.high))
            data["delay"] = float(rng.uniform(cfg.delay_ms.low, cfg.delay_ms.high))

        speed = _speed_gbps(data)
        if speed is not None:
            data["capacity"] = speed
            used["capacity_real"] += 1
        else:
            data["capacity"] = float(rng.uniform(cfg.capacity.low, cfg.capacity.high))
    return used
