# RAG settings study: R3 Parent-Document RAG

One setting changed at a time, the others at the current value. 45 answerable + 24 out-of-syllabus questions (as rag_eval.py) · answer model GPT-6 Luna · judge Claude Haiku 5.5 · 2026-10-25

| Setting | Options tested | Evidence | Selection |
|---|---|---|---|
| Chunk size | 300, 600, 1,000 and 1,500 characters, and whole sections | 300, 600, 1,000 and whole section: no clear difference (factual correctness 0.79, 0.76, 0.80 and 0.82 vs 0.82). | 1,500 (current): no option is clearly better |
| Number of sections (k) | 1, 2, 3, 5 and 10 sections | 1: lower factual correctness (0.61 vs 0.82), lower evidence recall (0.68 vs 0.92), lower hit rate (0.87 vs 0.98), 16 vs 5 declined, 0.6× the text; 2: lower evidence recall (0.88 vs 0.92), higher precision (0.92 vs 0.91), 8 vs 5 declined, 0.8× the text; 5: higher factual correctness (0.86 vs 0.82), lower precision (0.90 vs 0.91), 3 vs 5 declined, 1.3× the text; 10: higher factual correctness (0.87 vs 0.82), lower precision (0.89 vs 0.91), 3 vs 5 declined, 1.5× the text. | 5: clearly higher factual correctness (0.86 vs 0.82), with 1.3× the text; 10 adds no clear gain over it |
| Context limit | 1,800, 3,600 and 7,200 characters, and no limit | 1,800: lower factual correctness (0.68 vs 0.82), lower evidence recall (0.77 vs 0.92), lower hit rate (0.87 vs 0.98), 11 vs 5 declined, 0.6× the text; 7,200 and no limit: no clear difference (factual correctness 0.82 and 0.82 vs 0.82). | 3,600 (current): no option is clearly better |
| Minimum similarity | 0 (none) to 0.85 (13 steps) | Best-match cosine: answerable questions 0.37–0.77, general out-of-syllabus up to 0.52, near-syllabus up to 0.59, so no threshold separates them; 0.35 is the highest that loses no answerable question or evidence (it rejects 2/12 general and 0/12 near-syllabus ones); rejecting every out-of-syllabus question needs 0.60, which also rejects 13/45 answerable ones; Tanya Bulan's gate (0.55 on its best match in the subject) turns away 5/45 answerable questions. | 0.35 as a safeguard that loses no answerable question; out-of-syllabus questions are left to the answer model's decline rule (24/24 declined) |
| Query variants | none, 2 rewrites + RRF fusion and 2 rewrites + round-robin | 2 rewrites + RRF fusion and 2 rewrites + round-robin: no clear difference (evidence recall 0.90 and 0.91 vs 0.92). | none (current): no option is clearly better |
| Search scope | all notes, subject and topic first | all notes and topic first: no clear difference (evidence recall 0.92 and 0.93 vs 0.92). | subject (current): no option is clearly better; topic first where the question's topic is known (marking) |
| Matching method | bge-m3 only, BM25 only and hybrid bge-m3 + BM25 | BM25 only: lower evidence recall (0.85 vs 0.92); bge-m3 only: no clear difference (evidence recall 0.93 vs 0.92). | hybrid bge-m3 + BM25 (current): no option is clearly better; the keyword side is what finds questions typed in Jawi |
| Jawi-script questions | bge-m3 weight 0, 0.25, 0.5 and 1 for questions typed in Jawi | The same questions typed in Jawi reach evidence recall 0.79 vs 0.92 in Rumi; weight 0, weight 0.5 and weight 1: no clear difference (evidence recall 0.82, 0.75 and 0.77 vs 0.79). | weight 0.25 (current): no option is clearly better |

Evidence uses the gold evidence (textbook lines that state each statement of the reference answer, judged once: 207 of 208 statements are in the notes). 'Clear' = the 95% paired bootstrap interval of the change leaves out 0.

## Chunk size

characters per chunk; chunks are matched, then their whole sections are passed (R3)

| Option | Hit rate | Evidence recall | Precision | MRR | Sections read | Characters | Faithfulness | Factual correctness | Declined | Out-of-syllabus declined |
|---|---|---|---|---|---|---|---|---|---|---|
| 300 | 0.98 | 0.91 | 0.94 | 0.94 | 2.22 | 2151 | 0.97 | 0.79 | 6 | 24 |
| 600 | 0.93 | 0.88 | 0.87 | 0.88 | 2.38 | 2179 | 0.97 | 0.76 | 6 | 24 |
| 1,000 | 0.98 | 0.90 | 0.91 | 0.92 | 2.44 | 2131 | 0.98 | 0.80 | 5 | 24 |
| 1,500 (current) | 0.98 | 0.92 | 0.91 | 0.92 | 2.44 | 2125 | 0.98 | 0.82 | 5 | 24 |
| whole section | 0.98 | 0.90 | 0.91 | 0.92 | 2.49 | 2111 | 0.97 | 0.82 | 5 | 24 |

## Number of sections (k)

how many different textbook sections the answer model is given

| Option | Hit rate | Evidence recall | Precision | MRR | Sections read | Characters | Faithfulness | Factual correctness | Declined | Out-of-syllabus declined |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.87 | 0.68 | 0.87 | 0.87 | 1.00 | 1252 | 0.99 | 0.61 | 16 | 24 |
| 2 | 0.98 | 0.88 | 0.92 | 0.92 | 1.76 | 1748 | 0.99 | 0.78 | 8 | 24 |
| 3 (current) | 0.98 | 0.92 | 0.91 | 0.92 | 2.44 | 2125 | 0.98 | 0.82 | 5 | 24 |
| 5 | 0.98 | 0.95 | 0.90 | 0.92 | 3.56 | 2824 | 0.99 | 0.86 | 3 | 24 |
| 10 | 0.98 | 0.95 | 0.89 | 0.92 | 4.13 | 3117 | 0.99 | 0.87 | 3 | 24 |

