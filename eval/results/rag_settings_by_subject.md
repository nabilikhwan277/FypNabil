# RAG settings per subject (R3)

Value = mean of the deciding metric; under it the change from the current option (95% CI). **bold** = clearly better than the current option in that subject.

## Selection per subject

| Setting | Deciding metric | Current | Ibadah | Jawi | Tajwid |
|---|---|---|---|---|---|
| Chunk size | factual correctness | 1,500 | same as current | same as current | same as current |
| Number of sections (k) | factual correctness | 3 | same as current | same as current | same as current |
| Context limit | factual correctness | 3,600 | same as current | same as current | same as current |
| Query variants | evidence recall | none | same as current | same as current | same as current |
| Search scope | evidence recall | subject | same as current | same as current | same as current |
| Matching method | evidence recall | hybrid bge-m3 + BM25 | same as current | same as current | same as current |
| Jawi-script questions | evidence recall | weight 0.25 | same as current | same as current | same as current |

## Chunk size (factual correctness)

| Option | Ibadah (n=15) | Jawi (n=15) | Tajwid (n=15) |
|---|---|---|---|
| 300 | 0.670 (-0.041 [-0.12, +0.01]) | 0.993 (+0.036 [+0.00, +0.09]) | 0.699 (-0.102 [-0.25, -0.01]) |
| 600 | 0.710 (+0.000 [+0.00, +0.00]) | 0.846 (-0.111 [-0.33, +0.04]) | 0.738 (-0.063 [-0.20, +0.01]) |
| 1,000 | 0.710 (+0.000 [+0.00, +0.00]) | 0.957 (+0.000 [+0.00, +0.00]) | 0.738 (-0.063 [-0.20, +0.01]) |
| 1,500 | 0.710 (current) | 0.957 (current) | 0.801 (current) |
| whole section | 0.710 (+0.000 [+0.00, +0.00]) | 0.957 (+0.000 [+0.00, +0.00]) | 0.801 (+0.000 [+0.00, +0.00]) |

## Number of sections (k) (factual correctness)

| Option | Ibadah (n=15) | Jawi (n=15) | Tajwid (n=15) |
|---|---|---|---|
| 1 | 0.486 (-0.224 [-0.43, -0.03]) | 0.913 (-0.044 [-0.13, +0.00]) | 0.427 (-0.374 [-0.60, -0.17]) |
| 2 | 0.692 (-0.018 [-0.12, +0.06]) | 0.957 (+0.000 [+0.00, +0.00]) | 0.678 (-0.123 [-0.26, -0.00]) |
| 3 | 0.710 (current) | 0.957 (current) | 0.801 (current) |
| 5 | 0.759 (+0.048 [-0.02, +0.14]) | 0.957 (+0.000 [+0.00, +0.00]) | 0.873 (+0.072 [-0.01, +0.20]) |
| 10 | 0.780 (+0.070 [+0.00, +0.18]) | 0.957 (+0.000 [+0.00, +0.00]) | 0.870 (+0.069 [-0.03, +0.21]) |

## Context limit (factual correctness)

| Option | Ibadah (n=15) | Jawi (n=15) | Tajwid (n=15) |
|---|---|---|---|
| 1,800 | 0.704 (-0.007 [-0.08, +0.06]) | 0.713 (-0.244 [-0.47, -0.04]) | 0.626 (-0.175 [-0.38, -0.00]) |
| 3,600 | 0.710 (current) | 0.957 (current) | 0.801 (current) |
| 7,200 | 0.710 (+0.000 [+0.00, +0.00]) | 0.957 (+0.000 [+0.00, +0.00]) | 0.801 (+0.000 [+0.00, +0.00]) |
| no limit | 0.710 (+0.000 [+0.00, +0.00]) | 0.957 (+0.000 [+0.00, +0.00]) | 0.801 (+0.000 [+0.00, +0.00]) |

## Query variants (evidence recall)

| Option | Ibadah (n=15) | Jawi (n=15) | Tajwid (n=15) |
|---|---|---|---|
| none | 0.902 (current) | 1.000 (current) | 0.859 (current) |
| 2 rewrites + RRF fusion | 0.887 (-0.015 [-0.04, +0.00]) | 0.956 (-0.044 [-0.13, +0.00]) | 0.846 (-0.014 [-0.09, +0.04]) |
| 2 rewrites + round-robin | 0.902 (+0.000 [+0.00, +0.00]) | 1.000 (+0.000 [+0.00, +0.00]) | 0.826 (-0.033 [-0.10, +0.00]) |

## Search scope (evidence recall)

| Option | Ibadah (n=15) | Jawi (n=15) | Tajwid (n=15) |
|---|---|---|---|
| all notes | 0.902 (+0.000 [+0.00, +0.00]) | 1.000 (+0.000 [+0.00, +0.00]) | 0.859 (+0.000 [+0.00, +0.00]) |
| subject | 0.902 (current) | 1.000 (current) | 0.859 (current) |
| topic first | 0.917 (+0.014 [-0.02, +0.06]) | 1.000 (+0.000 [+0.00, +0.00]) | 0.874 (+0.015 [+0.00, +0.04]) |

## Matching method (evidence recall)

| Option | Ibadah (n=15) | Jawi (n=15) | Tajwid (n=15) |
|---|---|---|---|
| bge-m3 only | 0.913 (+0.011 [-0.07, +0.10]) | 1.000 (+0.000 [+0.00, +0.00]) | 0.863 (+0.004 [-0.03, +0.04]) |
| BM25 only | 0.895 (-0.007 [-0.02, +0.00]) | 1.000 (+0.000 [+0.00, +0.00]) | 0.649 (-0.210 [-0.40, -0.05]) |
| hybrid bge-m3 + BM25 | 0.902 (current) | 1.000 (current) | 0.859 (current) |

## Jawi-script questions (evidence recall)

| Option | Ibadah (n=15) | Jawi (n=15) | Tajwid (n=15) |
|---|---|---|---|
| Rumi (same questions) | **0.902 (+0.255 [+0.07, +0.47])** | 1.000 (+0.044 [+0.00, +0.13]) | 0.859 (+0.080 [-0.13, +0.28]) |
| weight 0 | 0.724 (+0.077 [-0.09, +0.26]) | 0.956 (+0.000 [+0.00, +0.00]) | 0.779 (+0.000 [+0.00, +0.00]) |
| weight 0.25 | 0.647 (current) | 0.956 (current) | 0.779 (current) |
| weight 0.5 | 0.647 (+0.000 [+0.00, +0.00]) | 0.856 (-0.100 [-0.27, +0.00]) | 0.757 (-0.022 [-0.07, +0.00]) |
| weight 1 | 0.667 (+0.020 [+0.00, +0.06]) | 0.900 (-0.056 [-0.13, +0.00]) | 0.757 (-0.022 [-0.07, +0.00]) |
