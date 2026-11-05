# Result tables (final teacher marks, 50 answers, 3 teachers)

QWK with a 95% bootstrap interval; * = significantly different from the final system (proposed:luna:R3:A2:off).

## Step 1 · LLM models (R1, A2, memory off)

| Configuration | QWK | 95% CI | Exact | Within 1 mark (2+ marks) | vs final system (p) | API cost / 100 answers | Time / answer |
|---|---|---|---|---|---|---|---|
| Claude Haiku 5.5 · R1 · A2 | 0.723 | 0.525–0.882 | 62% | 85% | -0.032 (p=0.492) | $0.050 | 9.0 s |
| GPT-6 Luna · R1 · A2 | 0.7 | 0.494–0.866 | 60% | 85% | -0.055 (p=0.265) | $0.029 | 3.3 s |
| Llama 3.1 8B · R1 · A2 | 0.538 | 0.334–0.728 | 54% | 74% | -0.217 (p=0.025) * | $0.036 | 2.3 s |

## Step 0 · Baselines (GPT-6 Luna) vs the proposed system

| Configuration | QWK | 95% CI | Exact | Within 1 mark (2+ marks) | vs final system (p) | API cost / 100 answers |
|---|---|---|---|---|---|---|
| B2 Rules + bge-m3 | 0.476 | 0.217–0.698 | 48% | 62% | -0.279 (p=0.001) * | $0.000 |
| B1 Zero-shot | 0.683 | 0.474–0.851 | 60% | 85% | -0.072 (p=0.061) | $0.019 |
| B3 RAG + rubric | 0.681 | 0.467–0.85 | 58% | 85% | -0.074 (p=0.096) | $0.023 |
| B4 RAG + verifier | 0.681 | 0.467–0.85 | 58% | 85% | -0.074 (p=0.096) | $0.043 |
| GPT-6 Luna · R3 · A2 | 0.755 | 0.576–0.895 | 62% | 85% | final system | $0.030 |

## Step 2 · RAG types (GPT-6 Luna, A2)

| Configuration | QWK | 95% CI | Exact | Within 1 mark (2+ marks) | vs final system (p) | API cost / 100 answers |
|---|---|---|---|---|---|---|
| GPT-6 Luna · R1 · A2 | 0.7 | 0.494–0.866 | 60% | 85% | -0.055 (p=0.265) | $0.029 |
| GPT-6 Luna · R2 · A2 | 0.7 | 0.494–0.866 | 60% | 85% | -0.055 (p=0.265) | $0.026 |
| GPT-6 Luna · R3 · A2 | 0.755 | 0.576–0.895 | 62% | 85% | final system | $0.030 |

## RAG evaluation (RAGAS, 45 questions + 24 out-of-syllabus)

| Metric | R1 | R2 | R3 |
|---|---|---|---|
| Context precision | 0.851 | 0.935 | 0.917 |
| Context recall | 0.848 | 0.862 | 0.930 |
| Faithfulness | 0.979 | 0.968 | 0.984 |
| Answer relevancy | 0.614 | 0.584 | 0.662 |
| Factual correctness | 0.771 | 0.753 | 0.823 |
| Declined answers (of 45) | 8 | 10 | 5 |
| Out-of-syllabus declined (of 24) | 24 | 24 | 24 |
| Retrieval time | 173 ms | 21405 ms | 35 ms |

## RAG settings study of R3

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

## Step 3 · ReAct types (GPT-6 Luna, R3)

| Configuration | QWK | 95% CI | Exact | Within 1 mark (2+ marks) | vs final system (p) | AI calls / answer | API cost / 100 answers | Time / answer |
|---|---|---|---|---|---|---|---|---|
| GPT-6 Luna · R3 · A1 | 0.7 | 0.494–0.866 | 62% | 85% | -0.055 (p=0.265) | 3.0 | $0.080 | 14.1 s |
| GPT-6 Luna · R3 · A2 | 0.755 | 0.576–0.895 | 62% | 85% | final system | 1.0 | $0.030 | 3.5 s |
| GPT-6 Luna · R3 · A3 | 0.722 | 0.524–0.885 | 64% | 85% | -0.033 (p=0.728) | 2.0 | $0.053 | 4.7 s |

