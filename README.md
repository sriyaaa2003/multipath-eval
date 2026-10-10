# multipath-eval

Which multipath routing algorithm is best? It depends on what you measure and on the network. This toolkit implements five algorithms,
runs them on **80 real operator networks** from the [Internet Topology Zoo](https://topology-zoo.org/), scores each on **cost, delay,
capacity and outage probability**, and checks whether the ranking holds across networks and settings. There are no generated graphs.

| algorithm | idea |
|---|---|
| `shortest` | baseline: one least-cost path |
| `ksp` | k least-cost loopless paths (Yen), equal split |
| `disjoint` | up to k edge-disjoint paths, equal split |
| `ecmp` | all least-hop paths (capped at k), equal split |
| `maxflow` | maximum flow on edge capacities decomposed into paths, split in proportion to path flow |

**Metrics** per source-destination pair: cost and mean delay (split-weighted), capacity (largest demand the split can carry), and outage
probability (all paths down at once, independent link failures, 4,000 Monte Carlo draws shared by all algorithms). The combined score
min-max normalises each metric within a scenario and averages with equal weights; Pareto non-dominance, 500 random weight vectors and
Kendall's tau between scenario rankings test whether the single score hides anything.

## Data

The networks with at least 15 nodes, coordinates for 95% of nodes and at least as many links as nodes: 80 of the 261 in the Zoo
(`scripts/make_zoo_config.py` selects them). Each gets 25 random source-destination pairs and three failure settings (x0.5, x1, x2).
What is real and what is assumed:

| property | source |
|---|---|
| topology | real |
| delay | real: great-circle link length / 200 km per ms (96% of the 4,699 links have coordinates at both ends) |
| capacity | real link speed where the file has one (**15%** of links), otherwise a draw from 1 to 10 |
| cost, failure probability | assumed proportional to link length (longer fibre costs more and is cut more often); mean cost 5.5, mean failure probability 0.03 |

## Results (80 networks, 240 scenarios, 2,000 demands)

| algorithm | cost | delay (ms) | capacity | outage prob. | combined score | first in x% of scenarios | first under random weights |
|---|---:|---:|---:|---:|---:|---:|---:|
| shortest | 24.5 | 11.2 | 2.6 | 0.127 | 0.508 | 17% | 30% |
| ecmp | 26.9 | 11.9 | 2.9 | 0.116 | 0.507 | 25% | 11% |
| ksp | 32.1 | 14.2 | 2.9 | 0.063 | 0.492 | **38%** | 23% |
| maxflow | 39.9 | 18.3 | **5.9** | 0.068 | 0.490 | 8% | 28% |
| disjoint | 33.9 | 14.8 | 3.1 | 0.079 | 0.452 | 13% | 9% |

- **No algorithm wins.** The mean combined scores of the top four differ by 0.02, and rankings barely agree between scenarios (mean
  Kendall's tau **0.05**; only 20% of scenario pairs above 0.5). `ksp` is best on large networks (0.548), `ecmp` on small ones (0.529).
- **The answer depends on the weights.** `ksp` is first most often under equal weights, but across random weight vectors the leaders are
  `shortest` and `maxflow` (30% and 28%): `maxflow` carries 1.9 times the capacity of the next algorithm for a cost 63% above `shortest`.
- **Edge-disjoint paths score lowest**: they cost more than `ksp` and still have a higher outage probability (0.079 against 0.063).
- The failure setting changes scores by less than 0.02, much less than network size does.

Limits: failures are independent and proportional to length, cost is a proxy, and 85% of capacities are sampled, so the capacity-driven
conclusions (`maxflow`) are the least certain. Per-network tables are in `results/default/score_by_topology.csv`.

## Run

```bash
pip install -e ".[dev]"
python -m multipath_eval run --config configs/default.toml     # results/default/: results.md, CSVs, summary.json, plots
python scripts/make_zoo_config.py path/to/topologyzoo/gml      # rebuild the network list
pytest                                                           # 13 tests, including byte-identical reruns
```

Every parameter lives in `configs/default.toml`; the design is in [docs/BLUEPRINT.md](docs/BLUEPRINT.md). Topology Zoo: Knight et al.,
"The Internet Topology Zoo", IEEE JSAC 2011 (CC BY); GML files from a public mirror.
