# Implementation Plan v2: Complete the System and Run the Evaluation

Follows **Blueprint FYP v0.4** (25 October 2026). The first plan (`IMPLEMENTATION_PLAN.md`) built the working app; this plan adds what the blueprint still needs: API language models, the three RAG types, the three ReAct types, the baselines, the evaluation (E1, E2, E3) and an **Evaluation page in the sidebar**.

Status (25 Oct 2026): **phases 1–9 built**; experiments run on the silver development set. Waiting for the teachers' Google Form marks (E1) and the A/B and SUS forms (E3). Defaults used: models below, budget $4, the 📊 Penilaian page only in researcher mode (`KAFA_RESEARCHER_MODE`).

---

## 1. Where the system is now

| Blueprint part | Status today | Work needed |
|---|---|---|
| Web app (sidebar, light/dark, Rumi/Jawi) | Done (React + FastAPI) | Add the Evaluation page |
| Knowledge base (48 notes, ChromaDB, bge-m3) | Done | Add parent-document view (R3) |
| Hybrid retrieval (BM25 + dense, RRF) | Done, no reranker | Add reranker (R2) |
| Rubric scoring | Done: rules + embedding similarity (no LLM) | Becomes **baseline B2**; LLM marking is new |
| Student memory (SQLite) | Done | Add memory on/off switch for the ablation |
| 5-step pipeline | Done, fixed order | Becomes the base of **A2 (constrained ReAct)** |
| LLMs M1–M4 via API | Not started | New: OpenRouter client |
| Local model M5 | Qwen2.5-3B (4-bit) runs locally for chat | Reuse it as M5 |
| Baselines B1, B3, B4 | Not started | New |
| ReAct A1, A3 | Not started | New |
| E1 teacher agreement | Tools ready; 50-answer Google Form waiting for teachers | Run when the marks come back |
| E2 grounding (RAGAS) | Not started | New |
| E3 blind A/B + usability | SUS form exists | Blind A/B form is new |
| Cost / latency / success rate | Latency only | Token and cost logging is new |

---

## 2. Decisions to confirm (differences from the blueprint)

These follow from what OpenRouter and the laptop can actually do. Each one will be written in the blueprint v0.5 and the thesis.

| # | Blueprint says | Plan | Reason |
|---|---|---|---|
| D1 | Embeddings via API | Keep **bge-m3 locally** | OpenRouter has no embedding models (checked 25 Oct 2026). bge-m3 already gives Recall@4 ≈ 0.93–1.00 |
| D2 | Reranker via API | **Local reranker** `BAAI/bge-reranker-v2-m3` (≈ 2.3 GB, run on CPU if GPU is full) | No reranker on OpenRouter |
| D3 | M5 = Qwen3 8B via Ollama | **M5 = Qwen2.5-3B (4-bit), already installed** | Ollama is not installed; 8B (≈ 5 GB) does not fit next to bge-m3 on the 6 GB GPU; the 3B model already runs |
| D4 | Streamlit interface | React web app (already built) | Better for children; already finished |
| D5 | Year 4 and 5 | **Year 5 only** | Only Year 5 textbooks and questions exist |
| D6 | Real pupil answers | 50 constructed answers marked by 2–4 teachers | Teachers could not release pupil work |
| D7 | Embedding model compared at Step 2 | Compare **bge-m3 vs multilingual-e5-base** (both local) | Both are local; no API embedding exists |

### Models used (decided 25 Oct 2026; replaces the blueprint's M1–M5)
The user chose 2 API models + 1 local model; Llama 3.1 8B is kept as an almost-free weak control baseline.

| Key | Model | OpenRouter name | Input / 1M | Output / 1M | Role |
|---|---|---|---|---|---|
| `haiku` | Claude Haiku 5.5 (Oct 2026) | `anthropic/claude-haiku-5.5` | $0.10 | $0.50 | API model 1 |
| `luna` | GPT-6 Luna (Sep 2026) | `openai/gpt-6-luna` | $0.10 | $0.50 | API model 2 |
| `llama` | Llama 3.1 8B | `meta-llama/llama-3.1-8b-instruct` | $0.05 | $0.08 | control baseline (from the proposal) |
| `qwen` | Qwen3-4B-Instruct-2507, 4-bit (local) | `unsloth/Qwen3-4B-Instruct-2507-bnb-4bit` | free | free | local / privacy option (replaces Qwen3 8B, which does not fit the 6 GB GPU) |

The E2 judge is always from another provider: Haiku's feedback is judged by GPT-6 Luna, all others by Haiku.

The API key is stored in `.env` as `KAFA_OPENROUTER_API_KEY` (git-ignored). Credit available: **$5.00**.

---

## 3. What will be built

