# Experiment Plan v3: Supervisor Feedback (Week 5)

**Goal:** run every experiment the supervisor asked for. The report comes later; this plan only covers experiments and their saved results.

**Main message from the supervisor:** do not only say *which* option is better, show *why*, and keep the experiments that failed so they can be compared.

**Already done (reused, not repeated):**
- Steps 0–4 on the final teacher marks (3 teachers + median rule), with 95% CIs and p-values: `eval/final_stats.py`
- RAG types R1/R2/R3 with RAGAS metrics: `eval/rag_eval.py`
- RAG settings study (chunk size, sections, context limit, similarity, query variants, scope, matching, Jawi weight): `eval/rag_settings.py`
- 12 figures and tables: `eval/make_figures.py`

---

## Overview

| Phase | What | Supervisor point | Cost | Who runs it |
|---|---|---|---|---|
| 1 | Analysis of results that already exist ("why"), all by subject; RAG settings per subject | CI everywhere, human vs AI by subject, A2 vs A1, settings per subject | Free (+$0.15 if the RAG test set grows) | Me |
| 2 | Embedding models, chunking method per subject, PDF reading (OCR) methods | "Compare models for reading PDF, chunking, embedding" | ~$0.15 | Me |
| 3 | Open-source models: Fanar (Arabic) and SEA-LION (Malay), vs Qwen3-4B | "Add Jais, Falcon, Allam, Fanar" | Free (Colab) | You start Colab, I run the tests |
| 4 | Fine-tuning and hybrid model | "Consider fine-tuning / hybrid" | Free (Colab) | You start Colab, I prepare everything |
| 5 | Database (ChromaDB) description for the next meeting | "Database and IDs" | Free | Me |
| 6 | Final rerun: apply the chosen settings, update all tables and figures | Consistent final results | ~$0.10 | Me |

Total API cost: about **$0.30–0.45** (budget left: about $2.50 of $4).

---

## Rule for every phase: results by subject
The supervisor asked for every evaluation to be split by subject, because each subject may score differently.
Every result in this plan is reported **overall and for Ibadah, Jawi and Tajwid separately**, each with its 95% CI.

| Data | Ibadah | Jawi | Tajwid | Total |
|---|---|---|---|---|
| Teacher-marked answers (E1) | 18 | 14 | 18 | 50 |
| RAG test questions | 15 | 15 | 15 | 45 |

With 14–18 answers per subject the intervals are wide, so a per-subject difference is called *clear* only when its interval leaves out 0; the others are reported as tendencies.

## Phase 1: Explain the existing results (free, no new model calls)

### 1.1 Confidence intervals for every metric
- **Why:** the supervisor wants a 95% CI on every result, not only QWK.
- **What:** add a 95% bootstrap CI (2,000 resamples of the questions) to:
  - RAG evaluation: context precision, context recall, faithfulness, answer relevancy, factual correctness, for R1/R2/R3;
  - paired tests between R1/R2/R3 (R3 vs R1, R3 vs R2) with p-values;
  - exact agreement and within-1-mark for every marking configuration (QWK already has them);
  - all of the above **per subject** (Ibadah, Jawi, Tajwid) as well as overall.
- **How:** a new `eval/rag_stats.py` reads the saved per-question scores in `rag_eval.json` (no model calls); `final_stats.py` gets CIs for exact and within-1.
- **Output:** `eval/results/rag_stats.json/.md`; the table "model | index | metric | value | 95% CI" the supervisor asked for (`eval/results/results_table.md`).
- **Done when:** every number in the result tables has a 95% CI and every comparison has a p-value.

