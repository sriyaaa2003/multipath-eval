# Results

Run `default`, base seed 7, k = 3, 4000 Monte Carlo draws.

Scenarios: 240 (80 topology instances x 3 settings). Demands evaluated: 2000, skipped (some algorithm found no route): 0.

## Mean metrics per algorithm (over all scenarios)

| algorithm | cost | delay | capacity | outage | score | mean_rank | first_share | pareto_nondominated | first_under_random_weights |
|---|---|---|---|---|---|---|---|---|---|
| ecmp | 26.902 | 11.931 | 2.856 | 0.116 | 0.507 | 2.592 | 0.250 | 0.908 | 0.111 |
| shortest | 24.494 | 11.176 | 2.637 | 0.127 | 0.508 | 2.604 | 0.171 | 1.000 | 0.298 |
| ksp | 32.116 | 14.193 | 2.861 | 0.063 | 0.492 | 2.833 | 0.383 | 1.000 | 0.227 |
| maxflow | 39.868 | 18.348 | 5.867 | 0.068 | 0.490 | 3.121 | 0.075 | 0.938 | 0.276 |
| disjoint | 33.879 | 14.821 | 3.052 | 0.079 | 0.452 | 3.587 | 0.133 | 0.812 | 0.088 |

## Ranking consistency across scenarios

Mean Kendall tau between the rankings of 28680 scenario pairs: **0.054** (10th percentile -0.600; 20.3% of pairs above 0.5).

Share of scenarios where each algorithm ranks first: ksp 38.3%, ecmp 25.0%, shortest 17.1%, disjoint 13.3%, maxflow 7.5%

## Mean combined score by size

| size | disjoint | ecmp | ksp | maxflow | shortest |
|---|---|---|---|---|---|
| large (50+) | 0.469 | 0.483 | 0.548 | 0.473 | 0.483 |
| medium (25-49) | 0.442 | 0.495 | 0.514 | 0.473 | 0.513 |
| small (<25 nodes) | 0.451 | 0.529 | 0.444 | 0.514 | 0.516 |

## Mean combined score by setting

| setting | disjoint | ecmp | ksp | maxflow | shortest |
|---|---|---|---|---|---|
| base_fail | 0.454 | 0.507 | 0.491 | 0.492 | 0.507 |
| high_fail | 0.441 | 0.505 | 0.496 | 0.486 | 0.508 |
| low_fail | 0.460 | 0.508 | 0.489 | 0.493 | 0.507 |
