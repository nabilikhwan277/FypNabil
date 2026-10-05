# Chapter 4 – Results and Discussion (draft)

> **Before submission:** the scoring figures below use **silver labels** (Section 3.12). Replace Tables 4.4–4.7 with the teacher-marked results (`eval/results/evaluation_teacher.md`), and fill in 4.6 (SUS) and the feedback rating. Every number here comes from `eval/results/` and can be regenerated with the commands in `README.md`.

## 4.1 Introduction
This chapter presents the prototype and the results of the evaluation:
- the knowledge base and the retrieval module
- the configuration of the scoring framework
- the scoring agreement on the held-out test set
- consistency and performance
- usability.

It ends by relating the results to the research questions.

## 4.2 Prototype
The prototype, named the Intelligent KAFA UPKK Learning Assistant, was implemented as described in Section 3.11. Figures 3.7–3.14 show the main screens.

**Table 4.1 Content of the knowledge base**

| Subject | Topics | Questions | Tahap 1 | Tahap 2 | Tahap 3 |
|---|---|---|---|---|---|
| Ibadah (Fiqh) | 16 | 113 | 65 | 33 | 15 |
| Jawi | 10 | 113 | 61 | 42 | 10 |
| Tajwid | 22 | 156 | 78 | 56 | 22 |
| **Total** | **48** | **382** | **204** | **131** | **47** |

The notes were split into 339 retrieval chunks.

## 4.3 Retrieval performance

**Table 4.2 Recall@4 of the correct topic, retrieval without the topic filter**

| Query | Semantic only (train) | Hybrid (train) | Semantic only (test) | Hybrid (test) |
|---|---|---|---|---|
| Rumi question, same subject | 0.964 | 0.990 | 0.947 | **1.000** |
| Jawi question, same subject | 0.807 | 0.958 | 0.737 | **0.934** |
| Rumi question, all subjects | 0.935 | 0.977 | 0.921 | **0.987** |

- **Hybrid retrieval met the target** of Recall@4 ≥ 0.85 in every setting.
- **Semantic search alone was weak for Jawi-script questions** (0.737 on test). Adding BM25 keyword search improved it by about 20 percentage points.
- **These figures are a lower bound.** In the live system the question's own topic is searched first.

## 4.4 Configuration of the scoring framework

**Table 4.3 Scoring methods for Tahap 2/3 criteria not settled by Layer A (training set, silver labels)**

| Method | Uses LLM | Criterion error* | Criterion accuracy | Exact item score |
|---|---|---|---|---|
| Generative judge + guard 0.60 (initial design) | Yes | 0.140 | 0.837 | 0.747 |
| Generative judge + guard 0.65 | Yes | 0.123 | 0.852 | 0.762 |
| Probability judge, zero-shot | Yes | 0.128 | 0.846 | 0.758 |
| Probability judge, few-shot | Yes | 0.145 | 0.830 | 0.751 |
| Hybrid probability judge + similarity | Yes | 0.124 | 0.850 | 0.767 |
| Keyword/content overlap | No | 0.137 | 0.838 | 0.756 |
| **Semantic similarity ≥ 0.65 (selected)** | No | **0.122** | **0.853** | 0.762 |

\*Share of available marks awarded wrongly; lower is better.

**Table 4.4 How well each signal separates met from not-met criteria (AUC, training set)**

| Signal | AUC |
|---|---|
| Similarity to criterion + to reference answer | 0.821 |
| Similarity to reference answer | 0.805 |
| Similarity to criterion | 0.762 |
| Keyword/content overlap | 0.684 |
| LLM probability judge (zero-shot / few-shot) | 0.560 / 0.552 |
| LLM generative judge | answered "ya" for 100% of met and 100% of not-met criteria |

- **The 1B model could not judge rubric criteria.** It accepted every answer, and its probabilities were close to chance.
- **Worked examples did not help.** The few-shot prompt made the probability judge slightly worse.
- **Configurations with the LLM only worked because of the guard.** Their accuracy came from the similarity guard, not from the model.
- **The selected method needs no LLM for marking.** It had the lowest error, gives the same result on every run and is much faster.
- **Consistent with earlier work.** This matches Reddig et al. (2025), who found a large share of LLM hints unhelpful. It also matches Dara and Cheng (2026), who found that sentence encoding influenced results more than the choice of LLM.

## 4.5 Scoring agreement on the test set

**Table 4.5 Overall agreement with the silver labels (test set, 485 answers)**

| Configuration | Exact | Within 1 mark | MAE (marks) | MAE % | QWK | Over-marked | Under-marked |
|---|---|---|---|---|---|---|---|
| Initial design (LLM judge + guard) | 0.849 | 0.953 | 0.19 | 6.0 | 0.921 | 7.4% | 7.6% |
| **Selected (no LLM in marking)** | 0.841 | 0.953 | 0.19 | 6.2 | 0.920 | 6.8% | 9.1% |

**Table 4.6 Selected configuration by level, subject and answer type**