### 1.2 Human vs AI, by subject and by question
- **Why:** "compare human marks (Google Form) with AI marks by subject; discuss where they differ".
- **What:**
  1. Per subject (Ibadah, Jawi, Tajwid): teacher-vs-teacher QWK **next to** system-vs-teacher QWK, with CIs.
  2. Per question: the questions where teachers disagree with each other, and the questions where the AI disagrees with the majority of teachers.
  3. Grouped reasons (from the answers and the teachers' comments): spelling (Jawi), partly correct answers (*separa*), wording vs meaning, numbers (harakat, rakaat), answers longer than the scheme.
  4. The "separa" problem: how often teachers vs AI give a partial mark, per subject.
- **How:** new `eval/human_vs_ai.py` using `data/teacher/` (3 teachers, final marks, comments) and the saved runs.
- **Output:** `eval/results/human_vs_ai.json/.md` (tables + list of example answers with the 3 teacher marks, the AI mark and the AI's reason); 2 figures (subject comparison, partial-mark rates).
- **Done when:** for each subject there is a number *and* concrete examples of where and why AI and teachers differ.

### 1.3 Why constrained ReAct (A2) beats vanilla ReAct (A1)
- **Why:** "explain why constraint is better than vanilla prompting".
- **What:** from the saved reasoning traces of A1, A2 and A3 (50 answers each):
  - completion rate and valid JSON rate;
  - did A1 read the rubric and the textbook before marking, or skip steps? how many steps, repeated or wasted actions;
  - calls, tokens, time and cost per answer;
  - answers where A1 and A2 give different marks: who was right (vs the teachers) and what A1 did differently in its trace;
  - A3: how often the critic changed the draft, and whether each change moved the mark closer to or further from the teachers;
  - every count above **per subject**: e.g. whether A1 skips the textbook more often in Jawi spelling questions.
- **How:** new `eval/react_eval.py` (reads the saved runs; no model calls).
- **Output:** `eval/results/react_eval.json/.md`; figures: steps per answer, critic changes (helped / hurt / no effect).
- **Done when:** the advantage of A2 is explained with counts and trace examples, not only QWK.

### 1.4 "Why" notes for the RAG results
- **Why:** "if precision is low but other metrics are high, discuss why".
- **What:** per-subject RAGAS metrics for R1/R2/R3 (already saved), plus the questions each RAG type answered wrongly or declined, with the reason: answer cut by the 1,800-character limit, wrong section retrieved, answer spread over several sections, Jawi words.
- **Output:** `eval/results/rag_why.md` (per-subject table + failure categories with counts and examples).

### 1.5 RAG settings per subject (may each subject need its own setting?)
- **Why:** supervisor: subjects read differently (e.g. Jawi tables of spellings vs Ibadah paragraphs vs Tajwid rules with Quran examples), so the best chunk size, number of sections, similarity threshold etc. may differ per subject.
- **What:** split every setting of the settings study by subject: chunk size, number of sections, context limit, minimum similarity, query variants, search scope, matching method, Jawi weight, and in Phase 2 the embedding model.
  For each subject: the best option, its difference from the overall choice, 95% CI and p-value.
- **How:** free: the settings study already saved every question's result for every option (`rag_settings.json`), so it is re-scored per subject without new model calls.
- **Decision rule:** keep **one setting for all subjects** unless a subject is *clearly* better with another option (95% interval of the difference leaves out 0). Then that subject gets its own setting, applied in Phase 6 (the system reads settings per subject).
- **Sample size:** 15 RAG questions per subject is small. If a subject looks different but is not clear, the RAG test set can grow to 30 per subject (90 questions; about $0.15 more for gold evidence and answers); the 45 frozen questions stay inside it so old results remain comparable.
- **Output:** `eval/results/rag_settings_by_subject.md`: Setting | Option | Ibadah | Jawi | Tajwid | Overall, plus the per-subject selection.

---

## Phase 2: Reading PDFs, chunking and embedding (≈ $0.15)

**Done 1 Nov 2026 (spent ≈ $0.08).** Scripts: `eval/rag_phase2.py` (2.1 + 2.2), `eval/ocr_eval.py` (2.3 + 2.4).
Results: `eval/results/embedding_models.md`, `chunking_by_subject.md`, `ocr_eval.md`; figures `fig_4_13`–`fig_4_15`.
Tesseract 5.5 was installed from conda-forge into `%USERPROFILE%\tesseract-env` (no admin needed); its Arabic models are in `eval/cache/tessdata/`.

### 2.1 Embedding models (planned decision D7)
- **Why:** "every model has a different rate"; embedding was never compared.
- **What:** R3 retrieval with different embedding models, same gold evidence (`rag_gold.json`, so scoring is free):
  - `BAAI/bge-m3` (current)
  - `intfloat/multilingual-e5-large`
  - `intfloat/multilingual-e5-base`
  - `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (small, fast)
- **Metrics:** hit rate, evidence recall, precision, MRR (with 95% CI), Jawi-script questions separately, index time and model size. A full RAG answer run only for the best two (≈ $0.05).
- **How:** extend `rag_settings.py` with an `embedding` setting (the in-memory index already re-embeds per setting).
- **Output:** new row "Embedding model" in the settings table + figure.

### 2.2 Chunking method per subject
- **Why:** the three books are built differently, so the best way to cut them into chunks may differ (Phase 1.5 only tested chunk *size*):
  - **Jawi**: spelling tables, one word per row (Rumi | Jawi);
  - **Tajwid**: a rule followed by its Quran examples;
  - **Ibadah**: paragraphs (meaning, ruling, niat, fadhilat).
- **Methods compared** (each used with R3, same everything else):
  | Method | How it cuts | Expected to suit |
  |---|---|---|
  | A. Section + size (current) | one chunk per `##` section, split at 1,500 characters | Ibadah |
  | B. Fixed window | every 600 characters with 100 overlap, ignoring headings (the common default in RAG papers) | baseline |
  | C. Sub-section | one chunk per `###` sub-heading, so each rule keeps its own examples | Tajwid |
  | D. Table rows | each table row (or small group of rows) is a chunk, with the table's heading and column names repeated | Jawi |
  | E. Bilingual pair | each Rumi line kept with its Jawi line | Ibadah, Jawi |
  | F. Semantic | cut where the meaning changes (bge-m3 similarity between neighbouring sentences drops) | all |
- **Chunk overlap** (characters repeated from the end of one chunk at the start of the next): **0, 100, 200**, tested on the fixed window (B, where overlap is the textbook setting) and on the current method A (whose overlap today is "the last paragraph if it is short").
- **Metrics:** hit rate, evidence recall, precision, MRR (free: the gold evidence is per textbook line, so it does not depend on how the text is chunked); factual correctness and faithfulness for the 2 best methods per subject (≈ $0.05). All **per subject** with 95% CI.
- **Decision:** a subject gets its own method only if it is *clearly* better there (interval leaves out 0); a mixed setup (e.g. D for Jawi, C for Tajwid, A for Ibadah) is then compared against the best single method.
- **How:** new chunkers in `backend/app/kb/chunking.py` (pure functions, unit-tested); `rag_settings.py` gets a `chunker` setting; the live index is only rebuilt in Phase 6 if a new method is chosen.
- **Output:** `eval/results/chunking_by_subject.md` + figure (evidence recall per method × subject).

### 2.3 Ways of reading a scanned page (OCR)
- **Why:** "compare models' ability to read PDF"; Jawi books are scanned images.
- **What:** take 10 textbook pages whose notes are already in `data/knowledge/` (the reference text), and read them with:
  1. PyMuPDF text layer (no OCR; expected to fail on images)
  2. Tesseract OCR with Arabic (free, local; needs a one-time install)
  3. Claude Haiku 5.5 vision (the current method)
  4. GPT-6 Luna vision
- **Metrics:** character error rate (CER) and word error rate for the Jawi text and for the Arabic Quran text separately, number of `[TIDAK JELAS]`, cost and time per page.
- **How:** new `eval/ocr_eval.py` using pages from `data/raw/<book>/pages/`.
- **Output:** `eval/results/ocr_eval.json/.md` + figure (CER per method).
- **Cost:** ≈ $0.03.

### 2.4 Different kinds of pages
- **Why:** "some books have many pictures, some are full text; math vs history read differently".
- **What:** label the 10 pages in 2.3 by kind (text-heavy, table, picture-heavy, Quran verse) and report CER per kind; for RAG, report retrieval metrics per kind of section (text, table, list).
- **Output:** extra columns in 2.3 and 1.4 (no extra cost).

---

## Phase 3: Arabic and Malay open-source models (free on Colab)

**Finding (checked 1 Nov 2026):** Jais, Falcon, ALLaM and Fanar are **not** on OpenRouter. They run on Google Colab like Qwen, with their own notebook `notebooks/open_models_colab_server.ipynb` (same link + key API as the Qwen notebook; both are open, not gated, 9B Gemma-2 models).

### 3.1 Models to test (decided: the 2 best fits only)
| Model | Hugging Face id (to confirm before running) | Size | Why chosen |
|---|---|---|---|
| **Fanar** | `QCRI/Fanar-1-9B-Instruct` | 9B | Best fit of the supervisor's four: Arabic, and trained with Islamic content (the KAFA subjects) |
| **SEA-LION** | `aisingapore/Gemma-SEA-LION-v3-9B-IT` | 9B | The Malay model: Jawi is Malay written in Arabic script, so a Malay model may read it better than an Arabic one |
| Qwen3-4B | current | 4B | The existing open model (Step 1, not yet run): the baseline for both |

Not tested (reason for the report): Jais and ALLaM are Arabic-only like Fanar but without the Islamic-content focus; Falcon is a general model. Their published rankings go in the report.

**GPU (you have a Google paid plan):** if Colab offers an **L4 (24 GB)** or **A100 (40 GB)** under *Runtime → Change runtime type*, the models run in **16-bit, not 4-bit**: fairer (no quality loss from compression) and 2–4× faster. A free T4 (15 GB) still works in 4-bit. Paid GPUs use Colab compute units, so stop the runtime when a test ends.

### 3.2 Experiments per model
1. **Marking (E1):** proposed system with R3 + A2 + memory off on the 50 teacher answers (same as Step 1), so the result sits next to Luna / Haiku / Llama.
2. **Jawi reading test:** 30 short Jawi items (spelling, Jawi ↔ Rumi), scored automatically: can the model read and write Jawi at all?
3. **JSON reliability:** share of replies that follow the marking format (small models often fail here; a failure is a finding, not a bug).
- **Metrics:** QWK with 95% CI, exact, success rate, time per answer, GPU memory.
- **Output:** new rows in the Step 1 table and figure "LLM models"; `eval/results/open_models.md`.

### 3.3 What you do
For each model: open `notebooks/open_models_colab_server.ipynb` in Colab, choose the model in cell 3 (Fanar / SEA-LION), Run all, paste the link into **Admin → Qwen on Colab**. I run the tests and save the results. About 15–25 minutes per model (most of it downloading the model).

---

## Phase 4: Fine-tuning and a hybrid model (free on Colab)

### 4.1 Data (already exists)
| Set | Answers | Use |
|---|---|---|
| Silver training set (`data/silver/*_train`) | 263 paraphrase + 1,283 rule-made = 1,546 | Fine-tuning |
| Silver test set | 163 + 322 | Check during training |
| Teacher set (final marks) | 50 | **Final test only**, never trained on |

### 4.2 Fine-tuning (LoRA): only after Phase 3
- **Order (decided):** first compare all LLMs (Phase 3 + Step 1), then fine-tune **the best open model** (Qwen3-4B, Fanar or SEA-LION: whichever has the highest QWK). GPT-6 Luna and Claude Haiku are API models: their weights cannot be fine-tuned, so they stay as the commercial reference.
- **What:** teach the chosen model to mark one rubric criterion → `ya / separa / tidak` + reason, in the same JSON format.
- **How:** Unsloth + LoRA on Colab (L4/A100: ≈ 15–30 minutes per run; T4: ≈ 45–90 minutes); a new notebook `notebooks/finetune_marker.ipynb` that I write; the fine-tuned model is served by the same Colab server.
- **Hyperparameters (small grid, as the supervisor suggested):** LoRA rank 8 vs 16; 1 vs 2 epochs; learning rate 2e-4. 2–4 runs.
- **Compare:** base model vs fine-tuned, on the 50 teacher answers (QWK + 95% CI), especially the *separa* rate and Jawi.
- **Risk:** the training answers are AI-written (silver), so the model may learn the AI's style. That is a finding to report either way.

### 4.3 Hybrid model (open-source + commercial)
- **Idea:** cheap or local model first, commercial model only when needed.
  - Router A: short Tahap 1 questions → local model; structured/essay → GPT-6 Luna.
  - Router B: local model marks first; if its confidence is low or the reply is invalid → GPT-6 Luna.
- **Compare:** QWK (95% CI), API cost per 100 answers and time, against Luna alone and the local model alone.
- **How:** a `hybrid` system in `backend/app/assess/llm_marking.py` (config `hybrid:qwen+luna:R3:A2`), evaluated with `experiments.py`.
- **Output:** a row in the results table and a point in the "accuracy vs cost" figure.

### 4.4 Decision point
If the fine-tuned model does not beat the base model, keep the result (supervisor: do not throw away failed experiments) and report it as the research gap (little fine-tuning work for Jawi).

### 4.5 How it was run (2 Nov 2026)
- **Model:** Qwen3-4B, the best open model of Phase 3 (QWK 0.694 on the L4; SEA-LION 0.685, Fanar 0.624).
- **Data** (`eval/phase4.py data`, $0.20): 490 training + 88 validation answers (`data/finetune/kafa_marker_sft.jsonl`, `eval/results/finetune_data.md`). Each is the exact R3 + A2 request; the reply to learn = the silver verdicts with GPT-6 Luna's reasons and feedback, kept only where Luna's verdicts equal the silver labels (96% of criteria agreed). Training: all paraphrase answers + 40 per programmatic kind; validation: other questions (test split). Few *separa* targets (40), because Luna rarely gives *separa*.
- **Training** (`notebooks/finetune_marker.ipynb`): QLoRA with transformers + PEFT on the same 4-bit model (not Unsloth: fewer version problems on Colab), lr 2e-4 kept constant after warm-up so the epoch-1 adapter equals a 1-epoch run; rank 8 and 16 for 2 epochs each = 4 adapters. Tested end to end on the laptop GPU first.
- **Choice before the teacher test:** the adapter with the lowest validation loss is the one used in the hybrid; all 4 are still tested on the 50 teacher answers (`eval/phase4.py eval`).
- **Hybrid** (`eval/phase4.py report`): built from the saved runs (no model calls, exactly what the hybrid returns). Router A (by Tahap), Router B (invalid or *separa* → Luna) and Router C (invalid or differs from the rule-based scorer B2 → Luna). First result with base Qwen: Router A QWK 0.785 at half Luna's cost (not significantly above Luna alone). Output: `eval/results/phase4.md`, `fig_4_17_phase4.png`.
- **Results (2 Nov 2026, Colab L4, 47 min of training per rank):**
  - Validation loss picked **r8e2** (0.290; r16e2 0.292, r16e1 0.301, r8e1 0.312).
  - On the teacher answers every adapter scored at least as high as base Qwen (0.694): r8e2 0.701, r16e1 0.701, r8e1 0.741, r16e2 0.743 (GPT-6 Luna 0.755). No change is significant: the 95% intervals are about ±0.15 with 50 answers.
  - Every adapter gave a valid mark on all 50 answers (base Qwen 94%).
  - Side effect: almost no *separa* (0–4%, teachers 17%), since Luna rarely gives it and the targets copy Luna. Answers took 25–27 s (LoRA not merged; base 18 s).
  - Jawi test 13% (base 7%, Luna 70%).
  - Hybrid with the fine-tuned r8e2: Router A 0.733, below the hybrid with base Qwen (0.785). The best hybrid stays base Qwen + Luna, Router A.

---

## Phase 5: Database description (for the meeting in ~2 sessions)
- **What:** `scripts/describe_db.py` writes `docs/database.md`:
  - ChromaDB: the 2 collections (`kafa_notes`, `kafa_refs`), how IDs are built (`<topic_id>::s<section>p<part>`), metadata fields, counts per subject, one example record each, the embedding model and distance;
  - SQLite: the pupil memory tables and their fields;
  - where the JSON files sit (notes, questions, books, runtime settings).
- **Cost:** free.
- **Done (2 Nov 2026):** `docs/database.md` is generated from the live stores. It covers `kafa_notes` (339 chunks, 48 topics), `kafa_refs` (382 reference answers), the 5 SQLite tables (row counts only, no pupil data) and the file locations. It also shows that no note is marked `verified` by a teacher yet.

---

## Phase 6: Final rerun
1. Decide which RAG settings to apply (from the settings study: 5 sections, 0.35 similarity, lower Tanya Bulan's 0.55 gate), and any **per-subject settings** found in 1.5 (the R3 retriever then reads its settings by subject).
2. Choose the final configuration (Phase 1–4 results).
3. Re-run Steps 0–4 on the final teacher marks only where something changed; most answers come from the cache.
4. Re-run `final_stats.py`, `rag_stats.py`, `make_figures.py` so every table and figure uses the final setup.
- **Cost:** ≈ $0.10.

### 6.1 How it was run (2 Nov 2026)
- **Decisions (the researcher):**
  1. Apply the RAG settings study's choices.
  2. The final system is GPT-6 Luna alone: `proposed:luna:R3:A2:off`.
  3. Jawi spelling stays exact: no *separa* for a one-letter miss. On the 50 teacher answers, 9 spellings were one letter off; teachers marked 5 wrong, 3 right and 1 partly right.
- **Per-subject settings (1.5):** none. No subject is clearly better with another option, so one setting is used for all subjects.
- **R3 for marking:** the study measured answering, so its R3 choices (6 chunks, 5 sections, minimum 0.35) were first rerun on the teacher set (steps 2–4 and the Haiku check) and checked on silver development answers (`eval/r3_marking_dev.py`).
  - Silver answers could not separate the settings: QWK 0.960–0.964, and the minimum removed nothing.
  - On the teacher set the final system dropped significantly: 0.755 → 0.695 (−0.060, 95% CI −0.152 to −0.002). Haiku also dropped (−0.094).
  - **Decision:** marking keeps the earlier R3 (4 chunks, 3 sections, no minimum). The 5-section runs are archived in `eval/results/archive/r3_study_settings_2nov/`, and the results are in `eval/results/r3_marking_dev.md`.
- **Tanya Bulan:** the gate went from 0.55 to 0.35. The study's decline rule ("if the textbook text does not contain the answer, reply exactly: Data ini tiada dalam pangkalan data saya.") was added to its prompt, because the study's 24/24 declines were made by a model with that rule. The textbook-only fallback keeps 0.55, since it cannot decline. Tested in `backend/tests/test_chat_gate.py`.
- **Statistics:** `final_stats.py` now compares every run with the final system rather than the highest QWK. The simulated hybrids are marked ‡.
- **Rebuilt from the final runs:** phase4, open_models, human_vs_ai, react_eval, teacher_compare, rag_stats, rag_why, final_stats and make_figures.
- **Cost:** $0.24 for Phase 6 (teacher-set reruns, grounding, silver check). Total API spend: $2.00 of the $4 budget.

---

## Order and checkpoints
1. **Phase 1** (1.1 → 1.4): show you the new tables, you check them.
2. **Phase 2**: embedding + OCR results, you check.
3. **Phase 3**: one model at a time while you run Colab.
4. **Phase 4**: after Phase 3 (the best open model is fine-tuned).
5. **Phase 5**: before the meeting with your supervisor.
6. **Phase 6**: last, after all decisions.

## Not in this plan (report work, later)
Chapter 3 text (CI formula, instruments), screenshots of code, model justification from past studies and LLM rankings, comparison with other researchers' published results.

## Decisions (1 Nov 2026)
1. Phase 3: only the 2 best-fitting open models: **Fanar** and **SEA-LION** (plus Qwen3-4B as the baseline).
2. Phase 4: fine-tune **after** all LLMs are compared, on the best open model.
3. Phase 2.3: Tesseract OCR may be installed.
4. GPU: you have a paid Google plan; use an L4/A100 in Colab if offered (16-bit models), else a T4 (4-bit).
