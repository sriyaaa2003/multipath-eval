"""Command line entry point: python -m multipath_eval run --config configs/default.toml"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

from . import compare
from .config import ConfigError, load_config
from .report import write_report
from .runner import run_experiment


def run(config_path: str, out_dir: str | None = None) -> Path:
    cfg = load_config(config_path)
    rows, summary = run_experiment(cfg)
    if rows.empty:
        raise SystemExit("no demand could be routed by every algorithm; check the topologies")
    means = compare.scenario_means(rows)
    norm = compare.normalise(means)
    scored = compare.combined_scores(norm, cfg.weights)
    nondominated = compare.pareto_nondominated(scored)
    stability = compare.rank_stability(norm, cfg.weight_vectors, np.random.default_rng([cfg.seed, 5]))
    consistency = compare.ranking_consistency(scored)
    groups = {
        "size": compare.group_consistency(scored, "size"),
        "setting": compare.group_consistency(scored, "setting"),
    }
    out = Path(out_dir) if out_dir else cfg.base_dir / cfg.out_dir
    groups["topology"] = compare.group_consistency(scored, "topology")
    write_report(out, rows, means, scored, stability, consistency, groups, nondominated, summary, cfg)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="multipath-eval")
    sub = parser.add_subparsers(dest="command", required=True)
    r = sub.add_parser("run", help="run an experiment from a TOML config")
    r.add_argument("--config", required=True)
    r.add_argument("--out", help="override the output directory")
    args = parser.parse_args(argv)
    try:
        out = run(args.config, args.out)
    except ConfigError as exc:
        print(f"config error: {exc}", file=sys.stderr)
        return 2
    print(f"results written to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
