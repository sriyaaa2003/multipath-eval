## Mean metrics by algorithm and failure model (80 networks, 25 demands each)

|                                     |   cost |   delay |   capacity |   outage |   served |
|:------------------------------------|-------:|--------:|-----------:|---------:|---------:|
| ('independent', 'disjoint')         | 33.879 |  14.821 |      3.052 |    0.079 |    0.834 |
| ('independent', 'disjoint_mincost') | 32.044 |  14.202 |      3.043 |    0.075 |    0.841 |
| ('independent', 'ecmp')             | 26.902 |  11.931 |      2.856 |    0.116 |    0.863 |
| ('independent', 'geo_diverse')      | 32.918 |  14.507 |      3.039 |    0.077 |    0.839 |
| ('independent', 'ksp')              | 32.116 |  14.193 |      2.861 |    0.062 |    0.839 |
| ('independent', 'ksp_wcmp')         | 30.929 |  13.681 |      3.564 |    0.062 |    0.845 |
| ('independent', 'maxflow')          | 39.868 |  18.348 |      5.867 |    0.067 |    0.813 |
| ('independent', 'mincost_maxflow')  | 32.741 |  15.176 |      5.867 |    0.059 |    0.838 |
| ('independent', 'node_disjoint')    | 33.066 |  14.553 |      2.982 |    0.087 |    0.837 |
| ('independent', 'shortest')         | 24.494 |  11.176 |      2.637 |    0.127 |    0.873 |
| ('regional', 'disjoint')            | 33.879 |  14.821 |      3.052 |    0.055 |    0.91  |
| ('regional', 'disjoint_mincost')    | 32.044 |  14.202 |      3.043 |    0.055 |    0.91  |
| ('regional', 'ecmp')                | 26.902 |  11.931 |      2.856 |    0.068 |    0.924 |
| ('regional', 'geo_diverse')         | 32.918 |  14.507 |      3.039 |    0.056 |    0.909 |
| ('regional', 'ksp')                 | 32.116 |  14.193 |      2.861 |    0.055 |    0.905 |
| ('regional', 'ksp_wcmp')            | 30.929 |  13.681 |      3.564 |    0.055 |    0.908 |
| ('regional', 'maxflow')             | 39.868 |  18.348 |      5.867 |    0.052 |    0.898 |
| ('regional', 'mincost_maxflow')     | 32.741 |  15.176 |      5.867 |    0.05  |    0.907 |
| ('regional', 'node_disjoint')       | 33.066 |  14.553 |      2.982 |    0.056 |    0.911 |
| ('regional', 'shortest')            | 24.494 |  11.176 |      2.637 |    0.078 |    0.922 |

## Combined score (equal weights, min-max within scenario) and share of random weight vectors won

| failure model   | algorithm        |   mean score | first (equal weights)   | first (random weights)   |
|:----------------|:-----------------|-------------:|:------------------------|:-------------------------|
| independent     | mincost_maxflow  |        0.71  | 89%                     | 52%                      |
| independent     | ksp_wcmp         |        0.584 | 5%                      | 13%                      |
| independent     | disjoint_mincost |        0.513 | 10%                     | 6%                       |
| independent     | shortest         |        0.509 | 2%                      | 17%                      |
| independent     | ecmp             |        0.508 | 1%                      | 5%                       |
| independent     | ksp              |        0.489 | 1%                      | 2%                       |
| independent     | maxflow          |        0.485 | 1%                      | 1%                       |
| independent     | geo_diverse      |        0.48  | 5%                      | 0%                       |
| independent     | disjoint         |        0.449 | 4%                      | 3%                       |
| independent     | node_disjoint    |        0.446 | 4%                      | 0%                       |
| regional        | mincost_maxflow  |        0.719 | 91%                     | 54%                      |
| regional        | ksp_wcmp         |        0.553 | 4%                      | 7%                       |
| regional        | ecmp             |        0.548 | 3%                      | 9%                       |
| regional        | disjoint_mincost |        0.524 | 10%                     | 7%                       |
| regional        | shortest         |        0.517 | 2%                      | 17%                      |
| regional        | geo_diverse      |        0.496 | 5%                      | 1%                       |
| regional        | maxflow          |        0.485 | 0%                      | 1%                       |
| regional        | node_disjoint    |        0.48  | 4%                      | 0%                       |
| regional        | disjoint         |        0.473 | 4%                      | 4%                       |
| regional        | ksp              |        0.458 | 1%                      | 1%                       |

## Did the fixes work? Paired differences across networks (mean, 95% CI by resampling networks)

| a                | b                | metric   | failure model   |   mean a-b | ci95               |
|:-----------------|:-----------------|:---------|:----------------|-----------:|:-------------------|
| disjoint_mincost | disjoint         | cost     | independent     |    -1.8349 | [-2.3518, -1.3935] |
| disjoint_mincost | disjoint         | outage   | independent     |    -0.0044 | [-0.0061, -0.0030] |
| mincost_maxflow  | maxflow          | cost     | independent     |    -7.1266 | [-9.2314, -5.5813] |
| mincost_maxflow  | maxflow          | capacity | independent     |    -0.0007 | [-0.0008, -0.0005] |
| mincost_maxflow  | maxflow          | outage   | independent     |    -0.0083 | [-0.0107, -0.0059] |
| ksp_wcmp         | ksp              | capacity | independent     |     0.7035 | [0.5853, 0.8148]   |
| ksp_wcmp         | ksp              | cost     | independent     |    -1.1873 | [-1.6340, -0.8212] |
| geo_diverse      | ksp              | outage   | regional        |     0.0011 | [-0.0017, 0.0040]  |
| geo_diverse      | disjoint         | outage   | regional        |     0.0011 | [0.0002, 0.0020]   |
| geo_diverse      | disjoint_mincost | outage   | regional        |     0.0006 | [-0.0000, 0.0012]  |
| disjoint_mincost | ksp              | outage   | regional        |     0.0005 | [-0.0024, 0.0034]  |
| disjoint_mincost | ksp              | outage   | independent     |     0.0122 | [0.0070, 0.0175]   |
| node_disjoint    | disjoint         | outage   | regional        |     0.0015 | [0.0005, 0.0026]   |
| mincost_maxflow  | ksp              | served   | regional        |     0.0018 | [-0.0008, 0.0043]  |
| ksp              | shortest         | outage   | independent     |    -0.0645 | [-0.0691, -0.0598] |
| ksp              | shortest         | outage   | regional        |    -0.0235 | [-0.0277, -0.0192] |

## Does correlation change the ranking? (per-network best algorithm by combined score)

The best algorithm is the same under both failure models in **89%** of scenarios.
Kendall tau between the two mean-score rankings: 0.64.

## Can the best algorithm be predicted from the network? (depth-3 tree, leave-one-network-out)

- independent failures: accuracy **75%** against 80% for always guessing the most common winner.
- regional failures: accuracy **75%** against 82% for always guessing the most common winner.