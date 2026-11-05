# Embedding models for R3 (Phase 2.1)

Same 45 questions, gold evidence and R3 setup; only the embedding model changes. Mean [95% bootstrap CI]; in brackets the change from bge-m3 (**bold** = clear: the interval leaves out 0).

## The models

| Model | Parameters | Vector size | Longest input (tokens) | Time to embed the notes (RTX 3050 laptop, fp16) | Chunks |
|---|---|---|---|---|---|
| bge-m3 | 568 M | 1024 | 8,192 | 8 s | 339 |
| multilingual-e5-large | 560 M | 1024 | 512 | 7 s | 339 |
| multilingual-e5-base | 278 M | 768 | 512 | 3 s | 339 |
| MiniLM-L12 (multilingual) | 118 M | 384 | 128 | 1 s | 339 |

## Hybrid search (as live), all metrics

| Model | Hit rate | Evidence recall | Precision | MRR |
|---|---|---|---|---|
| bge-m3 (current) | 0.978 [0.93, 1.00] | 0.920 [0.85, 0.98] | 0.907 [0.84, 0.96] | 0.922 [0.86, 0.98] |
| multilingual-e5-large | 0.933 [0.84, 1.00] | 0.883 [0.80, 0.96] | 0.870 [0.78, 0.94] | 0.874 [0.78, 0.95] |
| multilingual-e5-base | 0.911 [0.82, 0.98] | 0.828 [0.73, 0.91] | 0.848 [0.75, 0.93] | 0.867 [0.77, 0.94] |
| MiniLM-L12 (multilingual) | 0.711 [0.58, 0.84] | 0.579 [0.44, 0.71] | 0.609 [0.47, 0.73] | 0.626 [0.49, 0.75] |

## Hybrid search (as live): evidence recall per subject

| Option | All (n=45) | Ibadah (n=15) | Jawi (n=15) | Tajwid (n=15) |
|---|---|---|---|---|
| bge-m3 (current) | 0.920 | 0.902 | 1.000 | 0.859 |
| multilingual-e5-large | 0.883 (-0.038 [-0.11, +0.01]) | 0.922 (+0.020 [+0.00, +0.06]) | 0.933 (-0.067 [-0.20, +0.00]) | 0.793 (-0.067 [-0.20, +0.00]) |
| multilingual-e5-base | 0.828 (**-0.093 [-0.18, -0.03]**) | 0.865 (-0.037 [-0.09, +0.00]) | 1.000 (+0.000 [+0.00, +0.00]) | 0.618 (**-0.241 [-0.46, -0.05]**) |
| MiniLM-L12 (multilingual) | 0.579 (**-0.341 [-0.47, -0.22]**) | 0.392 (**-0.510 [-0.73, -0.29]**) | 0.811 (-0.189 [-0.39, +0.00]) | 0.534 (**-0.325 [-0.56, -0.10]**) |

## Dense only (the embedding alone): evidence recall per subject

| Option | All (n=45) | Ibadah (n=15) | Jawi (n=15) | Tajwid (n=15) |
|---|---|---|---|---|
| bge-m3 (current) | 0.925 | 0.913 | 1.000 | 0.863 |
| multilingual-e5-large | 0.810 (**-0.116 [-0.21, -0.04]**) | 0.885 (-0.028 [-0.11, +0.05]) | 0.878 (-0.122 [-0.31, +0.00]) | 0.666 (**-0.197 [-0.38, -0.04]**) |
| multilingual-e5-base | 0.749 (**-0.176 [-0.28, -0.08]**) | 0.793 (-0.120 [-0.29, +0.02]) | 1.000 (+0.000 [+0.00, +0.00]) | 0.455 (**-0.408 [-0.63, -0.20]**) |
| MiniLM-L12 (multilingual) | 0.341 (**-0.585 [-0.71, -0.45]**) | 0.069 (**-0.844 [-0.94, -0.73]**) | 0.467 (**-0.533 [-0.80, -0.27]**) | 0.486 (**-0.377 [-0.59, -0.16]**) |

