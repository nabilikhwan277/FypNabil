# RAG settings study of R3 Parent-Document RAG: detailed tables

45 answerable questions (15 per subject) + 24 out-of-syllabus questions · answer model GPT-6 Luna · judge Claude Haiku 5.5. Mean [95% bootstrap CI]. One setting is changed at a time; the others stay at the current value.

## 1. Chunk size

*What it is:* characters per chunk; chunks are matched, then their whole sections are passed (R3).

| Option | Hit rate | Evidence recall | Precision | MRR | Sections read | Characters read | Faithfulness | Factual correctness | Declined (of 45) | Off-syllabus declined (of 24) |
|---|---|---|---|---|---|---|---|---|---|---|
| 300 | 0.978 [0.93, 1.00] | 0.910 [0.84, 0.97] | 0.937 [0.87, 0.98] | 0.944 [0.88, 0.99] | 2.22 | 2,151 | 0.966 [0.93, 0.99] | 0.787 [0.68, 0.88] | 6 | 24 |
| 600 | 0.933 [0.87, 1.00] | 0.882 [0.80, 0.96] | 0.867 [0.78, 0.94] | 0.878 [0.79, 0.96] | 2.38 | 2,179 | 0.974 [0.94, 1.00] | 0.765 [0.66, 0.87] | 6 | 24 |
| 1,000 | 0.978 [0.93, 1.00] | 0.904 [0.83, 0.96] | 0.911 [0.85, 0.96] | 0.922 [0.86, 0.98] | 2.44 | 2,131 | 0.980 [0.95, 1.00] | 0.802 [0.70, 0.89] | 5 | 24 |
| 1,500 **(current)** | 0.978 [0.93, 1.00] | 0.920 [0.86, 0.98] | 0.907 [0.84, 0.96] | 0.922 [0.86, 0.98] | 2.44 | 2,125 | 0.984 [0.96, 1.00] | 0.823 [0.73, 0.91] | 5 | 24 |
| whole section | 0.978 [0.93, 1.00] | 0.902 [0.83, 0.97] | 0.907 [0.84, 0.96] | 0.922 [0.86, 0.98] | 2.49 | 2,111 | 0.974 [0.94, 1.00] | 0.823 [0.73, 0.91] | 5 | 24 |

**Change from the current option (factual correctness)**

| Option | Change | 95% CI | Clear? (interval leaves out 0) |
|---|---|---|---|
| 300 | -0.036 | [-0.097, +0.011] | no |
| 600 | -0.058 | [-0.136, +0.007] | no |
| 1,000 | -0.021 | [-0.067, +0.004] | no |
| whole section | +0.000 | [+0.000, +0.000] | no |

**Per subject (factual correctness; change from current in brackets)**

| Option | Ibadah | Jawi | Tajwid |
|---|---|---|---|
| 300 | 0.670 (-0.041) | 0.993 (+0.036) | 0.699 (-0.102, clear) |
| 600 | 0.710 (+0.000) | 0.846 (-0.111) | 0.738 (-0.063) |
| 1,000 | 0.710 (+0.000) | 0.957 (+0.000) | 0.738 (-0.063) |
| 1,500 | 0.710 | 0.957 | 0.801 |
| whole section | 0.710 (+0.000) | 0.957 (+0.000) | 0.801 (+0.000) |

**Evidence:** 300, 600, 1,000 and whole section: no clear difference (factual correctness 0.79, 0.76, 0.80 and 0.82 vs 0.82).

**Selection:** 1,500 (current): no option is clearly better

## 2. Number of sections (k)

*What it is:* how many different textbook sections the answer model is given.

