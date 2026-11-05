# KafAI UPKK: Experiments and Conclusions

Final Year Project, results as of 2 November 2026. Every number below comes from the result files in `eval/results/` (listed at the end).

## Summary

KafAI UPKK marks pupils' written answers for KAFA UPKK (Ibadah, Jawi and Tajwid) and explains each mark from the textbook. Its chat, Tanya Bulan, answers pupils' questions from the same textbook notes.

Six rounds of experiments chose the final marker: **GPT-6 Luna, reading the rubric and whole textbook sections (R3) in one fixed reasoning step (A2), with pupil memory off.**

- On 50 answers marked by three KAFA teachers, it reached **QWK 0.755 (95% CI 0.58–0.90)** against the teachers' final marks.
- Its agreement with each single teacher (mean QWK 0.593) is higher than the teachers' agreement with each other (0.449).
- Its feedback is almost always backed by the textbook (faithfulness 0.976).

With only 50 answers, most design choices could not be told apart statistically. Only the rule-based scorer, Llama 3.1 8B and Fanar were significantly worse. Jawi is the hardest subject, and the AI rarely gives partial marks.

---

## 1. What was tested

| Evaluation | Question | Data |
|---|---|---|
| **E1** Marking accuracy | Does the AI give the same mark as KAFA teachers? | 50 answers, 3 teachers |
| **E2** Feedback grounding | Is the feedback supported by the textbook? | The same 50 answers, scored by an AI judge |
| **RAG evaluation** | Does the system find the right textbook text and answer from it? Does it refuse questions outside the syllabus? | 45 textbook questions and 24 off-syllabus questions |
| Supporting studies | Reading scanned pages (OCR), chunking, embedding models, open-source models, fine-tuning, hybrid models | See each section |
| **E3** Users | Do teachers prefer the feedback? Is the app easy to use (SUS)? | **Not run yet** |

## 2. Data and method

### The teacher-marked set (the main test)

KAFA teachers would not share real pupils' answers, so a set of 50 answers was built:

- **28 from the silver test set:**
  - 24 AI-written answers: 9 fully correct paraphrases, 9 partly correct, 6 with a misconception.
  - 4 rule-built traps: a Jawi typo, a swapped number, Rumi written where Jawi was asked, and a true/false flip.
- **22 written by the researcher:**
  - 10 in a pupil's style.
  - 10 "keyword illusion" answers: fluent and using the right words, but wrong.
  - 1 confused answer and 1 fluent answer that does not answer the question.

By subject: Ibadah 18, Jawi 14 and Tajwid 18 answers, with 114 rubric criteria in total.

Three KAFA teachers marked every criterion *ya / separa / tidak* (correct / partly correct / wrong). They marked blind and independently, through a Google Form. The final mark for each criterion is the middle of the three marks: the majority mark, or *separa* when all three differ.

**Only the marks are human; the answers are not from real pupils.**

### Silver sets (development only)

These are AI-written paraphrases and rule-built answers whose marks are set by an AI or by construction: about 1,500 for training and 485 for testing. They were used to build the first scorer, to check settings and to fine-tune. They were never used as the final test.

### RAG test set

- 45 answerable questions from the question bank: 15 per subject, covering all levels.
- 24 off-syllabus questions: 12 general, and 12 near the syllabus (for example qalqalah, solat Jumaat and awalan *ber-*), each checked to be absent from the notes.

### Knowledge base

Notes from three Year 5 textbooks (Ibadah KAFA JAKIM, JAIS Tajwid, JAIS Jawi): 48 topic notes cut into 339 chunks, plus 382 reference answers. They are stored in ChromaDB with bge-m3 embeddings.

### Measures

- **QWK** (quadratic weighted kappa) on the 0–4 score band. How to read it: below 0.40 is weak, 0.41–0.60 moderate, 0.61–0.80 substantial, and above 0.80 almost perfect.
- **Exact agreement** and **within 1 mark**. Within 1 mark is counted only on answers worth more than 1 mark (34 of the 50), because a 1-mark answer can never be more than 1 mark out and would always count. Counted on all 50 answers the final system reaches 90%, but that figure is inflated by the 16 one-mark answers.
- **95% bootstrap confidence intervals** (2,000 resamples) on every number.
- **Paired comparisons** on the same answers. A difference is **significant** only when its 95% interval leaves out 0; tables mark significant differences with \*.
- **RAG quality:** RAGAS metrics (context precision, context recall, faithfulness, answer relevancy, factual correctness).
  - GPT-6 Luna wrote the answers. Claude Haiku 5.5, from another provider, judged them.
  - Retrieval was also scored against gold evidence: the textbook lines that state each part of the reference answer.

