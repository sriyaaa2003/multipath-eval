"""Additional routing algorithms (v2).

The first five (algorithms.py) are the textbook baselines. These five fix known weaknesses of them:

* ``disjoint_mincost``  the k edge-disjoint paths of *least total cost* (min-cost flow, the Suurballe/Bhandari idea). The baseline
  ``disjoint`` takes whichever disjoint paths a max-flow finds first, which can be much longer than necessary.
* ``node_disjoint``     k node-disjoint paths (survive router failures, not only link failures).
* ``mincost_maxflow``   among all maximum flows, the cheapest one. The baseline ``maxflow`` ignores cost entirely.
* ``ksp_wcmp``          k shortest paths with traffic split in proportion to each path's bottleneck capacity (weighted ECMP).
* ``geo_diverse``       k paths chosen one at a time, each avoiding the *neighbourhood* of the paths already chosen, so the paths
  do not share a conduit, a trench or a city. Needs node coordinates; without them it falls back to link-disjointness.
"""
from __future__ import annotations

from itertools import islice
from typing import Callable

import networkx as nx
import numpy as np

from .algorithms import EPS, RoutingResult, _equal, _find_path, ksp
from .topologies import haversine_km

SCALE = 1000          # integer scaling for network-simplex (it needs integer costs and capacities)


def _bottleneck(g: nx.Graph, path) -> float:
    return min(g.edges[e]["capacity"] for e in zip(path, path[1:]))


def ksp_wcmp(g: nx.Graph, src, dst, k: int) -> RoutingResult | None:
    try:
        paths = [tuple(p) for p in islice(nx.shortest_simple_paths(g, src, dst, weight="cost"), k)]
    except nx.NetworkXNoPath:
        return None
    caps = np.array([_bottleneck(g, p) for p in paths])
    return RoutingResult(tuple(paths), tuple((caps / caps.sum()).tolist()))


def node_disjoint(g: nx.Graph, src, dst, k: int) -> RoutingResult | None:
    try:
        if g.has_edge(src, dst):
            # networkx needs a non-adjacent pair; route the direct link plus disjoint paths in the graph without it
            h = g.copy()
            h.remove_edge(src, dst)
            extra = list(islice(nx.node_disjoint_paths(h, src, dst), k - 1)) if k > 1 and nx.has_path(h, src, dst) else []
            return _equal([(src, dst)] + extra)
        return _equal(islice(nx.node_disjoint_paths(g, src, dst), k))
    except nx.NetworkXNoPath:
        return None


def _flow_paths(g: nx.Graph, src, dst, flow_dict) -> RoutingResult | None:
    net = {}
    for u, nbrs in flow_dict.items():
        for v, f in nbrs.items():
            d = f - flow_dict.get(v, {}).get(u, 0)
            if d > 0:
                net[(u, v)] = d
    paths, amounts = [], []
    while True:
        path = _find_path(net, src, dst)
        if path is None:
            break
        edges = list(zip(path, path[1:]))
        b = min(net[e] for e in edges)
        for e in edges:
            net[e] -= b
            if net[e] <= 0:
                del net[e]
        paths.append(tuple(path))
        amounts.append(b)
    if not paths:
        return None
    tot = float(sum(amounts))
    return RoutingResult(tuple(paths), tuple(a / tot for a in amounts))


def _digraph(g: nx.Graph, cap: Callable[[dict], int], cost: Callable[[dict], int]) -> nx.DiGraph:
    d = nx.DiGraph()
    for u, v, data in g.edges(data=True):
        for a, b in ((u, v), (v, u)):
            d.add_edge(a, b, capacity=cap(data), weight=cost(data))
    return d


def mincost_maxflow(g: nx.Graph, src, dst, k: int) -> RoutingResult | None:
    d = _digraph(g, lambda e: max(int(round(e["capacity"] * SCALE)), 1), lambda e: int(round(e["cost"] * SCALE)))
    try:
        flow = nx.max_flow_min_cost(d, src, dst)
    except nx.NetworkXUnfeasible:
        return None
    return _flow_paths(g, src, dst, flow)


def disjoint_mincost(g: nx.Graph, src, dst, k: int) -> RoutingResult | None:
    """Up to k edge-disjoint paths with least total cost: min-cost flow of value k on unit capacities."""
    d = _digraph(g, lambda e: 1, lambda e: int(round(e["cost"] * SCALE)))
    best = None
    for kk in range(k, 0, -1):
        h = d.copy()
        h.add_node(src, demand=-kk)
        h.add_node(dst, demand=kk)
        try:
            flow = nx.min_cost_flow(h)
        except nx.NetworkXUnfeasible:
            continue
        best = _flow_paths(g, src, dst, flow)
        if best is not None:
            break
    return best


def _midpoint(g: nx.Graph, u, v):
    a, b = g.nodes[u], g.nodes[v]
    if all(key in n for n in (a, b) for key in ("Latitude", "Longitude")):
        return (a["Latitude"] + b["Latitude"]) / 2, (a["Longitude"] + b["Longitude"]) / 2
    return None


def geo_diverse(g: nx.Graph, src, dst, k: int, buffer_km: float = 150.0, penalty: float = 6.0) -> RoutingResult | None:
    """Greedy geographically diverse paths. After each path is chosen, every link whose midpoint lies within ``buffer_km`` of any
    link of the chosen paths has its cost multiplied by ``penalty`` for the next search; links of chosen paths are removed."""
    mids = {frozenset(e): _midpoint(g, *e) for e in g.edges()}
    h = g.copy()
    for u, v in h.edges():
        h.edges[u, v]["w"] = g.edges[u, v]["cost"]
    chosen: list = []
    for _ in range(k):
        try:
            p = tuple(nx.shortest_path(h, src, dst, weight="w"))
        except nx.NetworkXNoPath:
            break
        chosen.append(p)
        used = [mids[frozenset(e)] for e in zip(p, p[1:])]
        used = [m for m in used if m is not None]
        h.remove_edges_from(list(zip(p, p[1:])))
        for u, v in h.edges():
            m = mids[frozenset((u, v))]
            if m is not None and any(haversine_km(m[0], m[1], c[0], c[1]) < buffer_km for c in used):
                h.edges[u, v]["w"] = g.edges[u, v]["cost"] * penalty
    return _equal(chosen) if chosen else None


ALGORITHMS2: dict[str, Callable] = {
    "disjoint_mincost": disjoint_mincost,
    "node_disjoint": node_disjoint,
    "mincost_maxflow": mincost_maxflow,
    "ksp_wcmp": ksp_wcmp,
    "geo_diverse": geo_diverse,
}