| Option | Hit rate | Evidence recall | Precision | MRR | Sections read | Characters read | Faithfulness | Factual correctness | Declined (of 45) | Off-syllabus declined (of 24) |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.867 [0.76, 0.96] | 0.683 [0.57, 0.80] | 0.867 [0.76, 0.96] | 0.867 [0.76, 0.96] | 1.00 | 1,252 | 0.986 [0.96, 1.00] | 0.608 [0.48, 0.74] | 16 | 24 |
| 2 | 0.978 [0.93, 1.00] | 0.881 [0.80, 0.95] | 0.922 [0.86, 0.98] | 0.922 [0.86, 0.98] | 1.76 | 1,748 | 0.988 [0.97, 1.00] | 0.776 [0.67, 0.88] | 8 | 24 |
| 3 **(current)** | 0.978 [0.93, 1.00] | 0.920 [0.86, 0.98] | 0.907 [0.84, 0.96] | 0.922 [0.86, 0.98] | 2.44 | 2,125 | 0.984 [0.96, 1.00] | 0.823 [0.73, 0.91] | 5 | 24 |
| 5 | 0.978 [0.93, 1.00] | 0.947 [0.89, 1.00] | 0.899 [0.84, 0.95] | 0.922 [0.86, 0.98] | 3.56 | 2,824 | 0.990 [0.97, 1.00] | 0.863 [0.78, 0.93] | 3 | 24 |
| 10 | 0.978 [0.93, 1.00] | 0.947 [0.89, 1.00] | 0.892 [0.83, 0.95] | 0.922 [0.86, 0.98] | 4.13 | 3,117 | 0.990 [0.97, 1.00] | 0.869 [0.79, 0.94] | 3 | 24 |

**Change from the current option (factual correctness)**

| Option | Change | 95% CI | Clear? (interval leaves out 0) |
|---|---|---|---|
| 1 | -0.214 | [-0.328, -0.111] | yes |
| 2 | -0.047 | [-0.103, +0.001] | no |
| 5 | +0.040 | [+0.000, +0.090] | yes |
| 10 | +0.046 | [+0.001, +0.105] | yes |

**Per subject (factual correctness; change from current in brackets)**

| Option | Ibadah | Jawi | Tajwid |
|---|---|---|---|
| 1 | 0.486 (-0.224, clear) | 0.913 (-0.044) | 0.427 (-0.374, clear) |
| 2 | 0.692 (-0.018) | 0.957 (+0.000) | 0.678 (-0.123, clear) |
| 3 | 0.710 | 0.957 | 0.801 |
| 5 | 0.759 (+0.048) | 0.957 (+0.000) | 0.873 (+0.072) |
| 10 | 0.780 (+0.070) | 0.957 (+0.000) | 0.870 (+0.069) |

**Evidence:** 1: lower factual correctness (0.61 vs 0.82), lower evidence recall (0.68 vs 0.92), lower hit rate (0.87 vs 0.98), 16 vs 5 declined, 0.6× the text; 2: lower evidence recall (0.88 vs 0.92), higher precision (0.92 vs 0.91), 8 vs 5 declined, 0.8× the text; 5: higher factual correctness (0.86 vs 0.82), lower precision (0.90 vs 0.91), 3 vs 5 declined, 1.3× the text; 10: higher factual correctness (0.87 vs 0.82), lower precision (0.89 vs 0.91), 3 vs 5 declined, 1.5× the text.

**Selection:** 5: clearly higher factual correctness (0.86 vs 0.82), with 1.3× the text; 10 adds no clear gain over it

## 3. Context limit

*What it is:* characters of the passed sections the answer model reads.

| Option | Hit rate | Evidence recall | Precision | MRR | Sections read | Characters read | Faithfulness | Factual correctness | Declined (of 45) | Off-syllabus declined (of 24) |
|---|---|---|---|---|---|---|---|---|---|---|
| 1,800 | 0.867 [0.78, 0.96] | 0.770 [0.67, 0.87] | 0.826 [0.73, 0.92] | 0.833 [0.73, 0.92] | 2.00 | 1,359 | 0.962 [0.91, 1.00] | 0.681 [0.56, 0.80] | 11 | 24 |
| 3,600 **(current)** | 0.978 [0.93, 1.00] | 0.920 [0.86, 0.98] | 0.907 [0.84, 0.96] | 0.922 [0.86, 0.98] | 2.44 | 2,125 | 0.984 [0.96, 1.00] | 0.823 [0.73, 0.91] | 5 | 24 |
| 7,200 | 0.978 [0.93, 1.00] | 0.920 [0.86, 0.98] | 0.907 [0.84, 0.96] | 0.922 [0.86, 0.98] | 2.67 | 2,703 | 0.984 [0.96, 1.00] | 0.823 [0.73, 0.91] | 5 | 24 |
| no limit | 0.978 [0.93, 1.00] | 0.920 [0.86, 0.98] | 0.907 [0.84, 0.96] | 0.922 [0.86, 0.98] | 2.84 | 3,301 | 0.989 [0.97, 1.00] | 0.823 [0.73, 0.91] | 5 | 24 |