## Questions typed in Jawi (hybrid): evidence recall per subject

| Option | All (n=45) | Ibadah (n=15) | Jawi (n=15) | Tajwid (n=15) |
|---|---|---|---|---|
| bge-m3 (current) | 0.794 | 0.647 | 0.956 | 0.779 |
| multilingual-e5-large | 0.758 (-0.035 [-0.12, +0.05]) | 0.771 (**+0.123 [+0.00, +0.28]**) | 0.867 (-0.089 [-0.24, +0.00]) | 0.638 (-0.141 [-0.31, +0.00]) |
| multilingual-e5-base | 0.783 (-0.011 [-0.10, +0.08]) | 0.680 (+0.033 [-0.16, +0.23]) | 0.922 (-0.033 [-0.10, +0.00]) | 0.746 (-0.033 [-0.23, +0.17]) |
| MiniLM-L12 (multilingual) | 0.679 (-0.115 [-0.25, +0.01]) | 0.767 (+0.120 [-0.12, +0.36]) | 0.822 (-0.133 [-0.33, +0.00]) | 0.449 (**-0.330 [-0.55, -0.13]**) |

## Answers (the best two and the current model)

| Option | Group | Factual correctness | Change | Faithfulness | Change | Declined |
|---|---|---|---|---|---|---|
| bge-m3 | All | 0.823 [0.73, 0.91] | – | 0.985 [0.96, 1.00] | – | 5 |
| bge-m3 | Ibadah | 0.710 [0.50, 0.88] | – | 0.962 [0.89, 1.00] | – | 3 |
| bge-m3 | Jawi | 0.957 [0.91, 1.00] | – | 0.989 [0.97, 1.00] | – | 0 |
| bge-m3 | Tajwid | 0.801 [0.60, 0.96] | – | 1.000 [1.00, 1.00] | – | 2 |
| multilingual-e5-large | All | 0.799 [0.70, 0.90] | -0.024 [-0.08, +0.04] | 0.983 [0.95, 1.00] | +0.000 [+0.00, +0.00] | 7 |
| multilingual-e5-large | Ibadah | 0.765 [0.58, 0.91] | +0.055 [+0.00, +0.16] | 0.962 [0.89, 1.00] | +0.000 [+0.00, +0.00] | 2 |
| multilingual-e5-large | Jawi | 0.913 [0.77, 1.00] | -0.044 [-0.13, +0.00] | 0.988 [0.96, 1.00] | +0.000 [+0.00, +0.00] | 1 |
| multilingual-e5-large | Tajwid | 0.718 [0.47, 0.92] | -0.083 [-0.21, +0.00] | 1.000 [1.00, 1.00] | +0.000 [+0.00, +0.00] | 4 |
| multilingual-e5-base | All | 0.711 [0.59, 0.82] | **-0.112 [-0.20, -0.04]** | 0.987 [0.96, 1.00] | +0.005 [+0.00, +0.01] | 11 |
| multilingual-e5-base | Ibadah | 0.677 [0.44, 0.87] | -0.033 [-0.11, +0.01] | 0.974 [0.92, 1.00] | +0.015 [+0.00, +0.05] | 4 |
| multilingual-e5-base | Jawi | 0.957 [0.91, 1.00] | +0.000 [+0.00, +0.00] | 0.989 [0.97, 1.00] | +0.000 [+0.00, +0.00] | 0 |
| multilingual-e5-base | Tajwid | 0.498 [0.25, 0.73] | **-0.303 [-0.52, -0.11]** | 1.000 [1.00, 1.00] | +0.000 [+0.00, +0.00] | 7 |

## Selection

| Group | Selected |
|---|---|
| All | bge-m3 |
| Ibadah | bge-m3 |
| Jawi | bge-m3 |
| Tajwid | bge-m3 |
