# RAG evaluation (mean over 45 answerable questions)

Answer model: GPT-6 Luna (fixed) · judge: Claude Haiku 5.5 · embedding: bge-m3 · 2026-10-25

| Metric | R1 Naive Dense RAG | R2 Hybrid RAG + Reranker | R3 Parent-Document RAG |
|---|---|---|---|
| Context precision | 0.851 | 0.935 | 0.917 |
| Context recall | 0.848 | 0.862 | 0.930 |
| Faithfulness | 0.979 | 0.968 | 0.984 |
| Answer relevancy | 0.614 | 0.584 | 0.662 |
| Factual correctness | 0.771 | 0.753 | 0.823 |
| Declined answers (of 45) | 8 | 10 | 5 |
| Out-of-syllabus correctly declined (of 24) | 24 | 24 | 24 |
| - general (of 12) | 12 | 12 | 12 |
| - near the syllabus (of 12) | 12 | 12 | 12 |
| Passages retrieved → read by the model (mean) | 4 → 2.04 | 4 → 1.87 | 2.84 → 2.44 |
| Characters read (mean) | 1358 | 1336 | 2125 |
| Retrieval time (ms) | 173 | 21405 | 35 |