**Change from the current option (factual correctness)**

| Option | Change | 95% CI | Clear? (interval leaves out 0) |
|---|---|---|---|
| 1,800 | -0.142 | [-0.244, -0.051] | yes |
| 7,200 | +0.000 | [+0.000, +0.000] | no |
| no limit | +0.000 | [+0.000, +0.000] | no |

**Per subject (factual correctness; change from current in brackets)**

| Option | Ibadah | Jawi | Tajwid |
|---|---|---|---|
| 1,800 | 0.704 (-0.007) | 0.713 (-0.244, clear) | 0.626 (-0.175, clear) |
| 3,600 | 0.710 | 0.957 | 0.801 |
| 7,200 | 0.710 (+0.000) | 0.957 (+0.000) | 0.801 (+0.000) |
| no limit | 0.710 (+0.000) | 0.957 (+0.000) | 0.801 (+0.000) |

**Evidence:** 1,800: lower factual correctness (0.68 vs 0.82), lower evidence recall (0.77 vs 0.92), lower hit rate (0.87 vs 0.98), 11 vs 5 declined, 0.6× the text; 7,200 and no limit: no clear difference (factual correctness 0.82 and 0.82 vs 0.82).

**Selection:** 3,600 (current): no option is clearly better

## 4. Minimum similarity

*What it is:* matched chunks with a lower bge-m3 cosine are dropped; no chunk left = decline.

| Threshold | Matched chunks removed | Answerable rejected (of 45) | Hit rate | Evidence recall | General off-syllabus rejected (of 12) | Near-syllabus rejected (of 12) |
|---|---|---|---|---|---|---|
| 0.00 (current) | 0% | 0 | 0.978 | 0.920 | 0 | 0 |
| 0.30 | 1% | 0 | 0.978 | 0.920 | 0 | 0 |
| 0.35 | 2% | 0 | 0.978 | 0.920 | 2 | 0 |
| 0.40 | 4% | 1 | 0.956 | 0.898 | 7 | 1 |
| 0.45 | 9% | 1 | 0.956 | 0.898 | 9 | 2 |
| 0.50 | 14% | 2 | 0.933 | 0.876 | 11 | 6 |
| 0.55 | 25% | 5 | 0.844 | 0.787 | 12 | 10 |
| 0.60 | 44% | 13 | 0.711 | 0.654 | 12 | 12 |
| 0.65 | 62% | 17 | 0.600 | 0.550 | 12 | 12 |
| 0.70 | 87% | 30 | 0.333 | 0.247 | 12 | 12 |
| 0.75 | 98% | 41 | 0.089 | 0.058 | 12 | 12 |
| 0.80 | 100% | 45 | 0.000 | 0.000 | 12 | 12 |
| 0.85 | 100% | 45 | 0.000 | 0.000 | 12 | 12 |

Best-match cosine: answerable 0.37–0.77, general off-syllabus up to 0.52, near-syllabus up to 0.59.

**Evidence:** Best-match cosine: answerable questions 0.37–0.77, general out-of-syllabus up to 0.52, near-syllabus up to 0.59, so no threshold separates them; 0.35 is the highest that loses no answerable question or evidence (it rejects 2/12 general and 0/12 near-syllabus ones); rejecting every out-of-syllabus question needs 0.60, which also rejects 13/45 answerable ones; Tanya Bulan's gate (0.55 on its best match in the subject) turns away 5/45 answerable questions.

**Selection:** 0.35 as a safeguard that loses no answerable question; out-of-syllabus questions are left to the answer model's decline rule (24/24 declined)

## 5. Query variants

