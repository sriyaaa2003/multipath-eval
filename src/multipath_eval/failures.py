"""Failure models with identical per-link failure probabilities but different correlation.

``independent``  every link fails on its own with its probability p_e (the v1 model).
``regional``     a regional event (storm, flood, power cut, dig) with a random centre on the network and a random radius
                 knocks out every link that passes within the radius. The event rate is chosen so that the *average* link
                 failure probability equals that of the independent model, so any change in algorithm ranking between the two
                 models is due to correlation alone, not to links failing more often.
Links without coordinates fail independently in both models.
"""
from __future__ import annotations

import networkx as nx
import numpy as np

from .topologies import haversine_km


def _edge_points(g: nx.Graph):
    pts = []
    for u, v in g.edges():
        a, b = g.nodes[u], g.nodes[v]
        if all(key in n for n in (a, b) for key in ("Latitude", "Longitude")):
            pts.append([(a["Latitude"], a["Longitude"]), ((a["Latitude"] + b["Latitude"]) / 2, (a["Longitude"] + b["Longitude"]) / 2),
                        (b["Latitude"], b["Longitude"])])
        else:
            pts.append(None)
    return pts


def draw_independent(probs: np.ndarray, n: int, rng: np.random.Generator) -> np.ndarray:
    return rng.random((n, len(probs))) < probs


def draw_regional(g: nx.Graph, probs: np.ndarray, n: int, rng: np.random.Generator, radius_km=(30.0, 150.0), pool: int = 1500):
    """Returns (failures [n, E] bool, info). Marginal failure probability matches ``probs`` on average (see module docstring)."""
    pts = _edge_points(g)
    E = len(pts)
    geo = np.array([p is not None for p in pts])
    if geo.sum() < 3:
        return draw_independent(probs, n, rng), {"lambda": 0.0, "geo_edges": int(geo.sum())}
    centers = [pts[i][1] for i in np.flatnonzero(geo)]
    # coverage matrix of single events: pool x E
    cov = np.zeros((pool, E), bool)
    for j in range(pool):
        c = centers[rng.integers(len(centers))]
        r = rng.uniform(*radius_km)
        for i in np.flatnonzero(geo):
            if min(haversine_km(c[0], c[1], p[0], p[1]) for p in pts[i]) < r:
                cov[j, i] = True
    h = cov.mean(axis=0)
    target = float(probs[geo].mean())

    def marginal(lam):
        return float((1.0 - np.exp(-lam * h[geo])).mean())

    lo, hi = 0.0, 50.0
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if marginal(mid) < target else (lo, mid)
    lam = (lo + hi) / 2
    n_ev = rng.poisson(lam, size=n)
    out = np.zeros((n, E), bool)
    for d in np.flatnonzero(n_ev):
        out[d] |= cov[rng.integers(0, pool, size=n_ev[d])].any(axis=0)
    ind = np.flatnonzero(~geo)
    if len(ind):
        out[:, ind] = rng.random((n, len(ind))) < probs[ind]
    return out, {"lambda": float(lam), "geo_edges": int(geo.sum()), "marginal_geo": marginal(lam), "target": target}