## Context limit

characters of the passed sections the answer model reads

| Option | Hit rate | Evidence recall | Precision | MRR | Sections read | Characters | Faithfulness | Factual correctness | Declined | Out-of-syllabus declined |
|---|---|---|---|---|---|---|---|---|---|---|
| 1,800 | 0.87 | 0.77 | 0.83 | 0.83 | 2.00 | 1359 | 0.96 | 0.68 | 11 | 24 |
| 3,600 (current) | 0.98 | 0.92 | 0.91 | 0.92 | 2.44 | 2125 | 0.98 | 0.82 | 5 | 24 |
| 7,200 | 0.98 | 0.92 | 0.91 | 0.92 | 2.67 | 2703 | 0.98 | 0.82 | 5 | 24 |
| no limit | 0.98 | 0.92 | 0.91 | 0.92 | 2.84 | 3301 | 0.99 | 0.82 | 5 | 24 |

## Minimum similarity

| Threshold | Chunks removed | Answerable rejected | Hit rate | Evidence recall | General rejected | Near rejected |
|---|---|---|---|---|---|---|
| 0.00 | 0% | 0/45 | 0.98 | 0.92 | 0/12 | 0/12 |
| 0.30 | 1% | 0/45 | 0.98 | 0.92 | 0/12 | 0/12 |
| 0.35 | 2% | 0/45 | 0.98 | 0.92 | 2/12 | 0/12 |
| 0.40 | 4% | 1/45 | 0.96 | 0.90 | 7/12 | 1/12 |
| 0.45 | 9% | 1/45 | 0.96 | 0.90 | 9/12 | 2/12 |
| 0.50 | 14% | 2/45 | 0.93 | 0.88 | 11/12 | 6/12 |
| 0.55 | 25% | 5/45 | 0.84 | 0.79 | 12/12 | 10/12 |
| 0.60 | 44% | 13/45 | 0.71 | 0.65 | 12/12 | 12/12 |
| 0.65 | 62% | 17/45 | 0.60 | 0.55 | 12/12 | 12/12 |
| 0.70 | 87% | 30/45 | 0.33 | 0.25 | 12/12 | 12/12 |
| 0.75 | 98% | 41/45 | 0.09 | 0.06 | 12/12 | 12/12 |
| 0.80 | 100% | 45/45 | 0.00 | 0.00 | 12/12 | 12/12 |
| 0.85 | 100% | 45/45 | 0.00 | 0.00 | 12/12 | 12/12 |

Tanya Bulan's gate (0.55 on its best bge-m3 match in the subject): 5/45 answerable, 12/12 general and 10/12 near-syllabus questions turned away.

## Query variants

two rewrites of the question (by the answer model) are searched as well

| Option | Hit rate | Evidence recall | Precision | MRR | Sections read | Characters |
|---|---|---|---|---|---|---|
| none (current) | 0.98 | 0.92 | 0.91 | 0.92 | 2.44 | 2125 |
| 2 rewrites + RRF fusion | 0.98 | 0.90 | 0.91 | 0.92 | 2.44 | 2255 |
| 2 rewrites + round-robin | 0.98 | 0.91 | 0.91 | 0.92 | 2.44 | 2133 |

## Search scope

which notes are searched

| Option | Hit rate | Evidence recall | Precision | MRR | Sections read | Characters |
|---|---|---|---|---|---|---|
| all notes | 0.98 | 0.92 | 0.90 | 0.92 | 2.51 | 2195 |
| subject (current) | 0.98 | 0.92 | 0.91 | 0.92 | 2.44 | 2125 |
| topic first | 0.98 | 0.93 | 0.91 | 0.91 | 2.29 | 2038 |

## Matching method

how chunks are matched to the question

| Option | Hit rate | Evidence recall | Precision | MRR | Sections read | Characters |
|---|---|---|---|---|---|---|
| bge-m3 only | 0.98 | 0.93 | 0.90 | 0.90 | 2.47 | 2216 |
| BM25 only | 0.93 | 0.85 | 0.86 | 0.89 | 2.49 | 2187 |
| hybrid bge-m3 + BM25 (current) | 0.98 | 0.92 | 0.91 | 0.92 | 2.44 | 2125 |

## Jawi-script questions

bge-m3 weight in the fusion when the question is typed in Jawi

| Option | Hit rate | Evidence recall | Precision | MRR | Sections read | Characters |
|---|---|---|---|---|---|---|
| Rumi (same questions) | 0.98 | 0.92 | 0.91 | 0.92 | 2.44 | 2125 |
| weight 0 | 0.93 | 0.82 | 0.83 | 0.83 | 2.47 | 2304 |
| weight 0.25 (current) | 0.91 | 0.79 | 0.83 | 0.84 | 2.44 | 2208 |
| weight 0.5 | 0.89 | 0.75 | 0.80 | 0.80 | 2.47 | 2170 |
| weight 1 | 0.89 | 0.77 | 0.78 | 0.78 | 2.47 | 2126 |

## Check: the RAG types on the same gold evidence

| RAG type | Hit rate | Evidence recall | Precision | MRR | Judge context recall | Mean abs. difference | Pearson r |
|---|---|---|---|---|---|---|---|
| R1 | 0.91 | 0.83 | 0.86 | 0.86 | 0.85 | 0.02 | 0.98 |
| R2 | 0.93 | 0.86 | 0.91 | 0.91 | 0.86 | 0.01 | 0.99 |
| R3 | 0.98 | 0.92 | 0.91 | 0.92 | 0.93 | 0.01 | 0.99 |