*What it is:* two rewrites of the question (by the answer model) are searched as well.

| Option | Hit rate | Evidence recall | Precision | MRR | Sections read | Characters read |
|---|---|---|---|---|---|---|
| none **(current)** | 0.978 [0.93, 1.00] | 0.920 [0.86, 0.98] | 0.907 [0.84, 0.96] | 0.922 [0.86, 0.98] | 2.44 | 2,125 |
| 2 rewrites + RRF fusion | 0.978 [0.93, 1.00] | 0.896 [0.82, 0.96] | 0.907 [0.84, 0.96] | 0.919 [0.85, 0.97] | 2.44 | 2,255 |
| 2 rewrites + round-robin | 0.978 [0.93, 1.00] | 0.909 [0.84, 0.97] | 0.911 [0.84, 0.97] | 0.919 [0.85, 0.98] | 2.44 | 2,133 |

**Change from the current option (evidence recall)**

| Option | Change | 95% CI | Clear? (interval leaves out 0) |
|---|---|---|---|
| 2 rewrites + RRF fusion | -0.024 | [-0.064, +0.005] | no |
| 2 rewrites + round-robin | -0.011 | [-0.033, +0.000] | no |

**Per subject (evidence recall; change from current in brackets)**

| Option | Ibadah | Jawi | Tajwid |
|---|---|---|---|
| none | 0.902 | 1.000 | 0.859 |
| 2 rewrites + RRF fusion | 0.887 (-0.015) | 0.956 (-0.044) | 0.846 (-0.014) |
| 2 rewrites + round-robin | 0.902 (+0.000) | 1.000 (+0.000) | 0.826 (-0.033) |

**Evidence:** 2 rewrites + RRF fusion and 2 rewrites + round-robin: no clear difference (evidence recall 0.90 and 0.91 vs 0.92).

**Selection:** none (current): no option is clearly better

## 6. Search scope

*What it is:* which notes are searched.

| Option | Hit rate | Evidence recall | Precision | MRR | Sections read | Characters read |
|---|---|---|---|---|---|---|
| all notes | 0.978 [0.93, 1.00] | 0.920 [0.86, 0.98] | 0.904 [0.84, 0.96] | 0.922 [0.86, 0.98] | 2.51 | 2,195 |
| subject **(current)** | 0.978 [0.93, 1.00] | 0.920 [0.86, 0.98] | 0.907 [0.84, 0.96] | 0.922 [0.86, 0.98] | 2.44 | 2,125 |
| topic first | 0.978 [0.93, 1.00] | 0.930 [0.87, 0.98] | 0.909 [0.84, 0.97] | 0.911 [0.84, 0.97] | 2.29 | 2,038 |

**Change from the current option (evidence recall)**

| Option | Change | 95% CI | Clear? (interval leaves out 0) |
|---|---|---|---|
| all notes | +0.000 | [+0.000, +0.000] | no |
| topic first | +0.010 | [-0.004, +0.029] | no |

**Per subject (evidence recall; change from current in brackets)**

| Option | Ibadah | Jawi | Tajwid |
|---|---|---|---|
| all notes | 0.902 (+0.000) | 1.000 (+0.000) | 0.859 (+0.000) |
| subject | 0.902 | 1.000 | 0.859 |
| topic first | 0.917 (+0.014) | 1.000 (+0.000) | 0.874 (+0.015) |

**Evidence:** all notes and topic first: no clear difference (evidence recall 0.92 and 0.93 vs 0.92).

**Selection:** subject (current): no option is clearly better; topic first where the question's topic is known (marking)

## 7. Matching method

*What it is:* how chunks are matched to the question.

| Option | Hit rate | Evidence recall | Precision | MRR | Sections read | Characters read |
|---|---|---|---|---|---|---|
| bge-m3 only | 0.978 [0.93, 1.00] | 0.925 [0.86, 0.98] | 0.902 [0.83, 0.96] | 0.904 [0.83, 0.97] | 2.47 | 2,216 |
| BM25 only | 0.933 [0.84, 1.00] | 0.848 [0.76, 0.93] | 0.863 [0.77, 0.94] | 0.885 [0.80, 0.96] | 2.49 | 2,187 |
| hybrid bge-m3 + BM25 **(current)** | 0.978 [0.93, 1.00] | 0.920 [0.86, 0.98] | 0.907 [0.84, 0.96] | 0.922 [0.86, 0.98] | 2.44 | 2,125 |

