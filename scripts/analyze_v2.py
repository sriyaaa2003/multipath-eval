"""Analysis of the v2 run: which new algorithm helps, does correlation change the ranking, and can the best algorithm be predicted."""
import sys, json
sys.path.insert(0, "src")
import numpy as np, pandas as pd, networkx as nx
from multipath_eval.config import load_config
from multipath_eval.topologies import load_network, haversine_km
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import LeaveOneGroupOut, cross_val_predict

cfg = load_config("configs/default.toml")
d = pd.read_parquet("results/v2/demand_metrics_v2.parquet")
METRICS = ["cost", "delay", "capacity", "outage"]
DIR = {"cost": -1, "delay": -1, "capacity": 1, "outage": -1}
rng = np.random.default_rng(3)
out = {}

# scenario means (over demands)
sc = d.groupby(["topology", "setting", "fail_model", "algorithm"], as_index=False)[METRICS + ["served"]].mean()
def norm(df):
    df = df.copy()
    for m in METRICS:
        g = df.groupby(["topology", "setting", "fail_model"])[m]
        lo, hi = g.transform("min"), g.transform("max")
        span = (hi - lo).where((hi - lo) > 1e-12)
        n = ((df[m] - lo) / span).fillna(0.0)
        df[m + "_n"] = n if DIR[m] > 0 else (1 - n).where(span.notna(), 0.0)
    df["score"] = sum(df[m + "_n"] for m in METRICS) / len(METRICS)
    return df
S = norm(sc)

def boot_net(diff_by_net, n=2000):
    v = diff_by_net.to_numpy(); idx = rng.integers(0, len(v), (n, len(v)))
    m = v[idx].mean(axis=1); return float(v.mean()), float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))

def paired(a, b, metric, model):
    x = sc[(sc.fail_model == model)]
    pa = x[x.algorithm == a].groupby("topology")[metric].mean(); pb = x[x.algorithm == b].groupby("topology")[metric].mean()
    return boot_net((pa - pb).dropna())

lines = []
lines.append("## Mean metrics by algorithm and failure model (80 networks, 25 demands each)\n")
t = sc.groupby(["fail_model", "algorithm"])[METRICS + ["served"]].mean().round(3)
lines.append(t.to_markdown())

lines.append("\n## Combined score (equal weights, min-max within scenario) and share of random weight vectors won\n")
W = rng.dirichlet(np.ones(4), size=500)
rows = []
for model in ("independent", "regional"):
    sub = S[S.fail_model == model]
    wins = {a: 0 for a in sub.algorithm.unique()}; tot = 0
    for _, g in sub.groupby(["topology", "setting"]):
        mat = g[[m + "_n" for m in METRICS]].to_numpy(); algos = g.algorithm.to_numpy()
        win = (W @ mat.T).argmax(axis=1)
        for i in win: wins[algos[i]] += 1
        tot += len(win)
    top1 = sub.assign(rk=sub.groupby(["topology", "setting"])["score"].rank(ascending=False, method="min")).query("rk == 1").groupby("algorithm").size() / sub[["topology", "setting"]].drop_duplicates().shape[0]
    for a in sorted(wins, key=lambda a: -sub[sub.algorithm == a].score.mean()):
        rows.append({"failure model": model, "algorithm": a, "mean score": round(sub[sub.algorithm == a].score.mean(), 3),
                     "first (equal weights)": f"{100 * top1.get(a, 0):.0f}%", "first (random weights)": f"{100 * wins[a] / tot:.0f}%"})
lines.append(pd.DataFrame(rows).to_markdown(index=False))

