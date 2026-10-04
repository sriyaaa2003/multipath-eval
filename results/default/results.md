# Results

Run `default`, base seed 7, k = 3, 4000 Monte Carlo draws.

Scenarios: 90 (30 topology instances x 3 settings). Demands evaluated: 750, skipped (some algorithm found no route): 0.

## Mean metrics per algorithm (over all scenarios)

| algorithm | cost | delay | capacity | outage | score | mean_rank | first_share | pareto_nondominated | first_under_random_weights |
|---|---|---|---|---|---|---|---|---|---|
| ecmp | 16.473 | 21.417 | 3.824 | 0.061 | 0.610 | 1.122 | 0.878 | 1.000 | 0.419 |
| disjoint | 21.105 | 27.457 | 4.212 | 0.031 | 0.528 | 2.889 | 0.000 | 1.000 | 0.070 |
| ksp | 18.463 | 28.361 | 3.704 | 0.033 | 0.497 | 3.222 | 0.122 | 0.933 | 0.107 |
| maxflow | 26.736 | 35.967 | 10.063 | 0.029 | 0.480 | 3.722 | 0.000 | 1.000 | 0.281 |
| shortest | 14.375 | 23.492 | 3.265 | 0.099 | 0.469 | 3.889 | 0.000 | 1.000 | 0.124 |

## Ranking consistency across scenarios

Mean Kendall tau between the rankings of 4005 scenario pairs: **0.429** (10th percentile 0.000; 45.8% of pairs above 0.5).

Share of scenarios where each algorithm ranks first: ecmp 87.8%, ksp 12.2%, disjoint 0.0%, maxflow 0.0%, shortest 0.0%

## Mean combined score by topology

| topology | disjoint | ecmp | ksp | maxflow | shortest |
|---|---|---|---|---|---|
| aarnet | 0.551 | 0.643 | 0.437 | 0.458 | 0.477 |
| abilene | 0.472 | 0.594 | 0.350 | 0.509 | 0.496 |
| barabasi_albert | 0.553 | 0.608 | 0.504 | 0.500 | 0.406 |
| erdos_renyi | 0.537 | 0.599 | 0.556 | 0.499 | 0.479 |
| geant2012 | 0.544 | 0.629 | 0.540 | 0.412 | 0.477 |
| grid | 0.509 | 0.589 | 0.593 | 0.500 | 0.476 |

## Mean combined score by setting

| setting | disjoint | ecmp | ksp | maxflow | shortest |
|---|---|---|---|---|---|
| base_fail | 0.529 | 0.611 | 0.497 | 0.481 | 0.469 |
| high_fail | 0.522 | 0.609 | 0.495 | 0.479 | 0.469 |
| low_fail | 0.532 | 0.610 | 0.498 | 0.479 | 0.469 |
