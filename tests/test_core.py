from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd
import pytest

from multipath_eval import compare
from multipath_eval.algorithms import ALGORITHMS, disjoint, ecmp, ksp, maxflow, shortest
from multipath_eval.cli import run
from multipath_eval.config import ConfigError, load_config
from multipath_eval.metrics import draw_failures, edge_index, evaluate
from multipath_eval.topologies import assign_attributes, load_network

ROOT = Path(__file__).resolve().parents[1]


def diamond(fail=0.1, capacity=5.0):
    g = nx.Graph()
    for u, v in [("s", "a"), ("a", "t"), ("s", "b"), ("b", "t")]:
        g.add_edge(u, v, cost=1.0, delay=2.0, capacity=capacity, fail=fail)
    return g


def metrics_for(g, res, scale=1.0, n=20000, seed=1):
    failures, probs = draw_failures(g, scale, n, np.random.default_rng(seed))
    return evaluate(g, res, edge_index(g), failures, probs)


def test_split_sums_to_one_for_every_algorithm():
    g = diamond()
    for fn in ALGORITHMS.values():
        res = fn(g, "s", "t", 3)
        assert res is not None
        assert sum(res.split) == pytest.approx(1.0)


def test_disjoint_diamond_metrics_match_hand_calculation():
    g = diamond()
    m = metrics_for(g, disjoint(g, "s", "t", 3))
    assert m.cost == pytest.approx(2.0)
    assert m.delay == pytest.approx(4.0)
    assert m.capacity == pytest.approx(10.0)  # each edge carries half of the demand
    path_fail = 1 - 0.9**2
    assert m.expected_loss == pytest.approx(path_fail)
    assert m.outage == pytest.approx(path_fail**2, abs=0.005)


def test_single_path_outage_equals_path_failure():
    g = diamond()
    m = metrics_for(g, shortest(g, "s", "t", 3))
    assert m.capacity == pytest.approx(5.0)
    assert m.outage == pytest.approx(1 - 0.9**2, abs=0.01)


def test_multipath_beats_single_path_on_outage():
    g = diamond()
    single = metrics_for(g, shortest(g, "s", "t", 3))
    multi = metrics_for(g, disjoint(g, "s", "t", 3))
    assert multi.outage < single.outage


def test_maxflow_uses_both_branches_and_reaches_flow_value():
    g = diamond()
    res = maxflow(g, "s", "t", 3)
    assert len(res.paths) == 2
    assert metrics_for(g, res).capacity == pytest.approx(10.0)


def test_ksp_returns_loopless_distinct_paths():
    g = diamond()
    res = ksp(g, "s", "t", 5)
    assert len(res.paths) == 2 == len(set(res.paths))
    assert all(len(set(p)) == len(p) for p in res.paths)


def test_ecmp_uses_equal_hop_paths():
    g = diamond()
    res = ecmp(g, "s", "t", 3)
    assert {len(p) for p in res.paths} == {3}


def test_disconnected_pair_returns_none():
    g = diamond()
    g.add_edge("x", "y", cost=1.0, delay=1.0, capacity=1.0, fail=0.1)
    for fn in ALGORITHMS.values():
        assert fn(g, "s", "x", 3) is None


def test_gml_loader_reads_public_topology_with_real_values():
    g = load_network(ROOT / "data" / "topology_zoo" / "Arnes.gml")
    assert nx.is_connected(g)
    cfg = load_config(ROOT / "configs" / "default.toml")
    used = assign_attributes(g, cfg, np.random.default_rng(0))
    assert used["delay_real"] == g.number_of_edges()  # delay comes from node coordinates
    assert all(d["fail"] > 0 and d["cost"] > 0 for _, _, d in g.edges(data=True))


def test_missing_gml_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_network(tmp_path / "nope.gml")


def test_config_validation_names_the_field(tmp_path):
    bad = tmp_path / "configs"
    bad.mkdir()
    text = (ROOT / "configs" / "default.toml").read_text(encoding="utf-8").replace("seed = 7", "", 1)
    (bad / "bad.toml").write_text(text, encoding="utf-8")
    with pytest.raises(ConfigError, match="seed"):
        load_config(bad / "bad.toml")


def test_normalise_and_score_direction():
    means = pd.DataFrame(
        {
            "scenario": ["s"] * 2,
            "family": ["f"] * 2,
            "topology": ["t"] * 2,
            "setting": ["x"] * 2,
            "algorithm": ["good", "bad"],
            "cost": [1.0, 2.0],
            "delay": [1.0, 2.0],
            "capacity": [2.0, 1.0],
            "outage": [0.1, 0.2],
            "expected_loss": [0.1, 0.2],
        }
    )
    scored = compare.combined_scores(compare.normalise(means), {"cost": 1, "delay": 1, "capacity": 1, "outage": 1})
    best = scored.set_index("algorithm")
    assert best.loc["good", "rank"] == 1 and best.loc["bad", "rank"] == 2
    assert best.loc["good", "score"] == pytest.approx(4.0)


def tiny_config(tmp_path):
    cfg_dir = tmp_path / "configs"
    cfg_dir.mkdir()
    zoo = (ROOT / "data" / "topology_zoo").as_posix()
    (cfg_dir / "tiny.toml").write_text(
        """
[run]
name = "tiny"
seed = 3
out_dir = "results/tiny"
k = 3
demands = 6
mc_draws = 300
weight_vectors = 20
[weights]
cost = 0.25
delay = 0.25
capacity = 0.25
outage = 0.25
[attributes]
cost = { low = 1.0, high = 10.0 }
delay_ms = { low = 1.0, high = 20.0 }
capacity = { low = 1.0, high = 10.0 }
fail_prob = { low = 0.01, high = 0.05 }
[[settings]]
name = "a"
fail_scale = 1.0
[[settings]]
name = "b"
fail_scale = 2.0
[[topologies]]
name = "arnes"
family = "gml"
path = "{zoo}/Arnes.gml"
seeds = 1
[[topologies]]
name = "geant2010"
family = "gml"
path = "{zoo}/Geant2010.gml"
seeds = 1
""".replace("{zoo}", zoo),
        encoding="utf-8",
    )
    return cfg_dir / "tiny.toml"


def test_end_to_end_is_deterministic(tmp_path):
    cfg = tiny_config(tmp_path)
    out1 = run(str(cfg), str(tmp_path / "r1"))
    out2 = run(str(cfg), str(tmp_path / "r2"))
    for name in ("demand_metrics.csv", "scenario_scores.csv", "results.md"):
        assert (out1 / name).read_bytes() == (out2 / name).read_bytes()
    for name in ("metrics_by_algorithm.png", "rank_distribution.png", "cost_vs_outage.png"):
        assert (out1 / name).stat().st_size > 0