### Phase 1: API model layer
- `backend/app/llm_api.py`: one client for OpenRouter (and M5 local) with the same interface: `complete(messages, model, json_schema=None, tools=None)`.
- Settings fixed for repeatable marking: temperature 0, seed where supported, JSON output.
- Retries with back-off for rate limits and outages; timeout per call.
- **Every call logged** (model, tokens in/out, cost, time, success) to `storage/llm_calls.jsonl`.
- **Response cache** on disk: the same prompt and model are never paid for twice.
- **Privacy**: only the question, rubric, textbook text and answer text are sent. No names, classes or IDs.

### Phase 2: Pluggable markers (baselines + proposed system)
One interface for all markers: `mark(question, answer, student) -> per-criterion verdicts (ya / separa / tidak), score, feedback, trace, cost`.

| System | What it does | Based on |
|---|---|---|
| B1 Zero-shot LLM | LLM marks with the rubric only, no textbook retrieval | Baseline |
| B2 Embedding similarity | **The current scorer** (rules + bge-m3 similarity) | Dara and Cheng |
| B3 RAG + rubric | Retrieve textbook text, then mark in one LLM call | Barenji; Sundar |
| B4 RAG + rubric + verifier | B3, then a second call checks the feedback is supported by the text | Reza |
| **Proposed** | Rules layer (exact Jawi spelling, Betul/Salah, numbers) **+ ReAct LLM agent + student memory** | This project |

The proposed system keeps the rules layer because an LLM is unreliable at exact Jawi spelling; the LLM only judges what the rules cannot decide.

### Phase 3: Three RAG types
| ID | Retrieval | Notes |
|---|---|---|
| R1 | Dense only (bge-m3 in ChromaDB) | Turn off BM25 |
| R2 | Hybrid BM25 + dense + **reranker** | Current retriever plus `bge-reranker-v2-m3` |
| R3 | Parent-document | Match small chunks, pass the **whole note section** they come from |

### Phase 4: Three ReAct types
| ID | Loop | Notes |
|---|---|---|
| A1 Vanilla ReAct | Open loop: the LLM picks tools (`search_notes`, `get_rubric`, `get_history`, `submit_marks`), max 6 steps | Shows loop / skipped-step risk |
| A2 Constrained ReAct | Fixed order (rubric → retrieve → memory → mark → feedback), strict JSON at each step | Built on the current 5-step pipeline |
| A3 Reflexion | A2 draft, then a critic checks leniency for Year 5 and syllabus limits, and may revise once | Closest to a teacher |

Memory: a switch `memory=on|off`. When on, only the **last 3 mistakes and 2 weakest topics** go into the prompt.

### Phase 5: Experiment runner
`eval/experiments.py` runs the **staged plan** from blueprint §6.2 on a test set and saves one result file per run in `eval/results/experiments/`.

| Step | Compare | Fixed | Runs |
|---|---|---|---|
| 0 | Baselines B1–B4 vs B2 (current) | best model | 4 |
| 1 | Models M1–M5 | R1, A2, memory off | 5 |
| 2 | RAG R1–R3 (+ bge-m3 vs e5) | best model | 3 (+1) |
| 3 | ReAct A1–A3 | best model + RAG | 3 |
| 4 | Final: memory on vs off, 3 repeats for consistency | best of all | 2 + repeats |

Metrics per run: **QWK, exact agreement, adjacent agreement (within 1 mark), MAE**, over-/under-marking, keyword-illusion check, **CoV over repeats**, latency (mean, p95), tokens, **cost per 100 answers**, success rate (valid JSON, no API error). The model name, version and test date are recorded in every result file.

Test data:
- **Development**: the silver test set (AI-marked). Used to build and debug only; never reported as the main result.
- **Main result**: the 50 teacher-marked answers (E1), once the Google Form responses are in.

### Phase 6: E2 grounding (RAGAS-style)
- **Faithfulness**: split the feedback into claims, ask a judge model whether each claim is supported by the retrieved text.
- **Context recall**: does the retrieved text contain what the reference answer needs.
- **Context precision**: how much of the retrieved text is relevant.
- **Unsupported-claim count** (error analysis, the main guard against wrong rulings).
- Judge model from **a different provider** than the model under test (e.g. GPT-4o-mini judges Claude; Gemini judges GPT).
- Implemented directly (following the RAGAS definitions) instead of installing the `ragas` library, so it works with OpenRouter and bge-m3 and the prompts can be shown in the thesis. A hand-checked sample of 20 judgements confirms the judge.

### Phase 7: E3 expert blind A/B and usability
- `scripts/ab_form.py`: makes a Google Form (same Apps Script method as the marking form). For each sample, teachers see **feedback A and B** (memory on / off, order shuffled) for the same pupil history and pick the one that fits better. Result: **memory win-rate**.
- Teacher feedback rating (1–5) for religious correctness, relevance, clarity for Year 5, usefulness of the next step.
- SUS for teachers (form exists: `docs/SUS_soal_selidik.md`, scorer: `scripts/sus_score.py`) and a smiley rating for pupils.

