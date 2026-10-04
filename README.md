# multipath-eval

Evaluation toolkit for multipath routing algorithms. It implements five routing algorithms, runs them on generated and public network topologies, scores each on **cost, delay, capacity and fault probability**, combines the four into one cross-property comparison, and checks whether the rankings stay consistent across networks and settings.

Built with Python, NumPy, NetworkX, SciPy, pandas and Matplotlib. The design is in [docs/BLUEPRINT.md](docs/BLUEPRINT.md).

## Algorithms

| name | idea |
|---|---|
| `shortest` | baseline: one least-cost path |
| `ksp` | k least-cost loopless paths (Yen), equal split |
| `disjoint` | up to k edge-disjoint paths, equal split |
| `ecmp` | all least-hop paths (capped at k), equal split |
| `maxflow` | maximum flow on edge capacities decomposed into paths, split proportional to path flow |

## Metrics (per source-destination pair, for a split path set)

- **cost**: split-weighted sum of edge costs. **delay**: split-weighted mean path delay.
- **capacity**: largest demand the split can carry, `min over edges of capacity / share of traffic on the edge`.
- **outage probability**: probability that every path is down, with independent edge failures (Monte Carlo, the same draws for all algorithms in a scenario). **expected loss** (exact) is also written to the CSV.
- **combined score**: each metric min-max normalised across the algorithms of a scenario (1 = best), then a weighted mean (weights in the config).
- **comparison beyond one score**: Pareto non-dominance, the share of random weight vectors (Dirichlet) under which each algorithm ranks first, and Kendall's tau between the rankings of every pair of scenarios.

## Run

```bash
pip install -e ".[dev]"
python -m multipath_eval run --config configs/default.toml
pytest
```

Every parameter (topologies, seeds, attribute ranges, failure settings, k, weights, Monte Carlo draws) is in [configs/default.toml](configs/default.toml). Output goes to `results/<run>/`: `results.md`, CSV files, `summary.json` and three plots. The same config always gives byte-identical files (tested).

## Topologies

Generated: Erdos-Renyi, 2D grid and Barabasi-Albert graphs (5 seeds each). Public: three real networks from the [Internet Topology Zoo](http://www.topology-zoo.org/) (Abilene, Aarnet, Geant2012; 5 attribute seeds each), loaded from the GML files in `data/topology_zoo/` (obtained from a public mirror of the Zoo dataset; the Zoo is licensed CC BY, cite Knight et al., "The Internet Topology Zoo", IEEE JSAC 2011).

On the Zoo graphs, delay is computed from the node coordinates (distance / 200 km per ms) and capacity from the link speed where the file has it. Cost and failure probability are not in the files and are always sampled. See `results/default/summary.json` for how many edges used real values.

## Results of the default run

750 source-destination pairs in 90 scenarios (30 topology instances x 3 failure settings); no pair was skipped. Full tables and plots are in [results/default/](results/default/results.md).

| algorithm | mean combined score | ranks first | first under random weights | outage prob. | capacity |
|---|---|---|---|---|---|
| ecmp | 0.610 | 87.8% | 41.9% | 0.061 | 3.82 |
| disjoint | 0.528 | 0.0% | 7.0% | 0.031 | 4.21 |
| ksp | 0.497 | 12.2% | 10.7% | 0.033 | 3.70 |
| maxflow | 0.480 | 0.0% | 28.1% | 0.029 | 10.06 |
| shortest | 0.469 | 0.0% | 12.4% | 0.099 | 3.27 |

What this shows, and what it does not:

- With equal weights ECMP ranks first in 88% of scenarios, but it wins under only 42% of random weight vectors. Max-flow is first under 28% of them because it carries about 2.4 times the capacity of the next algorithm, and it has the lowest outage probability. **The winner depends on the weights**, so a single combined score hides a real trade-off.
- Ranking consistency across scenarios is moderate: mean Kendall tau 0.43 over 4005 scenario pairs, and 46% of pairs above 0.5.
- The failure setting barely changes the combined score (it only scales outage probability); topology family changes it more.
- ECMP's good score partly reflects how it is defined here (least-hop paths, which are also short in cost and delay on these graphs); this is a property of the setup, not a general claim about ECMP.

## Limitations

- Edge failures are independent. Shared-risk link groups are not modelled.
- Cost and failure probability are sampled, not measured; delay and capacity are real only where the Zoo files provide them. Results on the generated graphs say nothing about any operator's network.
- Splits are static and equal (or proportional to flow). No congestion, queueing or dynamic rerouting is simulated.
- The combined score is relative within a scenario: adding or removing an algorithm changes the normalised values (the rank-stability test is there to show how much that matters).
- Five seeds per topology; spread across seeds is in `scenario_scores.csv` but no confidence intervals are computed yet.