| Group | n | Exact | Within 1 mark | MAE % | QWK |
|---|---|---|---|---|---|
| Tahap 1 | 241 | 0.938 | 0.996 | 3.5 | 0.953 |
| Tahap 2 | 181 | 0.785 | 0.917 | 9.2 | 0.866 |
| Tahap 3 | 63 | 0.635 | 0.889 | 7.7 | 0.931 |
| Ibadah | 147 | 0.837 | 0.946 | 7.1 | 0.911 |
| Jawi | 141 | 0.887 | 0.972 | 4.3 | 0.933 |
| Tajwid | 197 | 0.812 | 0.944 | 6.9 | 0.916 |
| Rule-built answers | 322 | 0.975 | 0.997 | 1.1 | 0.983 |
| AI-written pupil-style answers | 163 | 0.577 | 0.865 | 16.3 | 0.735 |

**Table 4.7 Selected configuration by answer type (test set)**

| Answer type | n | Exact | Typical error |
|---|---|---|---|
| Reference answer (Jawi / Rumi) | 76 / 68 | 0.987 / 0.956 | rare under-marking |
| Jawi one-letter misspelling | 7 | 1.000 | none |
| Rumi answer to a "write in Jawi" question | 7 | 1.000 | none |
| Wrong number / flipped Betul-Salah | 8 / 4 | 1.000 / 1.000 | none |
| "Saya tidak tahu" / other topic's answer | 76 / 76 | 0.987 / 0.961 | rare over-marking |
| Full answer in own words | 56 | 0.643 | under-marked (36%) |
| Partial answer | 51 | 0.412 | both directions |
| Misconception | 56 | 0.661 | over-marked (34%) |

**Findings**
- **The two configurations were equally accurate on the test set.** The difference is within noise. Removing the LLM from marking did not reduce accuracy, and it improved speed and consistency (Section 4.5).
- **Rule-based cases are marked almost perfectly.** This includes Jawi spelling, where one wrong letter is always detected; answers that contradict a number; Betul/Salah items; and irrelevant answers.
- **Open answers in the pupil's own words are the weak point** (58% exact, 87% within one mark):
  - correct answers phrased very differently from the rubric are sometimes under-marked;
  - misconceptions that reuse the topic's vocabulary are sometimes over-marked;
  - partial answers are hard because the selected rule never awards half marks.
- **The QWK of 0.92 overall is above the 0.70 target.** On the open answers alone it is 0.735, just above the target.

## 4.6 Consistency and performance

**Table 4.8 Live pipeline with the real models (60 test answers × 3 runs)**

| Measure | Result | Target |
|---|---|---|
| Same score in all three runs | 100% | ≥ 95% |
| Assessments completed without error | 180 / 180 (100%) | ≥ 98% |
| Median response time: Tahap 1 / 2 / 3 | 56 / 70 / 154 ms | Tahap 1 < 15 s |
| 95th percentile: Tahap 1 / 2 / 3 | 70 / 95 / 245 ms | – |
| Feedback grounded (correct answer = reference, page shown, 5-step trace) | 100% | – |
| Live score equal to the offline evaluation | 100% | – |

With the language-model judge enabled, Tahap 2/3 answers took 3–10 s each (Chapter 3, Phase 4 tests). The selected configuration therefore responds about 20–60 times faster, which matters for children waiting for feedback.

## 4.7 Usability
*To be completed:* SUS results from `eval/results/sus.md` (target mean ≥ 68), the two extra questions on feedback usefulness and the Jawi keyboard, and pupils' comments.

## 4.8 Feedback quality
*To be completed:* a teacher rates 20–30 feedback samples for accuracy, relevance and clarity on a 1–5 scale (target mean ≥ 4).

## 4.9 Discussion by research question

**RQ1: How can LLMs and RAG be applied to automated assessment and feedback?**
- RAG was essential for grounding. Without the textbook passage the model gave wrong facts; with it, it answered correctly.
- Hybrid retrieval found the right topic for 93–100% of questions.
- The feedback itself was generated from the rubric, the reference answer and the retrieved note. This guarantees it contains no invented facts, which matters for religious content taught to children.

**RQ2: Does the hybrid framework improve accuracy and relevance?**
- The combination of deterministic rules, retrieval, multilingual semantic similarity and learning memory reached 84% exact agreement and a QWK of 0.92 on the test set, with complete consistency.
- The comparison in Table 4.3 shows that the strength came from the rule layer and the embedding model. The 1B language model did not help as a judge.
- For a locally run, low-cost system, a small LLM should therefore not be trusted to judge answers. Its role is better limited to grounded generation, or it should be replaced by a larger or fine-tuned model once teacher-marked data is available.

**RQ3: Can a KAFA learning assistant provide adaptive assessment and personalised feedback for Tajwid, Fiqh and Jawi?**
- The prototype covers the whole Year 5 syllabus of the three subjects at three levels.
- It adapts the level and the next question to each pupil's mastery.
- It names repeated mistakes, supports Jawi input and output, and responds in well under a second.

## 4.10 Limitations
- **Silver labels.** The scoring results use AI-written and rule-built answers, not teacher-marked pupil answers, so they are an estimate.
- **Unverified notes.** The textbook notes were transcribed with AI assistance and are not yet verified by a teacher.
- **Open and partial answers.** Scoring of open and partial answers at Tahap 2/3 is the weakest part.
- **Model size.** Only a 1B model could run on the available hardware. Larger models or fine-tuning on teacher-marked examples were not tested.
- **Prototype security.** There is no authentication, so the system is suitable only for local or school-network use.