### Phase 8: Evaluation page in the sidebar
New sidebar item **📊 Penilaian** (under a "Penyelidik" heading, below the subjects), route `/penilaian`. Read-only: it shows results; it does not spend API credit.

| Tab | Shows |
|---|---|
| Ringkasan | Blueprint targets with ✅ / ❌ (QWK ≥ 0.70, adjacent ≥ 85%, faithfulness ≥ 0.85, recall ≥ 0.80, memory win-rate ≥ 65%, Likert ≥ 4, SUS ≥ 68), best configuration, total cost |
| E1 Ketepatan | Teacher agreement between teachers (Fleiss / Cohen), system vs teachers by subject and level, largest disagreements |
| Eksperimen | The experiment matrix: tables and bar charts per step (models, RAG, ReAct, baselines) with QWK, cost, latency |
| E2 Grounding | Faithfulness, context recall, context precision, unsupported claims |
| E3 Pengguna | Memory win-rate, teacher ratings, SUS, pupil smileys |
| Kos & Prestasi | Tokens, cost per 100 answers, latency, success rate per model |

Backend: `GET /api/eval/summary` reads the files in `eval/results/` and returns one JSON. Each tab says clearly whether its numbers are **silver (development)** or **teacher-marked (final)**, and shows "Belum ada data" until a run exists.

### Phase 9: Use the winner in the app
- The best configuration becomes the live marker (setting `KAFA_SCORER=…`).
- If the API is down or the credit runs out, the app **falls back to B2** (the current local scorer), so pupils are never blocked.

### Phase 10: Documents
- Update `SYSTEM_DETAIL.md`, blueprint v0.5 (decisions D1–D7, results), and results tables for the thesis.

---

## 4. Budget (rough estimate)

Assumptions: about 2,500 input and 300 output tokens per LLM call; A1/A3 use about 3 calls per answer; the response cache removes repeats.

| Part | Calls (≈) | If best model is GPT-4o-mini / Llama / Gemini | If best model is Claude Haiku |
|---|---|---|---|
| Development on silver set (small samples) | 600 | $0.30–0.80 | $0.30–0.80 (cheap model used) |
| Steps 0–3 on 50 teacher answers | 1,200 | $0.40–1.50 | $2.50–4.00 |
| Step 4 final + repeats + memory | 700 | $0.20–1.00 | $2.00–3.00 |
| E2 judge calls | 500 | $0.20–0.50 | $0.20–0.50 |
| **Total** | **≈ 3,000** | **≈ $1–4** | **≈ $5–8** |

$5 is enough unless Claude Haiku wins Step 1, in which case about **$3–5 more credit** may be needed. The runner stops before spending more than a set limit (default **$4**) and shows the running total.

---

## 5. Order of work

| # | Work | Depends on |
|---|---|---|
| 1 | Phase 1 API layer + cost log + cache, test with 1 call per model | approval |
| 2 | Phase 2 markers B1, B3, B4 + output schema | 1 |
| 3 | Phase 3 RAG R1, R2, R3 | — |
| 4 | Phase 4 ReAct A1, A2, A3 + memory switch | 2, 3 |
| 5 | Phase 5 runner, dry runs on a small silver sample (≈ $0.50) | 4 |
| 6 | Phase 8 Evaluation page (works with the dry-run results) | 5 |
| 7 | Phase 6 E2 grounding | 4 |
| 8 | Full runs on the 50 teacher answers | teacher marks |
| 9 | Phase 7 blind A/B form + SUS | 8 (final config) |
| 10 | Phase 9 winner in the app, Phase 10 documents | 8, 9 |

Steps 1–7 can be done now; step 8 waits for the teachers' Google Form responses.

---

## 6. Risks

| Risk | Response |
|---|---|
| Credit runs out | Cache, spending limit, staged runs, development on a cheap model |
| Provider changes a model | Model name + date saved in every result; rerun key tests before the final report |
| Rate limits / outages | Retries with back-off; failed calls counted in the success rate |
| LLM invents a ruling | Feedback must cite the retrieved text; E2 counts unsupported claims |
| Small local model fails JSON | Counted as a failure for M5 (this is a finding, not a bug) |
| GPU memory (reranker + bge-m3 + Qwen) | Reranker on CPU; local model tests run separately from API tests |
| Children's data sent abroad | Only answer text is sent; supervisor confirms consent (blueprint §6.5) |

---

## 7. Questions before starting

1. Do you approve decisions **D1–D7**?
2. Spending limit for the runner: **$4** (keep $1 spare)?
3. Who can see the **📊 Penilaian** page: everyone in the sidebar, or only when a researcher setting is on (so pupils don't see it)?
