"""Routing algorithms. Each returns a RoutingResult or None when the pair cannot be routed."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import islice
from typing import Callable

import networkx as nx

EPS = 1e-9


@dataclass(frozen=True)
class RoutingResult:
    paths: tuple  # tuple of tuples of nodes
    split: tuple  # fractions, one per path, summing to 1


def _equal(paths) -> RoutingResult | None:
    paths = [tuple(p) for p in paths]
    if not paths:
        return None
    return RoutingResult(tuple(paths), tuple(1.0 / len(paths) for _ in paths))


def shortest(g: nx.Graph, src, dst, k: int) -> RoutingResult | None:
    """Baseline: a single least-cost path."""
    try:
        return _equal([nx.shortest_path(g, src, dst, weight="cost")])
    except nx.NetworkXNoPath:
        return None


def ksp(g: nx.Graph, src, dst, k: int) -> RoutingResult | None:
    """The k least-cost loopless paths (Yen), traffic split equally."""
    try:
        return _equal(islice(nx.shortest_simple_paths(g, src, dst, weight="cost"), k))
    except nx.NetworkXNoPath:
        return None


def disjoint(g: nx.Graph, src, dst, k: int) -> RoutingResult | None:
    """Up to k edge-disjoint paths, traffic split equally."""
    try:
        return _equal(islice(nx.edge_disjoint_paths(g, src, dst), k))
    except nx.NetworkXNoPath:
        return None


def ecmp(g: nx.Graph, src, dst, k: int) -> RoutingResult | None:
    """Equal-cost multipath: all least-hop paths (capped at k), traffic split equally."""
    try:
        return _equal(islice(nx.all_shortest_paths(g, src, dst), k))
    except nx.NetworkXNoPath:
        return None


def maxflow(g: nx.Graph, src, dst, k: int) -> RoutingResult | None:
    """Maximum flow on edge capacities, decomposed into paths; split proportional to path flow."""
    value, flow = nx.maximum_flow(g, src, dst, capacity="capacity")
    if value <= EPS:
        return None
    net = {}
    for u, nbrs in flow.items():
        for v, f in nbrs.items():
            d = f - flow.get(v, {}).get(u, 0.0)
            if d > EPS:
                net[(u, v)] = d
    paths, amounts = [], []
    while True:
        path = _find_path(net, src, dst)
        if path is None:
            break
        edges = list(zip(path, path[1:]))
        bottleneck = min(net[e] for e in edges)
        for e in edges:
            net[e] -= bottleneck
            if net[e] <= EPS:
                del net[e]
        paths.append(tuple(path))
        amounts.append(bottleneck)
    if not paths:
        return None
    total = sum(amounts)
    return RoutingResult(tuple(paths), tuple(a / total for a in amounts))


def _find_path(net: dict, src, dst):
    adj: dict = {}
    for (u, v) in net:
        adj.setdefault(u, []).append(v)
    stack, seen = [(src, [src])], {src}
    while stack:
        node, path = stack.pop()
        if node == dst:
            return path
        for nxt in adj.get(node, []):
            if nxt not in seen:
                seen.add(nxt)
                stack.append((nxt, path + [nxt]))
    return None


ALGORITHMS: dict[str, Callable] = {
    "shortest": shortest,
    "ksp": ksp,
    "disjoint": disjoint,
    "ecmp": ecmp,
    "maxflow": maxflow,
}
