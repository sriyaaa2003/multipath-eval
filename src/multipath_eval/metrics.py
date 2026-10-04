"""Per-demand metrics of a split path set: cost, delay, capacity, outage probability, expected loss."""

from __future__ import annotations

from dataclasses import dataclass

import networkx as nx
import numpy as np

from .algorithms import RoutingResult


@dataclass(frozen=True)
class Metrics:
    cost: float
    delay: float
    capacity: float
    outage: float
    expected_loss: float


def _edges(path) -> list:
    return [frozenset(e) for e in zip(path, path[1:])]


def edge_index(g: nx.Graph) -> dict:
    return {frozenset(e): i for i, e in enumerate(g.edges())}


def draw_failures(g: nx.Graph, fail_scale: float, n: int, rng: np.random.Generator):
    """Boolean matrix (n draws x edges) of failed edges, shared by all algorithms of a scenario."""
    probs = np.array([min(g.edges[e]["fail"] * fail_scale, 0.5) for e in g.edges()])
    return rng.random((n, len(probs))) < probs, probs


def evaluate(g: nx.Graph, res: RoutingResult, index: dict, failures: np.ndarray, probs: np.ndarray) -> Metrics:
    cost = delay = loss = 0.0
    load: dict = {}
    path_failed = []
    for path, share in zip(res.paths, res.split):
        edges = _edges(path)
        cost += share * sum(g.edges[tuple(e)]["cost"] for e in edges)
        delay += share * sum(g.edges[tuple(e)]["delay"] for e in edges)
        idx = [index[e] for e in edges]
        survive = float(np.prod(1.0 - probs[idx]))
        loss += share * (1.0 - survive)
        for e in edges:
            load[e] = load.get(e, 0.0) + share
        path_failed.append(failures[:, idx].any(axis=1))
    capacity = min(g.edges[tuple(e)]["capacity"] / ld for e, ld in load.items())
    outage = float(np.logical_and.reduce(path_failed).mean())
    return Metrics(cost, delay, capacity, outage, loss)