### Models

- **Through the OpenRouter API:** GPT-6 Luna, Claude Haiku 5.5 and Llama 3.1 8B.
- **Open-weight, on Google Colab (NVIDIA L4):** Qwen3-4B (4-bit), Fanar 9B and SEA-LION v3 9B (16-bit).

The whole project spent **$2.00 of the $4 API budget** (money actually paid). The cost columns below are different: they are the **list price** of a run, counted even when a rerun was served from the cache, so they do not add up to the $2.00. For runs that were partly cached, the list price is estimated from token counts (within 0.1% for Luna, 0% for Haiku and Llama on answers the estimate had not seen; `eval/recost.py`).

### Names used below

| Name | Meaning |
|---|---|
| B1 | Zero-shot LLM: rubric only, no textbook |
| B2 | Rules + bge-m3 similarity, no LLM |
| B3 | Textbook retrieval + rubric, one LLM call |
| B4 | B3 + a second call that checks the feedback |
| Proposed | Hard rules + RAG + ReAct marking, with optional pupil memory |
| R1 / R2 / R3 | Naive dense RAG / hybrid search + reranker / parent-document RAG (whole sections) |
| A1 / A2 / A3 | Vanilla ReAct (free tool loop) / constrained ReAct (fixed steps, one call) / Reflexion (draft + critic) |
| *separa* | Partly correct (partial mark) |

---

## 3. Early development on silver answers (September 2026)

- **The first scorer.** B2 (rules + bge-m3 similarity, no LLM) was tuned on silver training answers.
  - On 485 silver test answers it scored **QWK 0.920**: 0.983 on rule-built answers and 0.735 on AI paraphrases.
  - On the teacher set, the same scorer scores **0.476** (Section 4.2).
- **Retrieval.** With bge-m3 alone, questions typed in Jawi script found their topic first only 49% of the time; with keyword search, 91%. This is why the system searches with both (hybrid bge-m3 + BM25).

**Conclusion:** silver answers made the rule-based scorer look far better than it is against teachers. They are useful for development, not for final claims.

---

## 4. Marking experiments (E1)

### 4.1 How much do the teachers agree with each other?

| Pair | QWK | Exact | Within 1 mark |
|---|---|---|---|
| Teacher 1 vs Teacher 2 | 0.497 | 48% | 65% |
| Teacher 1 vs Teacher 3 | 0.516 | 54% | 65% |
| Teacher 2 vs Teacher 3 | 0.334 | 44% | 68% |
| **Mean (the human baseline)** | **0.449** (95% CI 0.267–0.618) | | |