## Step 4 · Memory (GPT-6 Luna, R3, A2; 3 repeats)

| Configuration | QWK | 95% CI | Exact | Within 1 mark (2+ marks) | vs final system (p) | Same score in 3 runs | CoV |
|---|---|---|---|---|---|---|---|
| GPT-6 Luna · R3 · A2 | 0.755 | 0.576–0.895 | 62% | 85% | final system | 94% | 7.66% |
| GPT-6 Luna · R3 · A2 · memory on | 0.736 | 0.547–0.88 | 60% | 85% | -0.019 (p=0.291) | 98% | 0.59% |

## E1 · Agreement with each teacher (human baseline 0.449, 95% CI 0.267–0.618)

| Configuration | guru 1 | guru 2 | guru 3 | Mean | Criterion kappa |
|---|---|---|---|---|---|
| qwen+luna · R3 · A2 | 0.784 | 0.5 | 0.491 | 0.592 | 0.557 |
| qwen+luna · R3 · A2 | 0.784 | 0.454 | 0.512 | 0.583 | 0.523 |
| GPT-6 Luna · R3 · A2 | 0.76 | 0.464 | 0.555 | 0.593 | 0.509 |
| qwen_ft_r16e2 · R3 · A2 | 0.794 | 0.405 | 0.497 | 0.565 | 0.511 |
| qwen_ft_r8e1 · R3 · A2 | 0.774 | 0.428 | 0.485 | 0.562 | 0.506 |
| qwen+luna · R3 · A2 | 0.743 | 0.455 | 0.546 | 0.581 | 0.469 |
| GPT-6 Luna · R3 · A2 · memory on | 0.755 | 0.484 | 0.534 | 0.591 | 0.484 |
| qwen_ft_r8e2+luna · R3 · A2 | 0.766 | 0.448 | 0.48 | 0.565 | 0.523 |
| Claude Haiku 5.5 · R3 · A2 | 0.776 | 0.388 | 0.505 | 0.556 | 0.512 |
| Claude Haiku 5.5 · R1 · A2 | 0.769 | 0.381 | 0.528 | 0.559 | 0.502 |
| GPT-6 Luna · R3 · A3 | 0.755 | 0.423 | 0.524 | 0.567 | 0.506 |
| qwen_ft_r8e2+luna · R3 · A2 | 0.782 | 0.359 | 0.484 | 0.542 | 0.504 |
| qwen_ft_r8e2+luna · R3 · A2 | 0.75 | 0.373 | 0.531 | 0.551 | 0.508 |
| qwen_ft_r16e1 · R3 · A2 | 0.749 | 0.383 | 0.519 | 0.55 | 0.489 |
| qwen_ft_r8e2 · R3 · A2 | 0.767 | 0.355 | 0.478 | 0.533 | 0.491 |
| GPT-6 Luna · R1 · A2 | 0.733 | 0.464 | 0.499 | 0.565 | 0.478 |
| GPT-6 Luna · R2 · A2 | 0.733 | 0.464 | 0.499 | 0.565 | 0.495 |
| GPT-6 Luna · R3 · A1 | 0.733 | 0.464 | 0.499 | 0.565 | 0.509 |
| Qwen3-4B · R3 · A2 | 0.665 | 0.471 | 0.502 | 0.546 | 0.446 |
| SEA-LION v3 9B · R3 · A2 | 0.726 | 0.455 | 0.437 | 0.539 | 0.5 |
| B1 Zero-shot | 0.744 | 0.392 | 0.51 | 0.549 | 0.482 |
| B3 RAG + rubric | 0.715 | 0.441 | 0.504 | 0.553 | 0.463 |
| B4 RAG + verifier | 0.715 | 0.441 | 0.504 | 0.553 | 0.463 |
| Fanar 9B · R3 · A2 | 0.599 | 0.417 | 0.379 | 0.465 | 0.342 |
| Llama 3.1 8B · R3 · A2 | 0.484 | 0.345 | 0.482 | 0.437 | 0.326 |
| Llama 3.1 8B · R1 · A2 | 0.432 | 0.372 | 0.439 | 0.414 | 0.356 |
| B2 Rules + bge-m3 | 0.521 | 0.188 | 0.415 | 0.375 | 0.233 |