**Change from the current option (evidence recall)**

| Option | Change | 95% CI | Clear? (interval leaves out 0) |
|---|---|---|---|
| bge-m3 only | +0.005 | [-0.022, +0.035] | no |
| BM25 only | -0.072 | [-0.147, -0.016] | yes |

**Per subject (evidence recall; change from current in brackets)**

| Option | Ibadah | Jawi | Tajwid |
|---|---|---|---|
| bge-m3 only | 0.913 (+0.011) | 1.000 (+0.000) | 0.863 (+0.004) |
| BM25 only | 0.895 (-0.007) | 1.000 (+0.000) | 0.649 (-0.210, clear) |
| hybrid bge-m3 + BM25 | 0.902 | 1.000 | 0.859 |

**Evidence:** BM25 only: lower evidence recall (0.85 vs 0.92); bge-m3 only: no clear difference (evidence recall 0.93 vs 0.92).

**Selection:** hybrid bge-m3 + BM25 (current): no option is clearly better; the keyword side is what finds questions typed in Jawi

## 8. Jawi-script questions

*What it is:* bge-m3 weight in the fusion when the question is typed in Jawi.

| Option | Hit rate | Evidence recall | Precision | MRR | Sections read | Characters read |
|---|---|---|---|---|---|---|
| Rumi (same questions) | 0.978 [0.93, 1.00] | 0.920 [0.86, 0.98] | 0.907 [0.84, 0.96] | 0.922 [0.86, 0.98] | 2.44 | 2,125 |
| weight 0 | 0.933 [0.87, 1.00] | 0.820 [0.72, 0.91] | 0.828 [0.73, 0.91] | 0.833 [0.74, 0.92] | 2.47 | 2,304 |
| weight 0.25 **(current)** | 0.911 [0.82, 0.98] | 0.794 [0.69, 0.89] | 0.830 [0.73, 0.92] | 0.837 [0.74, 0.93] | 2.44 | 2,208 |
| weight 0.5 | 0.889 [0.80, 0.98] | 0.753 [0.64, 0.86] | 0.798 [0.70, 0.89] | 0.796 [0.70, 0.89] | 2.47 | 2,170 |
| weight 1 | 0.889 [0.80, 0.98] | 0.775 [0.66, 0.87] | 0.783 [0.68, 0.88] | 0.781 [0.67, 0.88] | 2.47 | 2,126 |

**Change from the current option (evidence recall)**

| Option | Change | 95% CI | Clear? (interval leaves out 0) |
|---|---|---|---|
| Rumi (same questions) | +0.127 | [+0.026, +0.235] | yes |
| weight 0 | +0.026 | [-0.030, +0.089] | no |
| weight 0.5 | -0.041 | [-0.096, +0.000] | no |
| weight 1 | -0.019 | [-0.053, +0.009] | no |

**Per subject (evidence recall; change from current in brackets)**

| Option | Ibadah | Jawi | Tajwid |
|---|---|---|---|
| Rumi (same questions) | 0.902 (+0.255, clear) | 1.000 (+0.044) | 0.859 (+0.080) |
| weight 0 | 0.724 (+0.077) | 0.956 (+0.000) | 0.779 (+0.000) |
| weight 0.25 | 0.647 | 0.956 | 0.779 |
| weight 0.5 | 0.647 (+0.000) | 0.856 (-0.100) | 0.757 (-0.022) |
| weight 1 | 0.667 (+0.020) | 0.900 (-0.056) | 0.757 (-0.022) |

**Evidence:** The same questions typed in Jawi reach evidence recall 0.79 vs 0.92 in Rumi; weight 0, weight 0.5 and weight 1: no clear difference (evidence recall 0.82, 0.75 and 0.77 vs 0.79).

**Selection:** weight 0.25 (current): no option is clearly better

