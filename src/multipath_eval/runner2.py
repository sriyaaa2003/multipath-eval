"""v2 experiment: ten algorithms, two failure models with matched marginals, served-traffic metric."""
from __future__ import annotations

import itertools
import time

import numpy as np
import pandas as pd

from .algorithms import ALGORITHMS
from .algorithms2 import ALGORITHMS2
from .config import Config
from .failures import draw_independent, draw_regional
from .metrics import _edges, edge_index
from .topologies import assign_attributes, build_topology

ALL = {**ALGORITHMS, **ALGORITHMS2}


def metrics_from_draws(g, res, index, F):
    cost = delay = 0.0
    load, alive = {}, []
    for path, share in zip(res.paths, res.split):
        edges = _edges(path)
        cost += share * sum(g.edges[tuple(e)]["cost"] for e in edges)
        delay += share * sum(g.edges[tuple(e)]["delay"] for e in edges)
        idx = [index[e] for e in edges]
        for e in edges:
            load[e] = load.get(e, 0.0) + share
        alive.append(~F[:, idx].any(axis=1))
    capacity = min(g.edges[tuple(e)]["capacity"] / ld for e, ld in load.items())
    alive = np.stack(alive, axis=1)                         # draws x paths
    outage = float((~alive.any(axis=1)).mean())
    served = float((alive * np.array(res.split)).sum(axis=1).mean())
    return cost, delay, capacity, outage, served


def run_v2(cfg: Config, log=print) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows, nets = [], []
    t0 = time.time()
    for t_idx, spec in enumerate(cfg.topologies):
        rng = np.random.default_rng([cfg.seed, t_idx, 0])
        g = build_topology(spec, cfg.base_dir)
        assign_attributes(g, cfg, rng)
        nodes = list(g.nodes())
        pairs = list(itertools.permutations(nodes, 2))
        demands = [pairs[i] for i in rng.permutation(len(pairs))[: cfg.demands]]
        index = edge_index(g)
        routed = []
        for src, dst in demands:
            res = {}
            for name, fn in ALL.items():
                try:
                    res[name] = fn(g, src, dst, cfg.k)
                except Exception:                                   # a failed solver is a missing result, never a silent zero
                    res[name] = None
            if any(r is None for r in res.values()):
                continue
            routed.append(((src, dst), res))
        probs0 = np.array([min(g.edges[e]["fail"], 0.5) for e in g.edges()])
        nets.append({"topology": spec.name, "nodes": g.number_of_nodes(), "edges": g.number_of_edges(), "demands": len(routed),
                     "density": 2 * g.number_of_edges() / max(g.number_of_nodes() * (g.number_of_nodes() - 1), 1)})
        for s_idx, setting in enumerate(cfg.settings):
            probs = np.minimum(probs0 * setting.fail_scale, 0.5)
            mc = np.random.default_rng([cfg.seed, t_idx, s_idx, 99])
            F_ind = draw_independent(probs, cfg.mc_draws, mc)
            F_reg, info = draw_regional(g, probs, cfg.mc_draws, np.random.default_rng([cfg.seed, t_idx, s_idx, 7]))
            for model, F in (("independent", F_ind), ("regional", F_reg)):
                for (src, dst), res in routed:
                    for name, r in res.items():
                        c, d, cap, out, srv = metrics_from_draws(g, r, index, F)
                        rows.append({"topology": spec.name, "setting": setting.name, "fail_model": model, "src": src, "dst": dst,
                                     "algorithm": name, "n_paths": len(r.paths), "cost": c, "delay": d, "capacity": cap, "outage": out,
                                     "served": srv, "marginal_fail": float(F.mean())})
        if (t_idx + 1) % 10 == 0:
            log(f"{t_idx + 1}/{len(cfg.topologies)} networks, {time.time() - t0:.0f}s")
    return pd.DataFrame(rows), pd.DataFrame(nets)
