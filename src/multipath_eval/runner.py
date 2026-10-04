"""Runs the full experiment: topologies x settings x demands x algorithms."""

from __future__ import annotations

import itertools

import numpy as np
import pandas as pd

from .algorithms import ALGORITHMS
from .config import Config
from .metrics import draw_failures, edge_index, evaluate
from .topologies import assign_attributes, build_topology


def run_experiment(cfg: Config) -> tuple[pd.DataFrame, dict]:
    rows = []
    summary = {"instances": 0, "scenarios": 0, "skipped_demands": 0, "demands_evaluated": 0, "real_attributes": {}}

    for t_idx, spec in enumerate(cfg.topologies):
        for seed in range(spec.seeds):
            rng = np.random.default_rng([cfg.seed, t_idx, seed])
            g = build_topology(spec, seed, cfg.base_dir, rng)
            used = assign_attributes(g, cfg, rng)
            summary["instances"] += 1
            summary["real_attributes"][spec.name] = used

            nodes = list(g.nodes())
            pairs = [p for p in itertools.permutations(nodes, 2)]
            order = rng.permutation(len(pairs))[: cfg.demands]
            demands = [pairs[i] for i in order]
            index = edge_index(g)

            routed = []
            for src, dst in demands:
                results = {name: fn(g, src, dst, cfg.k) for name, fn in ALGORITHMS.items()}
                if any(r is None for r in results.values()):
                    summary["skipped_demands"] += 1
                    continue
                routed.append(((src, dst), results))
            summary["demands_evaluated"] += len(routed)

            for s_idx, setting in enumerate(cfg.settings):
                mc = np.random.default_rng([cfg.seed, t_idx, seed, s_idx, 99])
                failures, probs = draw_failures(g, setting.fail_scale, cfg.mc_draws, mc)
                scenario = f"{spec.name}#{seed}|{setting.name}"
                summary["scenarios"] += 1
                for (src, dst), results in routed:
                    for name, res in results.items():
                        m = evaluate(g, res, index, failures, probs)
                        rows.append(
                            {
                                "scenario": scenario,
                                "family": spec.family if spec.family != "gml" else "topology_zoo",
                                "topology": spec.name,
                                "setting": setting.name,
                                "src": src,
                                "dst": dst,
                                "algorithm": name,
                                "n_paths": len(res.paths),
                                "cost": m.cost,
                                "delay": m.delay,
                                "capacity": m.capacity,
                                "outage": m.outage,
                                "expected_loss": m.expected_loss,
                            }
                        )
    return pd.DataFrame(rows), summary
