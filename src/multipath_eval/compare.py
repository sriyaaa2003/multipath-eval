"""Cross-property comparison: combined score, Pareto dominance, rank stability and ranking consistency."""

from __future__ import annotations

import itertools

import numpy as np
import pandas as pd
from scipy.stats import kendalltau

from .config import METRICS

# direction: +1 means higher is better
DIRECTION = {"cost": -1, "delay": -1, "capacity": +1, "outage": -1}


def scenario_means(rows: pd.DataFrame) -> pd.DataFrame:
    """Mean of each metric over demands, one row per scenario and algorithm."""
    cols = ["cost", "delay", "capacity", "outage", "expected_loss"]
    return rows.groupby(["scenario", "family", "topology", "setting", "algorithm"], as_index=False)[cols].mean()


def normalise(means: pd.DataFrame) -> pd.DataFrame:
    """Min-max normalise each metric within a scenario so that 1 is best and 0 is worst."""
    out = means.copy()
    for m in METRICS:
        grp = out.groupby("scenario")[m]
        lo, hi = grp.transform("min"), grp.transform("max")
        span = (hi - lo).where((hi - lo) > 1e-12)
        norm = (out[m] - lo) / span
        norm = norm.fillna(0.0)
        out[f"{m}_n"] = norm if DIRECTION[m] > 0 else (1.0 - norm).where(span.notna(), 0.0)
    return out


def combined_scores(norm: pd.DataFrame, weights: dict) -> pd.DataFrame:
    out = norm.copy()
    out["score"] = sum(weights[m] * out[f"{m}_n"] for m in METRICS)
    out["rank"] = out.groupby("scenario")["score"].rank(ascending=False, method="min")
    return out


def pareto_nondominated(means: pd.DataFrame) -> pd.Series:
    """True for algorithms no other algorithm beats on every property of the scenario."""
    flags = pd.Series(False, index=means.index)
    for _, grp in means.groupby("scenario"):
        vals = np.column_stack([DIRECTION[m] * grp[m].to_numpy() for m in METRICS])
        for i, idx in enumerate(grp.index):
            dominated = any(
                np.all(vals[j] >= vals[i]) and np.any(vals[j] > vals[i]) for j in range(len(vals)) if j != i
            )
            flags[idx] = not dominated
    return flags


def rank_stability(norm: pd.DataFrame, n_vectors: int, rng: np.random.Generator) -> pd.DataFrame:
    """Share of random weight vectors (Dirichlet) under which each algorithm ranks first, per scenario."""
    w = rng.dirichlet(np.ones(len(METRICS)), size=n_vectors)
    rows = []
    for scen, grp in norm.groupby("scenario"):
        mat = grp[[f"{m}_n" for m in METRICS]].to_numpy()
        scores = w @ mat.T
        winners = scores.argmax(axis=1)
        for i, algo in enumerate(grp["algorithm"]):
            rows.append({"scenario": scen, "algorithm": algo, "first_share": float((winners == i).mean())})
    return pd.DataFrame(rows)


def ranking_consistency(scored: pd.DataFrame) -> dict:
    """Kendall tau between the algorithm rankings of every pair of scenarios."""
    wide = scored.pivot(index="scenario", columns="algorithm", values="rank")
    taus = []
    for a, b in itertools.combinations(wide.index, 2):
        tau = kendalltau(wide.loc[a], wide.loc[b]).statistic
        if not np.isnan(tau):
            taus.append(tau)
    taus = np.array(taus)
    first = (scored["rank"] == 1).groupby(scored["algorithm"]).mean()
    return {
        "scenarios": int(len(wide)),
        "pairs": int(len(taus)),
        "tau_mean": float(taus.mean()) if len(taus) else float("nan"),
        "tau_p10": float(np.percentile(taus, 10)) if len(taus) else float("nan"),
        "tau_share_above_0.5": float((taus > 0.5).mean()) if len(taus) else float("nan"),
        "first_share": first.to_dict(),
    }


def group_consistency(scored: pd.DataFrame, by: str) -> pd.DataFrame:
    """Mean combined score per algorithm within each group (family or setting), with the group ranking."""
    g = scored.groupby([by, "algorithm"], as_index=False)["score"].mean()
    g["rank"] = g.groupby(by)["score"].rank(ascending=False, method="min")
    return g
