import networkx as nx
import numpy as np

from multipath_eval.algorithms import disjoint, maxflow
from multipath_eval.algorithms2 import ALGORITHMS2, disjoint_mincost, ksp_wcmp, mincost_maxflow, node_disjoint
from multipath_eval.failures import draw_independent, draw_regional
from multipath_eval.metrics import _edges


def _grid(seed=0):
    g = nx.grid_2d_graph(4, 4)
    g = nx.convert_node_labels_to_integers(g)
    rng = np.random.default_rng(seed)
    for u, v in g.edges():
        g.edges[u, v].update(cost=float(rng.uniform(1, 9)), capacity=float(rng.integers(1, 6)), delay=1.0, fail=0.03)
    for n in g.nodes():
        g.nodes[n].update(Latitude=50 + (n // 4) * 0.5, Longitude=10 + (n % 4) * 0.5)
    return g


def _cost(g, res):
    return sum(s * sum(g.edges[e]["cost"] for e in zip(p, p[1:])) for p, s in zip(res.paths, res.split))


def test_mincost_maxflow_same_capacity_lower_or_equal_cost():
    g = _grid()
    a, b = maxflow(g, 0, 15, 3), mincost_maxflow(g, 0, 15, 3)
    cap = lambda r: min(g.edges[e]["capacity"] / sum(s for p, s in zip(r.paths, r.split) if e in zip(p, p[1:]) or e[::-1] in zip(p, p[1:])) for p in r.paths for e in zip(p, p[1:]))
    assert abs(cap(a) - cap(b)) < 1e-6 or cap(b) >= cap(a) - 1e-6
    assert _cost(g, b) <= _cost(g, a) + 1e-9


def test_disjoint_mincost_is_disjoint_and_not_costlier():
    g = _grid(1)
    a, b = disjoint(g, 0, 15, 3), disjoint_mincost(g, 0, 15, 3)
    edges = [frozenset(e) for p in b.paths for e in zip(p, p[1:])]
    assert len(edges) == len(set(edges))
    assert len(b.paths) >= len(a.paths) - 0
    if len(a.paths) == len(b.paths):
        assert _cost(g, b) <= _cost(g, a) + 1e-9


def test_all_algorithms_return_valid_splits():
    g = _grid(2)
    for name, fn in ALGORITHMS2.items():
        r = fn(g, 0, 15, 3)
        assert r is not None and abs(sum(r.split) - 1) < 1e-9, name
        for p in r.paths:
            assert p[0] == 0 and p[-1] == 15 and all(g.has_edge(u, v) for u, v in zip(p, p[1:]))


def test_wcmp_split_follows_bottleneck():
    g = _grid(3)
    r = ksp_wcmp(g, 0, 15, 3)
    caps = np.array([min(g.edges[e]["capacity"] for e in zip(p, p[1:])) for p in r.paths])
    assert np.allclose(np.array(r.split), caps / caps.sum())


def test_regional_failures_match_marginal_and_are_correlated():
    g = _grid(4)
    probs = np.full(g.number_of_edges(), 0.05)
    rng = np.random.default_rng(0)
    F, info = draw_regional(g, probs, 6000, rng, radius_km=(20.0, 80.0), pool=400)
    assert abs(F.mean() - 0.05) < 0.01
    Fi = draw_independent(probs, 6000, np.random.default_rng(1))
    both = lambda M: float((M[:, 0] & M[:, 1]).mean())          # adjacent links 0 and 1
    assert max(both(F[:, :]), both(F[:, [1, 0]])) >= both(Fi)