- At criterion level, all three teachers gave the same verdict on only 35% of criteria (Fleiss' kappa 0.264).
- They differ most on partial marks. Teacher 1 gave *separa* to 5% of criteria, Teacher 2 to 25% and Teacher 3 to 19%.

**Conclusion:** the reference marks are themselves uncertain. Moderate agreement is what teachers reach with each other.

### 4.2 Steps 0–4: building the marker

All rows use the 50 teacher answers and give QWK against the final teacher marks. The last column is the paired difference from the final system. \* = significant.

| Step | Configuration | QWK [95% CI] | Difference from final system |
|---|---|---|---|
| 0 Baselines (GPT-6 Luna) | B2 rules + bge-m3, no LLM | 0.476 [0.22, 0.70] | −0.279 (p = 0.001) \* |
| | B1 zero-shot | 0.683 [0.47, 0.85] | −0.072 (p = 0.061) |
| | B3 RAG + rubric | 0.681 [0.47, 0.85] | −0.074 (p = 0.096) |
| | B4 RAG + verifier | 0.681 [0.47, 0.85] | −0.074 (p = 0.096) |
| 1 LLM (R1, A2) | Claude Haiku 5.5 | 0.723 [0.53, 0.88] | −0.032 (p = 0.492) |
| | GPT-6 Luna | 0.700 [0.49, 0.87] | −0.055 (p = 0.265) |
| | Llama 3.1 8B | 0.538 [0.33, 0.73] | −0.217 (p = 0.025) \* |
| 2 RAG type (Luna, A2) | R1 naive dense | 0.700 [0.49, 0.87] | −0.055 (p = 0.265) |
| | R2 hybrid + reranker | 0.700 [0.49, 0.87] | −0.055 (p = 0.265) |
| | **R3 parent-document** | **0.755 [0.58, 0.90]** | final system |
| 3 ReAct type (Luna, R3) | A1 vanilla | 0.700 [0.49, 0.87] | −0.055 (p = 0.265) |
| | **A2 constrained** | **0.755** | final system |
| | A3 Reflexion | 0.722 [0.52, 0.89] | −0.033 (p = 0.728) |
| 4 Memory (Luna, R3, A2) | **off** | **0.755** | final system |
| | on | 0.736 [0.55, 0.88] | −0.019 (p = 0.291) |

**Why Luna over Haiku.** Haiku was slightly ahead at R1, and Luna was ahead at R3 (0.755 vs 0.729). Neither gap is significant. Luna is the cheaper and faster of the two ($0.030 vs $0.046 per 100 answers; 3.5 s vs 8.1 s per answer), and it reads Jawi best (Section 7).

**Why A2 (constrained ReAct), from the saved reasoning traces:**

| | A1 vanilla | A2 constrained | A3 Reflexion |
|---|---|---|---|
| Model calls per answer | 3.0 | 1.0 | 2.0 |
| API cost per 100 answers | $0.080 | $0.030 | $0.053 |
| Time per answer | 14.1 s | 3.5 s | 4.7 s |
| Criterion verdicts = final teacher mark | 71% | 71% | 71% |

- **A1 sometimes skipped the textbook.** It always read the rubric, but searched the textbook before marking in only 84% of answers (79% in Jawi).
- **A1 and A2 agree almost everywhere.** They gave different verdicts on only 3 of 114 criteria: A2 was right on 1, A1 on 1, and both were wrong on 1.
- **A3's critic rarely changed anything.** It changed 3 of 95 LLM-marked verdicts, all to a stricter mark: 1 helped, 1 hurt, 1 stayed wrong.

So constraining the agent gives the same accuracy for a third of the cost, four times faster, and the textbook is always read.

**Memory.** With memory on, repeated marking was more stable: the same score in all 3 repeats for 98% of answers, against 94% without memory. Agreement with the teachers did not rise.

**Conclusion:** the chosen option has the highest QWK at every step, but only B2 and Llama are significantly worse. With 50 answers, differences smaller than about 0.1 QWK cannot be confirmed.

### 4.3 Human vs AI, by subject

Comparing the system with the three-teacher final mark (0.755) is not the same as comparing one teacher with another. The fair human comparison is therefore the system against each single teacher.

| | All | Ibadah | Jawi | Tajwid |
|---|---|---|---|---|
| Teachers with each other (mean QWK) | 0.449 | 0.276 | 0.645 | 0.456 |
| System with each teacher (mean QWK) | 0.593 | 0.541 | 0.461 | 0.741 |
| System vs final marks (QWK) | 0.755 | 0.742 | 0.527 | 0.947 |
| *separa* in the final teacher marks | 17% | 18% | 17% | 15% |
| *separa* given by the system | 3% | 2% | 0% | 5% |

**Where the system differs from the final marks:** 33 of 114 criteria.

- 15 times more lenient (LLM verdict).
- 12 times stricter (LLM verdict).
- 6 times stricter because of the hard Jawi spelling rule, all in Jawi.

Of the 19 criteria the teachers marked *separa*, the system gave *ya* to 10, *tidak* to 8 and *separa* to 1.

**Jawi spelling rule.** On the 50 answers, 9 spellings were one letter off. The teachers marked 5 of them wrong, 3 right and 1 partly right, so the system keeps exact spelling (no *separa* for a one-letter miss).

**Conclusions:**
- Overall, and in Ibadah and Tajwid, the system agrees with each teacher more than the teachers agree with each other. These are point estimates, not a significance test.
- **Jawi is the exception.** There the system (0.461) is below the teachers' own agreement (0.645), and its interval against the final marks is very wide (0.06–0.91). Half of its Jawi disagreements come from the strict spelling rule.
- **The AI almost never gives partial marks** (3% against the teachers' 17%). This is its main systematic difference from teachers.
- **Where the reference marks are weakest.** The teachers agree least on Ibadah (0.276) and moderately on Tajwid (0.456), and most on Jawi (0.645). The three teachers were not all specialists in the subject they marked, so on Ibadah and Tajwid some verdicts may be guesses; this is a likely cause, but the data cannot prove it (strictness about partial marks would give the same pattern). A noisy reference lowers every QWK, so the system's Ibadah figure may understate it. In Jawi the opposite holds: the teachers agree well and the system is the weaker party, so Jawi is the system's real weak spot.
- **How to improve the reference honestly.** Ask a specialist teacher to re-mark only the criteria the teachers disagreed on in their own subject. Replacing the teachers' marks with the researcher's own would make the answer key come from the person who built the system, and is not acceptable.

### 4.4 Feedback grounding (E2)

An AI judge from another provider checked whether each feedback statement is supported by the textbook.

| System | Faithfulness | Answers with an unsupported claim |
|---|---|---|
| B1 zero-shot (no textbook) | 0.854 | 26% |
| B3 RAG + rubric | 0.964 | 8% |
| B4 RAG + verifier | 0.974 | 6% |
| Haiku, R1, A2 | 0.963 | 14% |
| **Final system (Luna, R3, A2, memory off)** | **0.976** | **8%** |
| Final system with memory on | 0.957 | 10% |

**Conclusion:** without the textbook, about 1 answer in 4 got feedback with an unsupported claim; with the final system, about 1 in 12. The extra checking call (B4) adds little over retrieval alone.

---

## 5. Finding and using the textbook (RAG)

### 5.1 RAG types (45 answerable and 24 off-syllabus questions)

| Metric | R1 naive dense | R2 hybrid + reranker | R3 parent-document |
|---|---|---|---|
| Context precision | 0.851 | **0.935** | 0.917 |
| Context recall | 0.848 | 0.862 | **0.930** |
| Faithfulness | 0.979 | 0.968 | **0.984** |
| Answer relevancy | 0.614 | 0.584 | **0.662** |
| Factual correctness | 0.771 | 0.753 | **0.823** |
| Answerable questions declined (of 45) | 8 | 10 | **5** |
| Off-syllabus questions declined (of 24) | 24 | 24 | 24 |
| Retrieval time | 173 ms | 21.4 s | 35 ms |

**Significant differences** (95% CI leaves out 0):
- R3 beats R1 on context precision (+0.065) and context recall (+0.082).
- R3 beats R2 on context recall (+0.068), answer relevancy (+0.078) and factual correctness (+0.069), and declines fewer answerable questions (11% vs 22%).
- Faithfulness is about 0.97–0.98 for all three.

**Why.** R1 and R2 retrieve 4 chunks, but their 1,800-character limit lets the model read only about 2 of them. R3 passes the whole section each chunk comes from.

Counting a failure as a declined answer or factual correctness below 0.5: R1 failed 8 of 45 questions, R2 10 and R3 6. R3 had no failures in Jawi. Most failures are answers spread over several sections, or evidence cut off by the length limit. R2's reranker took 21 seconds per question on the CPU.

**Conclusion:** R3 is the best way to give the model the textbook. It also gave the highest marking QWK (Step 2).

### 5.2 Settings of R3 (one setting changed at a time)

| Setting | Result | Choice |
|---|---|---|
| Chunk size (300–1,500 characters, whole section) | No clear difference | 1,500 |
| Sections passed (1, 2, 3, 5, 10) | 1–2 lose evidence. 5 raised factual correctness 0.82 → 0.86 and cut declines 5 → 3. 10 added nothing over 5. | 5 was best for answering, but marking keeps 3 (Section 5.5) |
| Context limit (1,800 to no limit) | 1,800 clearly worse (factual correctness 0.68, 11 declined). More than 3,600 adds nothing. | 3,600 |
| Minimum similarity (0–0.85) | Answerable questions score 0.37–0.77 and off-syllabus questions up to 0.59, so no threshold separates them. 0.35 is the highest that loses no answerable question. | 0.35 as a floor; refusing off-syllabus questions is left to the model's decline rule |
| Query rewrites | No clear difference, and each costs an extra call | None |
| Search scope | No clear difference | Subject (chat); topic first (marking) |
| Matching method | BM25 alone clearly worse (evidence recall 0.85 vs 0.92). bge-m3 alone is the same for Rumi questions. | Hybrid: the keyword side finds questions typed in Jawi |
| Questions typed in Jawi | Evidence recall 0.79, against 0.92 for the same questions in Rumi. The bge-m3 weight makes no clear difference. | Weight 0.25 |

**By subject:** no subject was clearly better with a different option, so one setting is used for all three subjects.

### 5.3 Embedding models

| Model | Size | Evidence recall (hybrid) | Change from bge-m3 |
|---|---|---|---|
| **bge-m3** | 568 M | **0.920** | – |
| multilingual-e5-large | 560 M | 0.883 | −0.038 (not significant) |
| multilingual-e5-base | 278 M | 0.828 | −0.093 \* (Tajwid −0.241 \*) |
| MiniLM-L12 multilingual | 118 M | 0.579 | −0.341 \* |

- When e5-base retrieved for the answer model, factual correctness also fell: −0.112 \* overall and −0.303 \* in Tajwid.
- **Conclusion:** bge-m3 is the best in every subject and stays. It also takes the longest input (8,192 tokens).

### 5.4 Chunking methods

| Method | Hit rate | Change from A |
|---|---|---|
| **A. Section + size (current)** | **0.978** | – |
| A with overlap 0 / 100 / 200 | 0.978 | none |
| B. Fixed window of 600 characters, no overlap | 0.867 | −0.111 \* |
| B. Fixed window, overlap 100 / 200 | 0.889 / 0.911 | −0.089 \* / −0.067 |
| C. Sub-section / D. Table rows / E. Bilingual pair | 0.978 / 0.956 / 0.978 | not significant |
| F. Semantic | 0.844 | −0.133 \* |

**Conclusion:**
- Cutting by the textbook's own sections works best for all three subjects.
- The common default in RAG papers (a fixed window) and semantic cutting are clearly worse.
- A mixed per-subject setup was not better than method A.

### 5.5 Do the answering settings also suit marking? (Phase 6)

The settings study measured *answering*. Its choices (6 chunks, 5 sections, minimum 0.35) were therefore tested on *marking* before being kept.

| Check | Earlier R3 (4 chunks, 3 sections) | Study's R3 | Change |
|---|---|---|---|
| 171 silver answers (QWK) | 0.960 | 0.964 | +0.004 (not significant) |
| Teacher set, final system (QWK) | 0.755 | 0.695 | −0.060 [−0.152, −0.002] \* |
| Teacher set, Haiku (QWK) | 0.729 | 0.636 | −0.094 [−0.232, −0.004] \* |

**Decision:** marking keeps the earlier R3. The study's findings are used where they were measured: Tanya Bulan's lower gate and its decline rule (Section 9).

**Conclusion:** settings tuned for answering did not transfer to marking, and the silver answers were too easy to show it.

---

## 6. Reading scanned textbook pages (OCR)

10 textbook pages (7 notes) were read by each method. Character error rate (CER): lower is better.

| Method | Jawi CER | Arabic (Quran) CER | Seconds / page | Cost / page |
|---|---|---|---|---|
| PDF text layer (PyMuPDF) | 100% | 100% | 0.1 | $0 |
| Tesseract (Arabic) | 60.8% | 91.8% | 2.4 | $0 |
| **Claude Haiku 5.5 vision** | **22.4%** | 26.1% | 14.5 | $0.0017 |
| GPT-6 Luna vision | 23.8% | **14.0%** | 29.1 | $0.0016 |

**By kind of page:** text pages are easiest (Haiku 13.8%, Luna 12.7% Jawi CER). Tables are hardest (Haiku 41.4%, Luna 49.0%).

**Conclusions:**
- The textbook PDFs have no text layer, and free OCR (Tesseract) cannot read Jawi.
- AI vision reads Jawi with about 22–24% CER. Haiku is slightly better on Jawi; Luna is clearly better on Quranic Arabic.
- **Caveat:** the reference notes are AI transcriptions. They were checked against the page but not yet verified by a teacher, which may favour the model that made them.

---

## 7. Open-source models (Phase 3)

Same setup for every model (proposed system, R3, A2, memory off) on the 50 teacher answers.

| Model | Runs on | QWK [95% CI] | vs Luna | Valid marks | s / answer | $ / 100 answers | Jawi reading test |
|---|---|---|---|---|---|---|---|
| **GPT-6 Luna** | API | **0.755 [0.58, 0.90]** | – | 100% | 3.5 | $0.030 | **70%** |
| Claude Haiku 5.5 | API | 0.729 [0.53, 0.89] | −0.026 | 98% | 8.1 | $0.046 | 57% |
| Llama 3.1 8B | API | 0.546 [0.33, 0.73] | −0.209 \* | 98% | 5.0 | $0.041 | 17% |
| Qwen3-4B | Colab L4, 4-bit | 0.694 [0.50, 0.84] | −0.061 | 94% | 18.4 | free | 7% |
| SEA-LION v3 9B (Malay) | Colab L4, 16-bit | 0.685 [0.50, 0.83] | −0.070 | 100% | 24.8 | free | 10% |
| Fanar 9B (Arabic, Islamic) | Colab L4, 16-bit | 0.624 [0.42, 0.79] | −0.131 \* | 96% | 24.2 | free | 17% |

The Jawi reading test has 30 textbook words: 15 to spell (Rumi → Jawi) and 15 to read (Jawi → Rumi). Even Luna spells only 53% exactly.

**Conclusions:**
- Qwen3-4B and SEA-LION are not significantly below Luna in marking, but they are 5–7 times slower.
- No open model can read or write Jawi (7–17%).
- Training on Arabic (Fanar) or Malay (SEA-LION) did not help with Jawi, and Fanar marks significantly worse than Luna.

---

## 8. Fine-tuning and a hybrid model (Phase 4)

### Fine-tuning

- **Model:** QLoRA on Qwen3-4B, the best open model.
- **Data:** 490 training and 88 validation silver answers. The reply to learn is the silver verdicts with GPT-6 Luna's reasons and feedback. No teacher answer was used.
- **Runs:** LoRA rank 8 or 16, 1 or 2 epochs, on a Colab L4 (47 minutes per rank).
- **Selection:** the validation loss chose r8e2 before the teacher test.

| Model | QWK [95% CI] | Change from base | Valid marks | *separa* given (teachers 17%) | s / answer | Jawi test |
|---|---|---|---|---|---|---|
| Qwen3-4B base | 0.694 [0.50, 0.84] | – | 94% | 13% | 18.4 | 7% |
| r8, 1 epoch | 0.741 [0.55, 0.88] | +0.047 | 100% | 1% | 25.6 | 13% |
| **r8, 2 epochs (selected)** | 0.701 [0.50, 0.86] | +0.007 | 100% | 1% | 27.4 | 13% |
| r16, 1 epoch | 0.701 [0.51, 0.85] | +0.007 | 100% | 0% | 25.5 | 13% |
| r16, 2 epochs | 0.743 [0.55, 0.90] | +0.049 | 100% | 4% | 25.1 | 13% |

**Conclusion:**
- Fine-tuning made Qwen follow the marking format every time (100% valid, against 94%) and raised QWK a little, but no change is significant.
- It also learned to avoid partial marks, copying Luna's habit from the training replies.
- Jawi stayed poor, and marking became slower (the adapter was not merged).

### Hybrid: open model + GPT-6 Luna

These hybrids were built from saved runs (simulated), not run live.

| Hybrid | QWK [95% CI] | vs Luna alone | Answers sent to Luna | $ / 100 answers |
|---|---|---|---|---|
| GPT-6 Luna alone | 0.755 [0.58, 0.90] | – | 100% | $0.030 |
| **Router A: Tahap 1 → Qwen, Tahap 2–3 → Luna** | **0.785 [0.60, 0.92]** | +0.030 (p = 0.103) | 48% | $0.017 |
| Router B: Qwen first; Luna if invalid or *separa* | 0.764 [0.58, 0.90] | +0.009 | 32% | $0.011 |
| Router C: Qwen first; Luna if invalid or it differs from B2 | 0.737 [0.55, 0.88] | −0.018 | 54% | $0.017 |
| Router A with fine-tuned Qwen (r8e2) | 0.733 [0.54, 0.89] | −0.022 | 48% | $0.017 |

**Conclusion:**
- Router A has the highest QWK of all runs at about 57% of Luna's API cost ($0.017 vs $0.030 per 100 answers). The gain is not significant, and it still needs a live run.
- Fine-tuned Qwen did not make a better hybrid.

---

## 9. Tanya Bulan: refusing questions outside the syllabus

- **The decline rule works with Luna.** In the RAG evaluation, with the rule in the prompt, all three RAG types declined 24 of 24 off-syllabus questions.
- **The old gate was too strict.** It required a best match of at least 0.55, which also turned away 5 of 45 answerable questions. A similarity threshold alone cannot separate the two groups (Section 5.2).
- **Phase 6 change:**
  - The gate is now 0.35, and the decline rule was added to the chat prompt.
  - The textbook-only fallback (used when no model is running) keeps 0.55, because it cannot decline.
- **Live check without a model** (`eval/chat_gate_eval.py --no-model`):
  - 37 of 45 textbook questions were answered and 23 of 24 off-syllabus questions were declined.
  - 21 of the 24 off-syllabus questions score between 0.35 and 0.55, so with Qwen running, it is Qwen's own decline that has to stop them.
  - This check also found and fixed a bug: the fallback showed an empty reply with source cards when it could not find a key fact.
- **Not yet measured:** how often the real chat model (Qwen) declines. This needs Qwen running on Colab.

---

## 10. The final system

| Part | Choice | Why |
|---|---|---|
| Model | GPT-6 Luna | Highest QWK at R3 (not significantly above Haiku), cheapest and fastest of the good models, best at reading Jawi |
| Textbook retrieval | R3: 4 matched chunks → up to 3 whole sections, 3,600 characters, hybrid bge-m3 + BM25, topic first | Best RAG type; the answering settings lowered marking agreement |
| Reasoning | A2 constrained ReAct | As accurate as A1 and A3, with one call, about 3× cheaper |
| Memory | Off | No gain in agreement |
| Hard rule | Jawi spelling must be exact | Teachers marked most one-letter errors wrong (5 of 9) |

### Results against the project's targets (50 teacher answers)

| Measure | Result | Target | Met? |
|---|---|---|---|
| QWK against the final teacher marks | 0.755 [0.58, 0.90] | ≥ 0.70 | Yes on the point estimate (the interval goes down to 0.58) |
| Within 1 mark (answers worth 2+ marks: 29 of 34) | 85% [72%, 97%] | ≥ 85% | Only just, on the point estimate (the interval goes down to 72%). The teachers agree with each other on 65–68% of these answers |
| Feedback faithfulness (E2) | 0.976 | ≥ 0.85 | Yes |
| Context recall (RAG, R3) | 0.930 | ≥ 0.80 | Yes |
| Teachers prefer the feedback with memory (E3) | – | ≥ 65% | Not measured yet |
| Teacher rating of the feedback (E3) | – | ≥ 4.0 of 5 | Not measured yet |
| Usability, SUS (E3) | – | ≥ 68 | Not measured yet |

**Other figures for the final system:**
- Exact agreement 62%.
- Mean QWK with each teacher 0.593, against 0.449 between teachers.
- $0.030 API cost per 100 answers, 3.5 seconds per answer.

---

## 11. Conclusions

1. **A textbook-grounded LLM can mark KAFA UPKK answers about as consistently as teachers mark each other.**
   - The final system reaches QWK 0.755 against the final teacher marks.
   - It averages 0.593 with each single teacher, against 0.449 between teachers.
   - The rule-based scorer without an LLM cannot do this (0.476, significantly worse).
2. **The textbook matters most for trustworthy feedback, less for the mark itself.**
   - Zero-shot marking is not significantly worse in QWK (0.683).
   - But its feedback had unsupported claims in 26% of answers, against 8% with retrieval.
3. **Whole sections (R3) are the best way to give the model the textbook.**
   - R3 has the highest recall and factual correctness when answering, and the highest marking QWK.
   - Most retrieval failures come from cutting text to fit a short limit.
4. **Constraining the agent saves cost, not accuracy.**
   - A2 marks as well as A1 and A3 with one call: about 3× cheaper and 4× faster.
   - The free loop (A1) skipped the textbook in 16% of answers, and the Reflexion critic changed only 3 of 95 verdicts.
5. **Pupil memory made marking more repeatable but not more accurate.**
6. **Jawi is the hardest part of the problem.**
   - It has the lowest agreement (0.527) and is the only subject where the system is below the teachers' own agreement.
   - The strict spelling rule causes half of the Jawi disagreements.
   - Open models cannot read or write Jawi (7–17%), and OCR is worst on Jawi tables.
7. **The AI rarely gives partial marks** (3% against the teachers' 17%). Fine-tuning on AI-made targets made this worse (0–4%).
8. **Open models come close in marking but cannot yet replace the API model.**
   - Qwen3-4B (0.694) is not significantly below Luna, but it is slower, sometimes breaks the format, and cannot handle Jawi.
   - Fine-tuning fixed the format but did not raise accuracy significantly.
   - The most promising use is a hybrid (Qwen for Tahap 1, Luna for Tahap 2–3: 0.785 at about 57% of the cost), which still has to be confirmed live.
9. **Development data can mislead.**
   - Silver answers rated the rule-based scorer 0.920 (teachers: 0.476).
   - They could not separate R3 settings that the teacher set showed to matter (0.755 → 0.695).
   - Settings tuned for answering did not transfer to marking. Final decisions need teacher-marked data.
10. **Refusing off-syllabus questions needs the model, not just a threshold.** Similarity scores of answerable and off-syllabus questions overlap; with a decline rule, the answer model declined 24 of 24.

## 12. Limitations

- **Chosen and reported on the same 50 answers.** 21 configurations were run on the 50 teacher answers (the 6 simulated hybrids not counted), and the final system is the highest of the 20 that use a language model (QWK 0.755; the median was 0.700, and the top five lie within 0.026 of each other with overlapping intervals). Its QWK is therefore somewhat optimistic: picking the best of many on the data it is reported on favours chance. The step-by-step design (models, then retrieval, then the ReAct loop) and the paired tests limit this, but do not remove it. A fresh set that was never used to choose the settings (planned: UPKK exam questions with model answers) would settle it.
- **Teachers not all specialists.** The three teachers were not all specialists in the subject they marked. Agreement is lowest in Ibadah (0.276) and Tajwid (0.456), so those reference marks are the least certain (Section 4.3).
- **"Within 1 mark" excludes 1-mark answers.** It is counted on the 34 answers worth more than 1 mark; the 16 one-mark answers cannot miss by more than 1 mark. On all 50 the figure would be 90% instead of 85%.
- **Small test set.** 50 answers (14–18 per subject) give intervals of about ±0.15 QWK overall, and much wider by subject (Jawi 0.06–0.91). Most differences between the good configurations cannot be confirmed.
- **Constructed answers.** They are not from real pupils; real answers may be messier.
- **Uncertain reference.** The teachers agree only moderately (QWK 0.449, Fleiss' kappa 0.264), especially on partial marks.
- **AI judges.** The RAG metrics and E2 rely on an LLM judge, always from another provider than the model judged.
- **AI-made data.** Silver labels were used for development and fine-tuning. The OCR reference notes are not yet verified by a teacher.
- **Simulated hybrids.** They were built from saved runs, not run live.
- **Single runs.** Each configuration was run once, except memory (3 repeats). Without memory, scores vary between repeats (coefficient of variation 7.66%).
- **E3 not run.** The user evaluation (teacher A/B rating and SUS) has not been done.

## 13. Still open

- **E3 user evaluation:**
  - Teachers' blind A/B comparison and Likert rating of the feedback (`scripts/ab_form.py`).
  - SUS questionnaire (`docs/SUS_soal_selidik.md`).
- **OCR notes:** a teacher checks the 7 notes in `data/semakan_nota_ocr.xlsx`; then rerun `eval/ocr_eval.py` (free).
- **Tanya Bulan:** run `eval/chat_gate_eval.py` with Qwen running on Colab, to measure how often the real chat model declines.
- **Specialist re-marking:** a specialist teacher re-marks the criteria the teachers disagreed on in Ibadah and Tajwid (about 15 minutes each); then rerun `eval/final_stats.py` (free).
- **Fresh test set:** UPKK exam questions with model answers and marks, never used to choose settings, to confirm the final QWK.
- **Live marker:** decide whether the website's marker for pupils switches from B2 to the final system.
- **Optional:**
  - Run Router A live.
  - Add *separa* examples to the fine-tuning data.
  - Collect more teacher-marked answers to narrow the intervals.

---

## Where the numbers come from

| Section | Result file (in `eval/results/` unless shown) | Figure (`docs/figures/results/`) |
|---|---|---|
| 3 Early development | `evaluation_test.md`, `retrieval_test.md` | – |
| 4.1–4.2 Steps 0–4 | `final_stats.md`, `teacher_compare.md`, `docs/figures/results/tables.md` | `fig_4_01`, `fig_4_02`, `fig_4_03`, `fig_4_07`, `fig_4_08`, `fig_4_09`, `fig_4_10`, `fig_4_11` |
| 4.2 ReAct traces | `react_eval.md` | `fig_4_07` |
| 4.3 Human vs AI | `human_vs_ai.md`, `data/teacher/agreement.md` | `fig_4_12` |
| 4.4 E2 grounding | `experiments/*.grounding.json` | – |
| 5.1 RAG types | `rag_eval.md`, `rag_stats.md`, `rag_why.md` | `fig_4_04` |
| 5.2 R3 settings | `rag_settings.md`, `rag_settings_by_subject.md` | `fig_4_05`, `fig_4_06` |
| 5.3 Embedding models | `embedding_models.md` | `fig_4_13` |
| 5.4 Chunking | `chunking_by_subject.md` | `fig_4_14` |
| 5.5 R3 for marking | `r3_marking_dev.md` | – |
| 6 OCR | `ocr_eval.md` | `fig_4_15` |
| 7 Open models | `open_models.md`, `jawi_reading.md` | `fig_4_16` |
| 8 Fine-tuning and hybrid | `phase4.md`, `finetune_data.md` | `fig_4_17` |
| 9 Tanya Bulan | `rag_settings.md`, `chat_gate_eval_no_model.md` | – |