lines.append("\n## Did the fixes work? Paired differences across networks (mean, 95% CI by resampling networks)\n")
cmp_ = [("disjoint_mincost", "disjoint", "cost", "independent"), ("disjoint_mincost", "disjoint", "outage", "independent"),
        ("mincost_maxflow", "maxflow", "cost", "independent"), ("mincost_maxflow", "maxflow", "capacity", "independent"),
        ("mincost_maxflow", "maxflow", "outage", "independent"), ("ksp_wcmp", "ksp", "capacity", "independent"),
        ("ksp_wcmp", "ksp", "cost", "independent"), ("geo_diverse", "ksp", "outage", "regional"),
        ("geo_diverse", "disjoint", "outage", "regional"), ("geo_diverse", "disjoint_mincost", "outage", "regional"),
        ("disjoint_mincost", "ksp", "outage", "regional"), ("disjoint_mincost", "ksp", "outage", "independent"),
        ("node_disjoint", "disjoint", "outage", "regional"), ("mincost_maxflow", "ksp", "served", "regional"),
        ("ksp", "shortest", "outage", "independent"), ("ksp", "shortest", "outage", "regional")]
rows = []
for a, b, m, model in cmp_:
    mean, lo, hi = paired(a, b, m, model)
    rows.append({"a": a, "b": b, "metric": m, "failure model": model, "mean a-b": round(mean, 4), "ci95": f"[{lo:.4f}, {hi:.4f}]"})
lines.append(pd.DataFrame(rows).to_markdown(index=False))

# ranking agreement between the two failure models
lines.append("\n## Does correlation change the ranking? (per-network best algorithm by combined score)\n")
best = S.groupby(["topology", "setting", "fail_model"]).apply(lambda g: g.loc[g.score.idxmax(), "algorithm"]).unstack("fail_model")
agree = float((best["independent"] == best["regional"]).mean())
lines.append(f"The best algorithm is the same under both failure models in **{100 * agree:.0f}%** of scenarios.")
mi, mr = S[S.fail_model == "independent"].groupby("algorithm").score.mean(), S[S.fail_model == "regional"].groupby("algorithm").score.mean()
from scipy.stats import kendalltau
lines.append(f"Kendall tau between the two mean-score rankings: {kendalltau(mi, mr.reindex(mi.index)).statistic:.2f}.")

# predict the best algorithm from network features
feats = []
for t_ in sc.topology.unique():
    spec = [s for s in cfg.topologies if s.name == t_][0]
    g = load_network(cfg.base_dir / spec.params["path"])
    kms = [haversine_km(g.nodes[u]["Latitude"], g.nodes[u]["Longitude"], g.nodes[v]["Latitude"], g.nodes[v]["Longitude"]) for u, v in g.edges()
           if all(k in g.nodes[n] for n in (u, v) for k in ("Latitude", "Longitude"))]
    feats.append({"topology": t_, "nodes": g.number_of_nodes(), "edges": g.number_of_edges(), "avg_degree": 2 * g.number_of_edges() / g.number_of_nodes(),
                  "diameter": nx.diameter(g), "mean_link_km": float(np.mean(kms)) if kms else 0.0, "cyclomatic": g.number_of_edges() - g.number_of_nodes() + 1,
                  "min_degree1_share": float(np.mean([deg == 1 for _, deg in g.degree()]))})
F = pd.DataFrame(feats).set_index("topology")
res = {}
for model in ("independent", "regional"):
    b = best[model].reset_index(); X = F.loc[b.topology].to_numpy(); y = b[model].to_numpy(); grp = b.topology.to_numpy()
    pred = cross_val_predict(DecisionTreeClassifier(max_depth=3, min_samples_leaf=8, random_state=0), X, y, groups=grp, cv=LeaveOneGroupOut())
    maj = pd.Series(y).value_counts(normalize=True).iloc[0]
    res[model] = (float((pred == y).mean()), float(maj))
lines.append("\n## Can the best algorithm be predicted from the network? (depth-3 tree, leave-one-network-out)\n")
for model, (acc, maj) in res.items():
    lines.append(f"- {model} failures: accuracy **{100 * acc:.0f}%** against {100 * maj:.0f}% for always guessing the most common winner.")
open("results/v2/results_v2.md", "w", encoding="utf-8").write("\n".join(lines))
print("\n".join(lines))
