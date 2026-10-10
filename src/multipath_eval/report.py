"""Write CSV files, Markdown tables and plots for a finished run."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from .config import METRICS  # noqa: E402

LABELS = {"cost": "cost", "delay": "delay (ms)", "capacity": "capacity", "outage": "outage probability"}


def _md(df: pd.DataFrame, floatfmt: str = "{:.3f}") -> str:
    cols = list(df.columns)
    lines = ["| " + " | ".join(str(c) for c in cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, row in df.iterrows():
        cells = [floatfmt.format(v) if isinstance(v, (float, np.floating)) else str(v) for v in row]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def write_report(out: Path, rows, means, scored, stability, consistency, group_tables, nondominated, summary, cfg) -> None:
    out.mkdir(parents=True, exist_ok=True)
    rows.to_csv(out / "demand_metrics.csv", index=False)
    scored.to_csv(out / "scenario_scores.csv", index=False)
    (out / "summary.json").write_text(json.dumps({"run": summary, "consistency": consistency}, indent=2), encoding="utf-8")

    algo = scored.groupby("algorithm").agg(
        cost=("cost", "mean"),
        delay=("delay", "mean"),
        capacity=("capacity", "mean"),
        outage=("outage", "mean"),
        score=("score", "mean"),
        mean_rank=("rank", "mean"),
        first_share=("rank", lambda r: float((r == 1).mean())),
    )
    algo["pareto_nondominated"] = nondominated.groupby(scored["algorithm"]).mean()
    stab = stability.groupby("algorithm")["first_share"].mean()
    algo["first_under_random_weights"] = stab
    algo = algo.sort_values("mean_rank").reset_index()

    text = ["# Results", "", f"Run `{cfg.name}`, base seed {cfg.seed}, k = {cfg.k}, {cfg.mc_draws} Monte Carlo draws.", ""]
    text += [
        f"Scenarios: {summary['scenarios']} ({summary['instances']} topology instances x {len(cfg.settings)} settings). "
        f"Demands evaluated: {summary['demands_evaluated']}, skipped (some algorithm found no route): {summary['skipped_demands']}.",
        "",
        "## Mean metrics per algorithm (over all scenarios)",
        "",
        _md(algo),
        "",
        "## Ranking consistency across scenarios",
        "",
        f"Mean Kendall tau between the rankings of {consistency['pairs']} scenario pairs: "
        f"**{consistency['tau_mean']:.3f}** (10th percentile {consistency['tau_p10']:.3f}; "
        f"{consistency['tau_share_above_0.5']:.1%} of pairs above 0.5).",
        "",
        "Share of scenarios where each algorithm ranks first: "
        + ", ".join(f"{k} {v:.1%}" for k, v in sorted(consistency["first_share"].items(), key=lambda kv: -kv[1])),
        "",
    ]
    group_tables["topology"].to_csv(out / "score_by_topology.csv", index=False)
    for by, table in group_tables.items():
        if by == "topology":
            continue
        wide = table.pivot(index=by, columns="algorithm", values="score")
        wide.insert(0, by, wide.index)
        text += [f"## Mean combined score by {by}", "", _md(wide.reset_index(drop=True)), ""]
    (out / "results.md").write_text("\n".join(text), encoding="utf-8")
    algo.to_csv(out / "algorithm_summary.csv", index=False)

    _plot_metrics(out, scored)
    _plot_rank_distribution(out, scored)
    _plot_tradeoff(out, scored)


def _plot_metrics(out: Path, scored: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 4, figsize=(13, 3.2))
    for ax, m in zip(axes, METRICS):
        g = scored.groupby("algorithm")[m].mean().sort_values()
        ax.bar(g.index, g.values, color="#4c78a8")
        ax.set_title(LABELS[m])
        ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    fig.savefig(out / "metrics_by_algorithm.png", dpi=150)
    plt.close(fig)


def _plot_rank_distribution(out: Path, scored: pd.DataFrame) -> None:
    ranks = sorted(scored["rank"].unique())
    share = scored.groupby("algorithm")["rank"].value_counts(normalize=True).unstack(fill_value=0).reindex(columns=ranks, fill_value=0)
    share = share.loc[share.mul(range(len(ranks))).sum(axis=1).sort_values().index]
    fig, ax = plt.subplots(figsize=(6.5, 3.6))
    left = np.zeros(len(share))
    for i, r in enumerate(ranks):
        ax.barh(share.index, share[r].values, left=left, label=f"rank {r:.0f}", color=plt.cm.viridis_r(i / max(len(ranks) - 1, 1)))
        left += share[r].values
    ax.set_xlabel("share of scenarios")
    ax.set_title("Rank of combined score across networks (1 = best)")
    ax.legend(ncol=5, fontsize=7, loc="lower center", bbox_to_anchor=(0.5, -0.4))
    fig.tight_layout()
    fig.savefig(out / "rank_distribution.png", dpi=150)
    plt.close(fig)


def _plot_tradeoff(out: Path, scored: pd.DataFrame) -> None:
    g = scored.groupby("algorithm")[["cost", "outage"]].mean()
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.scatter(g["cost"], g["outage"], s=60, color="#e45756")
    for name, row in g.iterrows():
        ax.annotate(name, (row["cost"], row["outage"]), textcoords="offset points", xytext=(5, 5))
    ax.set_xlabel("mean path cost")
    ax.set_ylabel("outage probability")
    ax.set_title("Cost versus outage probability")
    fig.tight_layout()
    fig.savefig(out / "cost_vs_outage.png", dpi=150)
    plt.close(fig)
