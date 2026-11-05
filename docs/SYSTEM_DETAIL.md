# System Detail: KafAI UPKK (Intelligent KAFA UPKK Learning Assistant)

This document explains every technical component of the system in detail —
what data is used, where it lives, which databases and models are involved,
and how every piece connects together.

---

## 1. Overview

This is a **Hybrid LLM + RAG** learning assistant for Year 5 KAFA students
preparing for the **UPKK** exam. It covers three subjects:

| Subject | Local Name | Topics |
|---------|-----------|--------|
| Ibadah (Fiqh) | Fiqh | Solat sunat (rawatib, dhuha, tahajud, tarawih, witir, gerhana, hajat, hari raya, istikharah, taubat), Puasa |
| Jawi | Jawi | Imbuhan `-an`, Kata pinjaman (Arab, Inggeris), Akronim |
| Tajwid | Tajwid | Mad Asli, Mad Far'i (16 jenis), Waqaf, Ibtida' |

The student types an answer in Bahasa Melayu (Rumi or Jawi script).
The system:
1. Retrieves relevant textbook passages (RAG)
2. Scores the answer against a rubric (rules + embeddings)
3. Gives detailed adaptive feedback with the correct answer and its textbook page

---

## 2. Data

### 2.1 Knowledge Notes (`data/knowledge/`)

48 topic notes written from the official Year 5 KAFA textbooks. Each note is a Markdown file with YAML front-matter.

```
data/knowledge/
├── fiqh/     (16 files, e.g. fiqh_b1_solat_rawatib.md)
├── jawi/     (10 files, e.g. jawi_b3_pinjaman_inggeris.md)
└── tajwid/   (22 files, e.g. tajwid_b3_mad_badal.md)
```

**Front-matter fields in every note:**

```yaml
---
id: tajwid_b3_mad_badal
subject: tajwid
bab: 3
bab_rumi: "Mad Far'i"
bab_jawi: "مد فرعي"
topic_rumi: "Mad Badal"
topic_jawi: "مد بدل"
source: "Buku Teks Tajwid JAIS Tahun 5"
pdf_pages: [22, 23]
book_pages: [14, 15]
verified: false
---
```

**Note body format:** headings `##` for sections (Pengertian, Contoh, Lafaz Niat, etc.), each section written in both Rumi and Jawi on separate lines.

**Size:** 48 notes total, ~1,500–3,000 characters each.

---

### 2.2 Question Bank (`data/questions/`)

382 questions with reference answers and rubrics stored as JSON files.

```
data/questions/
├── fiqh/     (17 files — 15 topic files + 2 latihan/exercise files)
├── jawi/     (10 files)
└── tajwid/   (22 files)
```

**Question distribution:**

| Level | Count | Description |
|-------|-------|-------------|
| Tahap 1 | 204 | Short answer (1–2 sentences) |
| Tahap 2 | 131 | Structured (list 2–4 points) |
| Tahap 3 | 47  | Essay / elaborate |
| **Total** | **382** | — |

**Structure of one question file:**

```json
{
  "subject": "tajwid",
  "topic_id": "tajwid_b3_mad_badal",
  "questions": [
    {
      "id": "tajwid_b3_mad_badal_q1",
      "level": 1,
      "type": "short",
      "origin": "textbook",
      "max_marks": 1,
      "question_rumi": "Apakah yang dimaksudkan dengan Mad Badal?",
      "question_jawi": "اڤاكه يڠ دمقصودكن دڠن مد بدل؟",
      "reference_answer_rumi": "Mad Badal ialah mad yang berlaku apabila hamzah menggantikan huruf mad.",
      "reference_answer_jawi": "مد بدل اياله مد يڠ برلاكو اڤابيلا همزه مڠڬنتيكن حروف مد.",
      "rubric": [
        {
          "criterion": "Hamzah menggantikan huruf mad",
          "marks": 1,
          "keywords": ["hamzah", "menggantikan", "حروف مد"]
        }
      ],
      "source_pages": [22]
    }
  ]
}
```

Every question has:
- **Bilingual** text (Rumi + Jawi)
- **Reference answer** in both scripts
- **Rubric** — one or more criteria, each with marks and keywords

---

### 2.3 Silver Training Data (`data/silver/`)

382 synthetic answers used to tune the scoring model (no real student answers yet).

| File type | Count | Description |
|-----------|-------|-------------|
| `paraphrase_train_*.json` | 263 | AI-written pupil-style paraphrases, marked by AI teacher |
| `programmatic_train.json` | 183 | Rule-built answers (reference copy, Jawi typo, wrong number, etc.) |
| `paraphrase_test_*.json` | ~100 | Held-out test set |

---

### 2.4 Splits (`data/splits/`)

80/20 train/test split stratified by subject and level (random seed 42).

- `train.json` — 306 question IDs
- `test.json` — 76 question IDs (used once for evaluation, never for tuning)

---

## 3. Models

### 3.1 Large Language Model (LLM)

| Item | Detail |
|------|--------|
| **Model ID** | `unsloth/Qwen2.5-3B-Instruct-bnb-4bit` *(Default active model)*<br>*(Fallback: `mesolitica/Malaysian-Llama-3.2-1B-Instruct`)* |
| **Source** | Hugging Face (downloaded offline to `models/`) |
| **Parameters** | 3.09 billion (Qwen 2.5) / 1 billion (Malaysian-Llama baseline) |
| **Purpose** | AI Chat assistant answers (`/api/chat`), optional encouragement generation |
| **Precision** | 4-bit NormalFloat4 (NF4) via `bitsandbytes` on CUDA (float16 fallback for 1B) |
| **VRAM usage** | **~2.05 GB** for LLM (peak system VRAM ~3.86 GB with `bge-m3` embedder loaded) |
| **Speed** | ~11–20 tokens/s on RTX 3050 Laptop GPU; chat responses in ~2.5–5.0 s |
| **Why this model** | 3B parameter reasoning scale delivers superior reading comprehension, syntactic parsing in Bahasa Melayu, strict adherence to negative constraints, and zero token-level looping loops |
| **Cache directory** | `models/` |

**Important:** The LLM is **NOT used for rubric scoring** (scoring runs purely on `bge-m3` embedding cosine similarity + deterministic rule matching for speed, 100% determinism, and zero hallucination risk).

The LLM is used for:
1. **AI Chat** (`/api/chat`) — answers free-form student questions grounded in retrieved textbook chunks with intent-aware section routing and extractive anchoring
2. **Encouragement line** (optional, off by default) — a short 1–2 sentence motivational sentence after each question attempt
3. **Structured Pedagogical Guardrails** — handles out-of-syllabus questions with standardized disclaimers, suppressing irrelevant syllabus sources

#### 3.1.1 ReAct Reasoning & Guardrail Architecture in AI Chat

The system incorporates **ReAct (Reasoning + Acting)** and extractive anchoring to guide how the AI Chat assistant processes queries:

1. **Structured Flow (`Thought -> Retrieval -> Observation & Thresholding -> Guarded Generation`):**
   - **Thought:** The model analyzes the student's question and identifies pedagogical intent (*fadhilat, niat, waktu, rakaat, hukum, syarat, rukun, kaifiat, pengertian*).
   - **Action:** The system queries ChromaDB and BM25 (`search_notes`) and reranks hits by matching sections.
   - **Observation & Thresholding:** The system computes the top semantic cosine similarity against ChromaDB vector store (gates from the RAG settings study, Section 5.4, applied on 2 Nov 2026).
     - If `score >= 0.55`: a **strong match**. Anchor facts are extracted directly from the textbook note.
     - If `0.35 <= score < 0.55`: a **weak match**. The model gets the passages and the study's decline rule ("if the textbook text does not contain the answer, reply exactly: *Data ini tiada dalam pangkalan data saya.*"), but no anchor fact. If it declines, the reply is treated as out of the notes (no sources).
     - If `score < 0.35`: Question is confirmed **NOT inside the vector database**.
     - Without a model (no Qwen locally or on Colab), the textbook-only fallback cannot decline, so only strong matches are answered from the notes, and only when a key fact can be taken from the top note.
     - `eval/chat_gate_eval.py` asks the live chat the RAG evaluation's 45 textbook and 24 off-syllabus questions with the model it really uses (Qwen on Colab or locally; `--no-model` for the fallback) and counts the declines.
   - **Response Generation:** The model generates a short (1–3 sentences), child-friendly answer.

2. **Handling Missing Vector Database Data (`Data ini tiada dalam pangkalan data saya`):**
   - **The Problem:** When pupils ask about non-syllabus topics (e.g., *"Bagaimanakah cara membuat kek coklat?"*, *"Siapakah perdana menteri pertama Malaysia?"*, *"Apakah itu dinosaur?"*), standard RAG retrieves low-similarity textbook chunks by coincidence and hallucinates false religious connections (e.g. associating cake recipes with Quran recitation rules).
   - **Vector DB Guardrail:** When the ChromaDB dense cosine score is below `0.35`, when the model declines a weak match, or when there is nothing to show (no model reply and no textbook key fact, e.g. no model for a weak match):
     - Misleading textbook sources are completely suppressed (`sources = []`).
     - The assistant is strictly instructed and programmatically enforced to start its response with:
       > **"Data ini tiada dalam pangkalan data saya."** *(or "This data is not in my database." for English queries)*
     - It then provides a concise, polite general knowledge reply (1–2 sentences) without confusing religious or UPKK syllabus terms.

3. **Extractive Factual Anchoring & Safety Fallback:**
   - For syllabus questions, `_extract_anchor_fact()` extracts the exact verified bullet points (e.g. exact rakaat count or lafaz niat) directly from the textbook note.
   - If the LLM generates an incomplete or wandering answer, the system automatically falls back to:
     > *"Berdasarkan buku teks [Topik] (ms. [X]): [anchor]"*

---

### 3.2 Embedding Model

| Item | Detail |
|------|--------|
| **Model ID** | `BAAI/bge-m3` |
| **Source** | Hugging Face (offline in `models/`) |
| **Type** | Multilingual bi-encoder (BERT-style) |
| **Purpose** | Vectorise note chunks, reference answers, and student answers for similarity scoring and retrieval |
| **Vector dimension** | 1024 |
| **Why this model** | Strong on both Rumi and Jawi text; retrieval Recall@4 = 0.990 on Rumi, 0.958 on Jawi |
| **AUC for scoring** | 0.82 (separates correct from wrong answers reliably) |
| **Speed** | ~50 ms per answer on GPU |

---

## 4. Databases

### 4.1 ChromaDB — Vector Knowledge Base

**What it stores:** embeddings of textbook note chunks and question reference answers.

| Property | Value |
|----------|-------|
| **Database type** | ChromaDB PersistentClient |
| **Storage location** | `storage/chroma/` |
| **Disk size** | 7.9 MB |
| **Distance metric** | Cosine similarity |
| **Embeddings** | Supplied externally by bge-m3 (Chroma's built-in embedder is disabled) |

**Two collections inside ChromaDB:**

#### Collection 1: `kafa_notes`
Stores textbook content for retrieval (RAG).

| Property | Value |
|----------|-------|
| **What** | One document per note chunk (section of a topic note) |
| **Count** | 339 chunks from 48 notes |
| **Created by** | `backend/app/kb/ingest.py` → `build_notes()` |
| **ID format** | `tajwid_b3_mad_badal::s02p0` (topic + section index + part index) |
| **Text format** | `Topik: Mad Badal | مد بدل\nBahagian: Pengertian\n\n<section content>` |

Metadata stored per chunk:

```python
{
  "topic_id": "tajwid_b3_mad_badal",
  "subject": "tajwid",
  "bab": 3,
  "topic_rumi": "Mad Badal",
  "topic_jawi": "مد بدل",
  "source": "Buku Teks Tajwid JAIS Tahun 5",
  "pdf_pages": "22,23",
  "verified": False,
  "section": "Pengertian",
  "part": 0
}
```

#### Collection 2: `kafa_refs`
Stores reference answers for scoring similarity.

| Property | Value |
|----------|-------|
| **What** | One document per question (Rumi + Jawi reference answer concatenated) |
| **Count** | 382 documents |
| **Created by** | `backend/app/kb/ingest.py` → `build_refs()` |
| **ID format** | question ID e.g. `tajwid_b3_mad_badal_q1` |
| **Purpose** | `reference_similarity(answer, question_id)` returns cosine score used in scoring |

**How to rebuild ChromaDB:**
```bash
.venv\Scripts\python -m backend.app.kb.ingest
# Takes ~25 s; writes storage/kb_manifest.json
```

---

### 4.2 SQLite — Student Memory

**What it stores:** every student's progress, answers, mastery and badges.

| Property | Value |
|----------|-------|
| **Database type** | SQLite (Python stdlib `sqlite3`) |
| **Storage location** | `storage/kafa.db` |
| **Current size** | 108 KB |
| **Thread safety** | Single connection + `threading.RLock()` (all reads and writes serialised) |

**Schema — 5 tables:**

#### `students`
```sql
CREATE TABLE students (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    kelas       TEXT NOT NULL DEFAULT '',
    avatar      TEXT NOT NULL DEFAULT '',
    script_pref TEXT NOT NULL DEFAULT 'rumi',
    created_at  TEXT NOT NULL,
    UNIQUE(name, kelas)
);
```
One row per student. Students are identified by `(name, kelas)` — no passwords (prototype).

#### `attempts`
```sql
CREATE TABLE attempts (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id       INTEGER NOT NULL REFERENCES students(id),
    question_id      TEXT NOT NULL,
    topic_id         TEXT NOT NULL,
    subject          TEXT NOT NULL,
    level            INTEGER NOT NULL,
    answer           TEXT NOT NULL,       -- what the student typed
    score            REAL NOT NULL,
    max_marks        REAL NOT NULL,
    percent          REAL NOT NULL,
    criteria_json    TEXT NOT NULL,       -- per-criterion breakdown (JSON)
    feedback_json    TEXT NOT NULL,       -- full feedback object (JSON)
    react_trace_json TEXT NOT NULL,       -- 5 ReAct steps (JSON)
    latency_ms       INTEGER NOT NULL,
    created_at       TEXT NOT NULL
);
```
Every answer ever submitted. The `react_trace_json` column stores the full 5-step ReAct trace that the UI shows under "Bagaimana AI berfikir".

#### `mistakes`
```sql
CREATE TABLE mistakes (
    student_id INTEGER NOT NULL REFERENCES students(id),
    topic_id   TEXT NOT NULL,
    criterion  TEXT NOT NULL,
    count      INTEGER NOT NULL DEFAULT 0,
    last_seen  TEXT NOT NULL,
    PRIMARY KEY (student_id, topic_id, criterion)
);
```
Counts how many times each rubric criterion was missed. When `count >= 2`, the feedback names it as a "repeated mistake".

#### `topic_mastery`
```sql
CREATE TABLE topic_mastery (
    student_id    INTEGER NOT NULL REFERENCES students(id),
    topic_id      TEXT NOT NULL,
    subject       TEXT NOT NULL,
    mastery       REAL NOT NULL,           -- EMA of percent scores (0.0–1.0)
    attempts      INTEGER NOT NULL,
    level_unlocked INTEGER NOT NULL DEFAULT 1,
    updated_at    TEXT NOT NULL,
    PRIMARY KEY (student_id, topic_id)
);
```

**Mastery formula (Exponential Moving Average):**
```
first attempt:  mastery = percent / 100
later:          mastery = 0.7 × old_mastery + 0.3 × (percent / 100)
```

**Level unlock rule:**
- Next level opens when: last 3 attempts at the current level average ≥ 70%
- Maximum level: 3

#### `progress`
```sql
CREATE TABLE progress (
    student_id       INTEGER PRIMARY KEY REFERENCES students(id),
    xp               INTEGER NOT NULL DEFAULT 0,
    streak_days      INTEGER NOT NULL DEFAULT 0,
    last_active_date TEXT,
    badges_json      TEXT NOT NULL DEFAULT '[]'
);
```

**XP formula:** `XP = 10 × stars + 2` per attempt.
- Stars: 3 if score = 100%, 2 if ≥ 50%, 1 otherwise (always at least 1 star)

**5 Badges:**

| Badge ID | Condition |
|----------|-----------|
| `langkah_pertama` | First answer ever |
| `tiga_bintang` | Score 100% on any question |
| `tahap_2` | Unlock Level 2 in any topic |
| `tahap_3` | Unlock Level 3 in any topic |
| `rajin_3_hari` | Active 3 consecutive days |

---

## 5. RAG Pipeline

RAG = Retrieval-Augmented Generation. The system retrieves textbook chunks before scoring or answering, so the LLM/scorer only uses facts from the textbook, not hallucinated ones.

### 5.1 Chunking (how notes become chunks)

File: `backend/app/kb/chunking.py`

Strategy:
1. Split the note on `##` headings → one chunk per section
2. Long sections (> 1500 characters ≈ 400–500 tokens) are split on paragraph breaks, with the last paragraph carried over as overlap
3. Each chunk is prefixed: `Topik: <title> | <jawi title>\nBahagian: <section>`
4. Sections shorter than 40 characters are dropped

Result: 48 notes → **339 chunks**, average ~640 characters.

### 5.2 Hybrid Retrieval

File: `backend/app/kb/retriever.py`

Two retrievers are combined with **Reciprocal Rank Fusion (RRF)**:

| Retriever | How it works | Strength |
|-----------|-------------|---------|
| **Dense** (bge-m3) | Cosine similarity in ChromaDB, 1024-dim vectors | Semantic meaning, paraphrase matching |
| **Keyword** (BM25) | TF-IDF-style term frequency in `backend/app/kb/lexical.py` | Exact Jawi word matching |

**RRF formula:** `score = Σ weight / (60 + rank)`
- Dense weight = **0.25** for Jawi-script queries (bge-m3 is weaker on Arabic script than BM25)
- Dense weight = **1.0** for Rumi queries

**Search strategy:** `search_notes(query, subject, topic_id, k=4)`
1. Search inside the question's own topic first
2. If fewer than 2 hits, fill remaining slots from the whole subject

**Retrieval accuracy (test split):**
- Rumi query → Recall@4 = **1.000**
- Jawi query → Recall@4 = **0.934**

### 5.3 RAG Types (R1–R3, blueprint §6.2)

File: `backend/app/kb/rag.py` — `retrieve(query, rag="R1"|"R2"|"R3", subject, topic_id, k=4)`

| Type | How it works | Text the model reads |
|------|--------------|----------------------|
| **R1** Naive dense | bge-m3 cosine only | best chunks, up to 1,800 characters |
| **R2** Hybrid + reranker | BM25 + bge-m3 (RRF), then the cross-encoder `bge-reranker-v2-m3` (CPU) re-orders 12 candidates | best chunks, up to 1,800 characters |
| **R3** Parent-document | match the 4 best chunks (hybrid), then pass the **whole section** each comes from (at most 3) | up to 3,600 characters |

`Retrieved.given()` returns only the passages that fit the character limit; `context`, the trace and every judge use exactly these, so the evaluation scores what the model really read.

### 5.4 RAG Evaluation (📊 Penilaian → RAG Evaluation)

**Step 1 — choose the RAG type** (`eval/rag_eval.py`). 45 answerable questions from the bank (15 per subject, all levels) and 24 out-of-syllabus questions (12 general, 12 near the syllabus such as qalqalah, solat Jumaat or awalan *ber-*, checked absent from the notes). One fixed answer model (GPT-6 Luna) answers from the retrieved text only; a judge from another provider (Claude Haiku 5.5) scores it with RAGAS definitions.

| Metric | R1 Naive Dense | R2 Hybrid + Reranker | R3 Parent-Document |
|---|---|---|---|
| Context precision | 0.851 | **0.935** | 0.917 |
| Context recall | 0.848 | 0.862 | **0.930** |
| Faithfulness | 0.979 | 0.968 | **0.984** |
| Answer relevancy | 0.614 | 0.584 | **0.662** |
| Factual correctness | 0.771 | 0.753 | **0.823** |
| Declined answers (of 45) | 8 | 10 | **5** |
| Out-of-syllabus declined (of 24) | 24 | 24 | 24 |
| Passages retrieved → read | 4 → 2.04 | 4 → 1.87 | 2.84 → 2.44 |
| Retrieval time | 173 ms | 21.4 s | 35 ms |

**R3 is selected**: best on five of six quality rows, fast. R1 and R2 retrieve 4 chunks but the 1,800-character limit lets the model read only about 2 of them, which is why their recall is lower.

**Step 2 — tune the settings of R3** (`eval/rag_settings.py`, results in `eval/results/rag_settings.md`). One setting changes at a time; the rest stay at the current value. Retrieval is scored with **gold evidence**: the judge marked once which textbook lines state each statement of the reference answer (207 of 208 statements are in the notes; it read the question's own topic note plus every section any setting retrieved). Every setting is then scored on the same evidence at no extra cost: *hit rate* (the text read holds a supporting line), *evidence recall*, *precision* (average precision) and *MRR*. Settings that change what the model reads also get faithfulness, factual correctness and declines. A change counts as **clear** only when its 95% paired bootstrap interval leaves out 0. Check: gold evidence recall agrees with the judge's context recall for R1–R3 (mean difference 0.01–0.02, Pearson r 0.98–0.99).

| Setting | Options tested | Evidence | Selection |
|---|---|---|---|
| Chunk size | 300, 600, 1,000, 1,500 characters, whole sections | No size is clearly better: factual correctness 0.79, 0.76, 0.80 and 0.82 vs 0.82 (R3 passes whole sections, so the chunk size only changes matching) | 1,500 (current) |
| Number of sections (k) | 1, 2, 3, 5, 10 | 1 and 2 lose evidence (recall 0.68 and 0.88 vs 0.92) and add declines (16 and 8 vs 5); 5 raises factual correctness 0.82 → 0.86 and cuts declines 5 → 3 with 1.3× the text; 10 adds no clear gain over 5 | **5** (from the best 6 chunks) |
| Context limit | 1,800, 3,600, 7,200 characters, no limit | 1,800 is clearly worse (factual correctness 0.68, 11 declined); 7,200 and no limit change nothing (0.82) | 3,600 (current) |
| Minimum similarity | 0 to 0.85 (13 steps) | Best-match cosine: answerable 0.37–0.77, general out-of-syllabus up to 0.52, near-syllabus up to 0.59, so no threshold separates them; 0.35 is the highest that loses no answerable question; rejecting all out-of-syllabus questions needs 0.60, which rejects 13/45 answerable ones; Tanya Bulan's 0.55 gate turns away 5/45 answerable questions | **0.35** as a safeguard; out-of-syllabus questions are left to the answer model's decline rule (24/24) |
| Query variants | none, 2 rewrites + RRF, 2 rewrites + round-robin | No clear difference (evidence recall 0.90 and 0.91 vs 0.92), and each rewrite costs an extra model call | none (current) |
| Search scope | all notes, subject, topic first | No clear difference (0.92, 0.92, 0.93) | subject (current) for Tanya Bulan; topic first in marking, where the topic is known |
| Matching method | bge-m3 only, BM25 only, hybrid | BM25 only is clearly worse (0.85 vs 0.92); bge-m3 only is no different for Rumi | hybrid (current): the keyword side finds questions typed in Jawi |
| Jawi-script questions | bge-m3 weight 0, 0.25, 0.5, 1 | Jawi questions reach recall 0.79 vs 0.92 in Rumi; the weights differ unclearly (0.82, 0.75, 0.77 vs 0.79) | 0.25 (current) |

**Outcome (Phase 6, 2 November 2026).** The study measured *answering* questions; before using its R3 choices for *marking* they were tested on marking (`eval/r3_marking_dev.py`, results in `eval/results/r3_marking_dev.md`):
- On 171 silver development answers the settings could not be separated (QWK 0.960–0.964; the 0.35 minimum removed nothing).
- On the 50 teacher answers, 5 sections lowered agreement with the teachers significantly: GPT-6 Luna (R3, A2) 0.755 → 0.695 (−0.060, 95% CI −0.152 to −0.002), Claude Haiku 0.729 → 0.636.
- Decision: **marking keeps R3 with 4 chunks, 3 sections and no minimum** (`R3_CHUNKS`, `R3_SECTIONS`, `R3_MIN_SIM` in `kb/rag.py`). The study's choices are used where they were measured: **Tanya Bulan's gate went from 0.55 to 0.35**, with the study's decline rule added to its prompt (Section 3.1.1). The 5-section teacher runs are kept in `eval/results/archive/r3_study_settings_2nov/`.

Re-run: `python eval\rag_eval.py` then `python eval\rag_settings.py` (about $0.40 together from an empty cache, then free from the cache; `--no-llm` re-scores retrieval only).

---

## 6. Assessment Pipeline

When a student submits an answer, these 5 steps run in order (the ReAct loop):

```
Student answer
     │
     ▼
Step 1: get_question         ← load rubric + reference answer from data/questions/
     │
     ▼
Step 2: search_notes         ← hybrid RAG: find 4 most relevant textbook chunks
     │
     ▼
Step 3: score_rubric         ← Two-layer marking (see below)
     │
     ▼
Step 4: get_history          ← load mastery, attempts, repeated mistakes from SQLite
     │
     ▼
Step 5: generate_feedback    ← build feedback from rubric + history + textbook source
     │
     ▼
Save to SQLite + return JSON response
```

Each step records a `{thought, action, observation, time_ms}` trace. The UI shows this trace under "Bagaimana AI berfikir" (How AI thinks).

### 6.1 Two-Layer Rubric Scoring

File: `backend/app/assess/rubric.py`

For each criterion in the rubric:

**Layer A — Rules (always runs first, deterministic)**

| Rule | When | How |
|------|------|-----|
| **Jawi spelling** | Jawi subject + all keywords are Arabic script | Exact character match after Unicode normalisation |
| **Betul/Salah** | Keywords contain "betul" or "salah" | Match the stated choice exactly |
| **Keyword match** | Other criteria | Any keyword appears in the answer text |
| **Number conflict** | Keyword matched but answer contradicts a number | Downgrade to "tidak" |

If Layer A cannot decide: go to **Layer B**.

**Layer B — Semantic similarity (deployed config: `no_llm_sim`)**

The deployed scoring config uses **bge-m3 cosine similarity** only (no LLM calls):
- Embed the answer and each criterion
- Tahap 1: threshold ≥ 0.95 (strict — correct only if very close to the reference)
- Tahap 2/3: threshold ≥ 0.65

Verdict mapping:
| Condition | Verdict | Marks |
|-----------|---------|-------|
| similarity ≥ threshold | `ya` | Full marks |
| 0.5 ≤ similarity < threshold | `separa` | Half marks |
| similarity < 0.5 | `tidak` | 0 |

**Why not the LLM for scoring?**
The 1B Malaysian-Llama model was evaluated and found to say "ya" for 394 of 404 criteria even on wrong answers (AUC 0.55, near-chance). Semantic similarity (AUC 0.82) is much more reliable and 50–100× faster.

**Scoring accuracy (test split, 485 answers):**
| Group | Exact score | QWK |
|-------|-------------|-----|
| Overall | 84.1% | 0.920 |
| Tahap 1 | 93.8% | 0.953 |
| Tahap 2 | 78.5% | 0.866 |
| Tahap 3 | 63.5% | 0.931 |

---

## 7. Adaptive Feedback

File: `backend/app/assess/feedback.py`

After scoring, the system builds feedback from **templates** (not the LLM):

| Feedback section | Source |
|-----------------|--------|
| Stars (1–3) | Score: 100% = 3★, ≥50% = 2★, else 1★ |
| Verdict ("Syabas!" / "Bagus!" / "Cuba lagi") | Fixed template per star count |
| Which criteria were missed | Rubric criteria where `awarded < marks` |
| Correct answer | `reference_answer_rumi` + `reference_answer_jawi` from the question file |
| Textbook source | `source_label()` — e.g. "Buku Teks Tajwid JAIS Tahun 5, ms. 14" |
| Next step suggestion | Based on mastery: < 40% → read note; 40–70% → try similar; > 70% → next level |
| Repeated mistake warning | Criteria missed ≥ 2 times in the same topic (from `mistakes` table) |
| Encouragement line | Fixed template (LLM option off by default) |

---

## 8. AI Chat Assistant

Added in Phase 9.2. Lets students ask free-form questions **before** practising.

File: `backend/app/chat.py`
Frontend: `frontend/src/components/ChatBox.tsx`
API: `POST /api/chat`

**How it works (Extractive Anchoring & ReAct Flow):**

1. **Thought & Input Analysis:** Student types a question (max 500 characters). Query tokens are filtered through domain stop words.
2. **Action (Retrieval):** `search_notes(question, subject, k=4)` queries the hybrid ChromaDB/BM25 store for textbook chunks.
3. **Observation & Syllabus Match Check:** 
   - *Case A (Strong Match):* Top ChromaDB dense cosine similarity $\ge 0.55$. The system executes `_extract_anchor_fact()` to extract the exact core definition/rule sentence directly from the top textbook section.
   - *Case B (Weak Match):* $0.35 \le$ similarity $< 0.55$. The model answers from the passages with the decline rule and no anchor fact; a decline (or no model to check it) is handled as Case C.
   - *Case C (Out-of-Syllabus / Missing in Vector DB):* Dense cosine similarity $< 0.35$ (e.g. general questions or topics outside Year 5 textbooks). Misleading sources are suppressed (`sources = []`), and the assistant strictly starts its response with: `"Data ini tiada dalam pangkalan data saya."` (or `"This data is not in my database."`).
4. **Reasoned Prompt Assembly** (prompt files in `backend/app/prompts/`, one sentence per line, joined into one paragraph by `prompts.render_paragraph`):
   - In-syllabus, `chat.txt`: injects the intent focus (`{focus}`) and the extracted textbook anchor (`{anchor}`) and instructs the model to keep answers short (1–3 sentences), factual, and faithful.
   - Out-of-syllabus, `chat_outside.txt`: instructs the model to lead with the explicit database notice (`{notice}`), followed by a concise 1–2 sentence general knowledge reply.
5. **LLM Generation:** Qwen 2.5 3B generates a concise response (`max_new_tokens = 150`, `temperature = 0.1`, `repetition_penalty = 1.0`, `no_repeat_ngram_size = 0`).
6. **Extractive Safety Guardrail & Output Cleaning:**
   - If in-syllabus generation is degenerate or incomplete, the verified textbook anchor is used as an automatic fallback (*"Berdasarkan buku teks [Topik] (ms. [X]): [anchor]"*).
   - If out-of-syllabus, the exact notice prefix (`"Data ini tiada dalam pangkalan data saya."`) is strictly enforced if omitted by the model.
   - `_clean()` strips prompt echoes, trims repetition loops, and ensures sentence boundaries end cleanly.

**Key Mechanisms in `backend/app/chat.py`:**

- **Subject Normalization:** Automatically maps common student inputs `ibadah` and `fiqah` to the internal database key `fiqh`.
- **8 Pedagogical Intent Detectors:**
  | Intent | Triggers | Target Section in ChromaDB |
  |--------|----------|----------------------------|
  | `fadhilat` | *fadhilat, kelebihan, kebaikan, hikmah, faedah* | `Fadhilat` |
  | `niat` | *niat, lafaz niat, bacaan niat* | `Lafaz Niat` |
  | `waktu` | *waktu, bila, masa* | `Waktu` |
  | `rakaat` | *berapa rakaat, bilangan rakaat, jumlah rakaat* | `Bilangan Rakaat` / `Kaifiat` |
  | `hukum` | *hukum, sah, batal* | `Hukum` |
  | `syarat` | *syarat, syarat sah, syarat wajib* | `Syarat` |
  | `rukun` | *rukun* | `Rukun` |
  | `kaifiat` | *cara, kaifiat, langkah, pelaksanaan* | `Kaifiat` / `Cara Solat` |
  | `pengertian` | *maksud, erti, takrif, apa itu* | `Pengertian` |

- **Intent Reranking:** Promotes chunks matching the intent's target section to Rank #1, preventing definition chunks from obscuring specific rules.
- **Top-2 Focused Context Window:** Injects only the top 2 intent-matching chunks, reducing prompt token noise by 50%.
- **Vector DB Semantic Gate (`GATE = 0.35`, `GATE_TEXTBOOK_ONLY = 0.55` in `chat.py`):** Questions below 0.35 are treated as out-of-database, triggering the `"Data ini tiada dalam pangkalan data saya."` response with `sources = []`; between 0.35 and 0.55 the model decides with the decline rule (the textbook-only fallback keeps 0.55, since it cannot decline).

**Rate limit:** 10 questions per session (resets on login).

---

## 9. Backend API

Framework: **FastAPI 0.115.6**, runs with **Uvicorn 0.34.0**

Base URL: `http://127.0.0.1:8000/api`

| Method | Route | Purpose |
|--------|-------|---------|
| `GET` | `/health` | Model warm-up status, scoring config name |
| `GET` | `/avatars` | List of 10 emoji avatars |
| `POST` | `/auth/login` | Find-or-create student by (name, kelas) |
| `GET` | `/subjects?student_id=` | Catalogue with pupil's mastery per topic |
| `GET` | `/topics/{id}/note` | Full note text + metadata |
| `GET` | `/questions/next` | Adaptive next question (avoids last 5, weakest topic first) |
| `POST` | `/answers` | Run the full assessment pipeline |
| `GET` | `/progress/{student_id}` | XP, streak, badges, mastery, recent attempts |
| `POST` | `/chat` | AI Chat: RAG + LLM answer |
| `POST` | `/admin/login` | Admin sign-in with `KAFA_ADMIN_PASSWORD` → token (12 h) |
| `GET/POST` | `/admin/config` | Live marking system: read / change (Section 17.2) |
| `GET` | `/admin/evaluate/estimate` | Answers and API cost of an evaluation before it runs |
| `POST` | `/admin/evaluate` | Start an evaluation run (background job) |
| `GET` | `/admin/jobs/{id}`, `/admin/jobs/latest?kind=` | Progress of an evaluation or book job |
| `GET/POST` | `/admin/books` | List books / upload a PDF (Section 17.3) |
| `POST` | `/admin/books/{id}/process` · `publish` · `remove` · `restore` | Read with AI · into the syllabus · out · back |
| `GET/POST/DELETE` | `/admin/books/{id}/drafts` | Draft notes and questions: read / save / leave out |
| `GET` | `/admin/books/{id}/pages/{n}` | Page image, to check a draft against the book |
| `GET` | `/eval/summary`, `/settings/qwen` | Evaluation results, Qwen Colab link (admin only) |

Every `/admin/*` route except `/admin/login`, and `/eval/summary` and `/settings/qwen`, needs `Authorization: Bearer <token>`.

**CORS:** `http://localhost:5173` and `http://127.0.0.1:5173` only (dev only).

**API docs:** http://127.0.0.1:8000/docs (Swagger UI auto-generated by FastAPI)

---

## 10. Frontend

Framework: **React 19**, **Vite 6.4**, **TypeScript**, **Tailwind CSS 4**, **Framer Motion 12**

Fonts: **Plus Jakarta Sans** (Rumi) and **Noto Naskh Arabic** (Jawi), bundled with `@fontsource` so the app works offline in class (no Google Fonts request). Icons: **lucide-react**.

Dev server: `http://localhost:5173`

### 10.1 Pages & Routing

| Route | Page | Sidebar | Description |
|-------|------|---------|-------------|
| `/landing` | Landing | No | Public introduction: hero with Bulan, the three subjects, "Bagaimana ia berfungsi?" (Baca nota → Jawab soalan → Dapat bintang) and a call to action |
| `/login` | Login | No | Split screen: welcome panel with Bulan on the left, sign-in card on the right. *Murid* signs in with name, class and avatar. *Guru* and *Admin* tabs are placeholders ("Akan datang") |
| `/` | Home | Yes | Greeting from Bulan, "Tanya Bulan" button, rank card, **Misi hari ini** (daily goal), "Sambung belajar" card and the three subject cards |
| `/subjek/:id` | Subject | Yes | Subject banner (mastery ring, topics, tried, mastered) and a grid of topic cards grouped by Bab. Each card shows a status badge, stars, mastery bar and level; the recommended topic is marked "Mula di sini!" |
| `/topik/:id` | Topic | Yes | Breadcrumb, topic banner, three level steps (🌱 Tahap 1, 🌿 Tahap 2, 🌳 Tahap 3) with lock hints, and the collapsible bilingual note |
| `/latihan/:topicId/:level` | Practice | Icons only | Focus mode. Round progress (stars per question), question card (listen, show in the other script, hint), answer area (Betul/Salah buttons, word chips, textarea, on-screen Jawi keyboard), result card and round summary |
| `/kemajuan` | Progress | Yes | Profile and rank, XP / streak / topics tried, badge shelf, mastery per subject and topic, recent attempts |

### 10.2 App Shell & Navigation

`Layout.tsx` wraps every signed-in page.

**Sidebar (screens ≥ 768 px).** Dark green, fixed on the start side (left in Rumi, right in Jawi). Top to bottom:
1. KafAI logo, UPKK badge and the tagline "Belajar daripada setiap jawapan"
2. Main menu: Utama, Kemajuan Saya
3. **Subjek**: Ibadah, Jawi, Tajwid with each subject's mastery %. The subject stays highlighted on its topic and practice pages
4. Tanya Bulan (opens the chat panel); Admin in researcher mode
5. Settings: Rumi/Jawi, light/dark, sound, server status; Keluar

**Top bar (screens ≥ 768 px, not in practice).** Topic search (Rumi or Jawi titles, Enter opens the first match), 💎 XP, 🔥 streak, and the pupil's avatar, name and class (links to Kemajuan Saya).

| Width | Sidebar |
|-------|---------|
| ≥ 1280 px | Full (256 px). The panel button collapses it to icons; the choice is saved (`kafa.sidebar` in localStorage) |
| 768–1279 px | Icons only (84 px), with tooltips, so tablets and small laptops keep room for the cards |
| Practice page | Always icons only and no top bar, so the question has the space (focus mode) |

**Phones (< 768 px).** Top bar (☰ menu, logo, XP, avatar), a slide-in drawer with the same sidebar content, and a bottom tab bar: Utama, Kemajuan, Tanya Bulan, Menu.

**Chat panel.** Opened from the sidebar, the tab bar or the home page through `ChatContext`; it docks in the bottom corner (bottom sheet on phones). There is no floating button, so nothing covers the "Semak Jawapan" button.

### 10.3 Key Frontend Components

| Component | Purpose |
|-----------|---------|
| `Layout.tsx` | App shell: sidebar (full / icons), mobile top bar, drawer, bottom tab bar, skip link |
| `ui.tsx` | Shared pieces: `Stars`, `MasteryBar`, `ProgressRing`, `Card`, `PageNav` (back button + breadcrumb), `Spinner`, `ErrorBox` |
| `Mascot.tsx` | Animated moon mascot "Bulan" with 5 moods (*happy, celebrate, thinking, encourage, wave*) and a speech bubble |
| `ChatBox.tsx` | "Tanya Bulan" chat panel with textbook source chips and the 10-question session limit |
| `RankCard.tsx` | Rank and XP bar to the next rank (full, large and compact sidebar versions) |
| `JawiKeyboard.tsx` | On-screen Jawi keyboard (40 letters, the 6 Jawi-only letters tinted, comma, question mark, space, backspace) |
| `ResultCard.tsx` | Feedback after an answer: stars, verdict, marks, XP, what to improve, correct answer with textbook page, next step, expandable 5-step AI reasoning trace |
| `CelebrationModal.tsx` | "Hebat!" dialog for a new rank, unlocked level or new badge, with confetti |
| `RoundSummary.tsx` | End-of-round card: stars per question, totals, play again / next level / other topic |
| `NoteView.tsx` | Markdown note renderer; each Rumi and Jawi line gets its own direction and font |
| `ScriptToggle.tsx` / `ThemeToggle.tsx` / `SoundToggle.tsx` | Rumi ⇄ Jawi, light ⇄ dark and sound on/off buttons |
| `ApiStatus.tsx` | Backend / AI warm-up status (dot + text) |
| `theme/ThemeContext.tsx` | Light/dark theme; sets `<html data-theme>`, saved in `kafa.theme` |
| `chat/ChatContext.tsx` | Open/closed state of the chat panel, shared by the sidebar, tabs and pages |
| `sound/SoundContext.tsx` | Web Audio tones (*tap, correct, partial, wrong, levelup, finish*) |
| `session/ProgressContext.tsx` | The pupil's XP, streak, badges and mastery, shared by the sidebar and pages |
| `lib/daily.ts` | Counts today's answers for "Misi hari ini" (goal: 5 a day) |

### 10.4 Script Toggle (Jawi ⇄ Rumi)

The entire UI switches between Bahasa Melayu in:
- **Rumi** (Latin script, LTR): default
- **Jawi** (Arabic script, RTL): `html dir="rtl" lang="ms-Arab"`

Every UI string has both versions in `frontend/src/i18n/strings.ts`. Question text, notes and answers detect their own direction with `textDir()` and use the Naskh font. Layout uses logical CSS (start/end instead of left/right), so in Jawi mode the sidebar, breadcrumbs, arrows and progress bars all mirror to the right-to-left reading direction.

### 10.5 Themes (Light ⇄ Dark)

Light is the default; the ☀️/🌙 button switches to dark. The first visit follows the device setting, and the choice is saved. A small script in `index.html` applies the saved theme before the page paints, so there is no flash. See Section 16 for the colour tokens.

---

## 11. Configuration

All settings are in `backend/app/config.py`. Override with environment variables prefixed `KAFA_`:

| Setting | Default | Description |
|---------|---------|-------------|
| `KAFA_LLM_MODEL_ID` | `mesolitica/Malaysian-Llama-3.2-1B-Instruct` | LLM model |
| `KAFA_EMBED_MODEL_ID` | `BAAI/bge-m3` | Embedding model |
| `KAFA_DEVICE` | `auto` | `auto` / `cuda` / `cpu` |
| `KAFA_LLM_DTYPE` | `float16` | Precision |
| `KAFA_CHROMA_DIR` | `storage/chroma` | ChromaDB directory |
| `KAFA_SQLITE_PATH` | `storage/kafa.db` | SQLite file |
| `KAFA_KNOWLEDGE_DIR` | `data/knowledge` | Topic notes directory |
| `KAFA_QUESTIONS_DIR` | `data/questions` | Question bank directory |
| `KAFA_LLM_ENCOURAGEMENT` | `false` | Enable LLM-written encouragement |
| `KAFA_PRELOAD_MODELS` | `true` | Load models at startup |
| `KAFA_ADMIN_PASSWORD` | *(empty = admin off)* | Password of the admin pages (Section 17) |
| `KAFA_BOOKS_DIR` | `storage/books` | Uploaded books, page images, drafts, removed books |
| `KAFA_SCORER` | `b2` | Live marking system until the admin changes it on the System setup tab |
| `KAFA_RESEARCHER_MODE` | `true` | Show the 🛡️ Admin link in the pupils' sidebar |

---

## 12. File Structure Summary

```
FypNabil/
├── data/
│   ├── knowledge/<subject>/<topic>.md    ← 48 topic notes (Rumi + Jawi)
│   ├── questions/<subject>/<topic>.json  ← 382 questions + rubrics
│   ├── silver/                           ← synthetic training labels
│   └── splits/train.json, test.json      ← 80/20 split
│
├── models/                               ← downloaded HuggingFace models (7.06 GB, git-ignored)
│   ├── mesolitica/Malaysian-Llama-3.2-1B-Instruct/
│   └── BAAI/bge-m3/
│
├── storage/                              ← runtime data (git-ignored)
│   ├── chroma/                           ← ChromaDB vector store (7.9 MB)
│   │   ├── kafa_notes/                   ← 339 textbook chunks
│   │   └── kafa_refs/                    ← 382 reference answers
│   ├── kafa.db                           ← SQLite student database (108 KB)
│   └── kb_manifest.json                  ← ingest metadata
│
├── backend/
│   ├── app/
│   │   ├── main.py                       ← FastAPI routes
│   │   ├── config.py                     ← all settings
│   │   ├── llm.py                        ← LLM loader + generate()
│   │   ├── embeddings.py                 ← bge-m3 loader + embed()
│   │   ├── chat.py                       ← AI chat helper
│   │   ├── catalog.py                    ← subject/topic catalogue
│   │   ├── notes.py                      ← note metadata loader
│   │   ├── questions.py                  ← question bank loader
│   │   ├── schemas.py                    ← Pydantic request/response models
│   │   ├── kb/
│   │   │   ├── chunking.py               ← note → chunks
│   │   │   ├── ingest.py                 ← build ChromaDB
│   │   │   ├── retriever.py              ← hybrid search (dense + BM25)
│   │   │   ├── lexical.py                ← BM25 index
│   │   │   └── store.py                  ← ChromaDB connection
│   │   ├── assess/
│   │   │   ├── pipeline.py               ← top-level assess() + next_question()
│   │   │   ├── react.py                  ← 5-step ReAct loop
│   │   │   ├── rubric.py                 ← two-layer scoring
│   │   │   ├── decision.py               ← scoring config rules
│   │   │   ├── matching.py               ← keyword, Jawi normalisation
│   │   │   ├── jawi_text.py              ← Arabic/Jawi text utilities
│   │   │   ├── judge.py                  ← LLM judge (disabled for scoring)
│   │   │   └── feedback.py               ← adaptive feedback templates
│   │   ├── memory/
│   │   │   └── db.py                     ← SQLite CRUD + mastery/XP logic
│   │   └── prompts/
│   │       ├── chat.txt                  ← Tanya Bulan prompt: answer from the textbook passages
│   │       ├── chat_outside.txt          ← Tanya Bulan prompt: out of syllabus, start with the notice
│   │       ├── judge_criterion.txt       ← local judge prompt (one criterion, JSON reply)
│   │       ├── judge_prob.txt            ← local judge prompt (YA / SEPARA / TIDAK, few-shot)
│   │       ├── judge_retry.txt           ← local judge prompt (short retry)
│   │       ├── judge_examples.json       ← few-shot examples for judge_prob
│   │       └── encourage.txt             ← LLM encouragement prompt
│   └── tests/                            ← 80 pytest tests
│
├── frontend/
│   └── src/
│       ├── index.css                     ← design tokens (light + dark) and button/card styles
│       ├── pages/                        ← Landing, Login, Home, Subject, Topic, Practice, Progress
│       ├── components/                   ← Layout (sidebar), Mascot, ChatBox, JawiKeyboard, ResultCard, …
│       ├── api/client.ts                 ← fetch wrappers
│       ├── api/types.ts                  ← TypeScript type definitions
│       ├── i18n/strings.ts               ← all UI strings (Rumi + Jawi)
│       ├── theme/ThemeContext.tsx        ← light / dark theme
│       ├── chat/ChatContext.tsx          ← chat panel open/closed
│       ├── session/                      ← StudentContext, ProgressContext
│       ├── sound/SoundContext.tsx        ← Web Audio tones
│       ├── hooks/                        ← useAsync, useSpeech, useMediaQuery
│       └── lib/rank.ts, quick.ts, daily.ts ← ranks, quick-answer logic, daily mission
│
├── eval/                                 ← evaluation scripts and results
├── scripts/                              ← e2e test, figure rendering, teacher tools
└── docs/                                 ← thesis chapters, SUS form, figures
```

---

## 13. How Everything Connects — End-to-End Flow

```
[Student types answer]
        │
        ▼
 React frontend (port 5173)
        │  POST /api/answers
        │  {student_id, question_id, answer}
        ▼
 FastAPI (port 8000) — pipeline.assess()
        │
        ├─► load_questions()  ────────────► data/questions/*.json (in memory, cached)
        │
        ├─► search_notes()    ────────────► bge-m3 (GPU) → ChromaDB query
        │                                   kafa_notes collection
        │                                   storage/chroma/
        │
        ├─► score_answer()    ────────────► bge-m3 embed answer + criteria
        │   Layer A: rules                  keyword match, Jawi spelling check
        │   Layer B: similarity             cosine(answer_vec, criterion_vec) ≥ 0.65
        │                                   reference_similarity() → kafa_refs
        │
        ├─► get_history()     ────────────► SQLite: storage/kafa.db
        │                                   topic_mastery, mistakes tables
        │
        ├─► build_feedback()  ────────────► template strings + source_label()
        │                                   notes metadata (book_pages)
        │
        └─► record_attempt()  ────────────► SQLite: save attempt, update mastery,
                                            unlock levels, award XP, grant badges
        │
        ▼
 JSON response → React frontend
 {stars, verdict, correct_answer, source, suggestion, trace[5 steps], new_badges, xp_gained}
        │
        ▼
 UI: stars animation + celebration modal + XP chip + "Bagaimana AI berfikir"
```

---

## 14. Performance Summary

| Metric | Value |
|--------|-------|
| Scoring accuracy (overall exact) | 84.1% |
| Quadratic Weighted Kappa | 0.920 |
| Retrieval Recall@4 (Rumi) | 100% |
| Retrieval Recall@4 (Jawi) | 93.4% |
| Consistency (same answer × 3) | 100% |
| Median latency — Tahap 1 | 56 ms |
| Median latency — Tahap 2 | 70 ms |
| Median latency — Tahap 3 | 154 ms |
| Chat response time (Qwen 3B) | ~2.5–5.0 s (~11.1 tokens/s) |
| Active LLM model | `unsloth/Qwen2.5-3B-Instruct-bnb-4bit` (4-bit NF4) |
| Success rate (180 test runs) | 100% |
| SQLite DB size | 108 KB |
| ChromaDB size | 7.9 MB (339 note chunks + 382 refs) |
| Models total | ~4.3 GB (bge-m3 + Qwen 3B 4-bit) |

---

## 15. The 3-Step AI & Knowledge Base Optimization Plan

To resolve issues with inaccurate, circular, or hallucinated answers in the AI Chat assistant, a comprehensive 3-step optimization was implemented and verified:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                      3-Step AI & Knowledge Base Optimization                           │
├─────────────────────────┬─────────────────────────────┬────────────────────────────────┤
│ Step 1: Routing & Anchor│ Step 2: KB Data Cleaning    │ Step 3: 3B Model & Guardrails  │
│ • 8 Pedagogical intents │ • Cleaned OCR artifacts     │ • Qwen 2.5 3B (4-bit NF4)      │
│ • Section-target rerank │   ([TIDAK JELAS], [semak])  │ • VRAM: ~2.05 GB (Safe 6GB GPU)│
│ • Extractive anchoring  │ • 0 errors in validate_data │ • "Data tiada dlm pangkalan..."│
│ • Top-2 chunk pruning   │ • Rebuilt ChromaDB (339 chk)│ • sources=[] on out-of-db      │
└─────────────────────────┴─────────────────────────────┴────────────────────────────────┘
```

### 15.1 Step 1: Intent-Aware Section Routing & Extractive Anchoring
- **The Problem:** The small LLM previously copied generic definitions (*"Solat tahajud ialah..."*) regardless of whether the pupil asked about *fadhilat*, *bilangan rakaat*, or *lafaz niat*.
- **Implementation in `backend/app/chat.py`:**
  1. `_detect_intent(query)`: Detects 8 core question types (*fadhilat, niat, waktu, rakaat, hukum, syarat, rukun, kaifiat, pengertian*).
  2. `_rerank_hits_by_intent(hits, intent_spec)`: Dynamically promotes the textbook section matching the intent to Rank #1.
  3. Context pruning: Reduces context to the top 2 intent-matching chunks, cutting prompt noise by 50%.
  4. `_extract_anchor_fact()`: Extracts the verified factual bullet points or rule sentences directly from the top textbook section to serve as the prompt anchor and automatic fallback.

### 15.2 Step 2: Knowledge Base Data Cleaning & ChromaDB Rebuilding
- **The Problem:** OCR transcription tags (`[TIDAK JELAS]` and `[semak]`) existed in 7 knowledge files, causing incomplete and blurry text in retrieved chunks.
- **Action Taken:**
  1. Corrected all 7 files in `data/knowledge/` against official JAIS Year 5 textbooks:
     - `fiqh_b1_solat_tahajud.md`: Corrected fadhilat and kaifiat.
     - `fiqh_b1_solat_tarawih.md`: Corrected bilangan rakaat and lafaz niat.
     - `fiqh_b1_solat_witir.md`: Corrected kaifiat and lafaz niat.
     - `fiqh_b2_fadhilat_puasa.md`: Corrected fadhilat and hikmah puasa.
     - `fiqh_b2_syarat_wajib_sah_puasa.md`: Corrected syarat wajib and syarat sah.
     - `jawi_b2_imbuhan_i_hamzah_ya.md`: Corrected Jawi spelling rules for `-i`.
     - `jawi_b4_akronim_inggeris.md`: Corrected English acronym rules in Jawi.
  2. Verified 100% clean data with `scripts/validate_data.py` (0 errors, 0 warnings).
  3. Re-ingested ChromaDB (`python -m backend.app.kb.ingest`): 339 note chunks and 382 reference questions vectorised cleanly.

### 15.3 Step 3: Model Upgrade to Qwen 2.5 3B (4-Bit) & Out-of-Database Guardrails
- **The Problem:** A 1B model has physical reasoning limits and struggles with complex multi-turn synthetic dialogue and negative constraints. Furthermore, when questions outside the syllabus were asked, standard RAG retrieved arbitrary textbook chunks and hallucinated connections (e.g. chocolate cake recipes associated with Quranic recitation).
- **Implementation:**
  1. **Model Upgrade:** Upgraded from `mesolitica/Malaysian-Llama-3.2-1B-Instruct` to **`unsloth/Qwen2.5-3B-Instruct-bnb-4bit`** via native Windows `bitsandbytes` (0.50.2).
  2. **VRAM Optimization:** Model consumes **~2.05 GB VRAM** in NormalFloat4 (NF4), maintaining total system VRAM under **3.86 GB** on the user's RTX 3050 Laptop GPU (6 GB capacity), with generation speeds of ~11.1 tokens/sec.
  3. **Vector Database Confidence Gate (`top_dense_score >= 0.55`; lowered to 0.35 with a decline rule on 2 Nov 2026, see Section 3.1.1):**
     - Questions scoring $\ge 0.55$ dense cosine similarity are answered with extractive textbook anchoring and textbook sources.
     - Questions scoring $< 0.55$ (not in database) strictly suppress textbook sources (`sources = []`) and lead with:
       > **"Data ini tiada dalam pangkalan data saya."** *(or "This data is not in my database." for English queries)*
       followed by a concise, polite general knowledge reply (1–2 sentences).
  4. **Subject Normalization:** Input aliases `ibadah` and `fiqah` automatically route to `fiqh` across ChromaDB dense vector searches and BM25 lexical indexing.

---

## 16. UI/UX Design System: KafAI UPKK (Light + Dark)

The interface was first redesigned on 25 October 2026 for its real users: KAFA Year 5 pupils aged 10–11, on shared school laptops, tablets or projectors (light by default, optional dark mode, sidebar navigation). On **2 November 2026** it was redesigned again as **KafAI UPKK** ("Belajar daripada setiap jawapan": learn from every answer), following the UI/UX brief and mockups in `KafAI_UIUX_Handoff/` (screens 1–8; the teacher dashboard, screen 9, is on hold). The aim was a calm, trustworthy learning product rather than a game, while keeping what already worked: Rumi/Jawi, light/dark, Bulan, XP and badges. Only the frontend changed, apart from `/api/progress` now returning the last 30 attempts (was 10) for the weekly chart and the history list.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                           UI/UX Design System: KafAI UPKK                              │
├─────────────────────────┬─────────────────────────────┬────────────────────────────────┤
│ 1. Brand & Tokens       │ 2. App shell                │ 3. Learn & Practise            │
│ • Deep emerald, cream,  │ • Dark green sidebar        │ • Dashboard: continue, picks,  │
│   gold; light + dark    │ • Top bar: topic search,    │   week chart, weak topics      │
│ • Plus Jakarta Sans +   │   XP, streak, profile       │ • Subject: progress, topics    │
│   Noto Naskh (Jawi)     │ • Phone: drawer + tab bar   │ • Lesson: note, levels         │
├─────────────────────────┼─────────────────────────────┼────────────────────────────────┤
│ 4. Feedback             │ 5. Motivation               │ 6. Bilingual & Accessibility   │
│ • Result → explanation  │ • XP, 6 ranks, streak       │ • Rumi LTR / Jawi RTL mirror   │
│   → action              │ • 5 badges, Misi hari ini   │ • Contrast ≥ 4.5:1 both themes │
│ • Honest checking bar   │ • Bulan mascot, confetti    │ • Touch targets ≥ 44 px        │
│ • AI trace: researchers │ • Sounds (can be muted)     │ • Keyboard, screen reader      │
└─────────────────────────┴─────────────────────────────┴────────────────────────────────┘
```

### 16.1 Design Principles for 10–11 Year Olds

| Principle | How it is applied |
|-----------|-------------------|
| Easy to read | Body text 16 px (18 px in Jawi), questions 24–26 px bold; Plus Jakarta Sans for Rumi, Noto Naskh Arabic for Jawi; warm light background by default |
| Easy to tap | Buttons and menu items at least 44 px high; main buttons 48–56 px |
| Learn from every answer | The result page follows RESULT → EXPLANATION → ACTION (Section 16.6) |
| No technical words for pupils | "Menyemak nota KAFA", "Berdasarkan nota KAFA kamu"; the ReAct trace is shown only in researcher mode |
| Meaning never by colour alone | Status chips have an icon and a word (Baru, Sedang belajar, Dikuasai); scores always show the number |
| One clear next step | One gold call to action per screen: "Sambung", "Mula Latihan"; "Semak Jawapan" is full width |
| Honest loading | The checking screen names the steps (read the answer, check the KAFA note, prepare feedback) with an indeterminate bar: no fake percentage |
| Low distraction while answering | Practice is a focus mode: icon rail, no top bar, one column |
| Encouraging tone | Bulan speaks in short Malay sentences; one star is always given for trying; mistakes are "Apa yang perlu dibaiki" |
| Works in class | Fonts bundled (offline); checked at 360, 390, 768, 820, 1024, 1280 and 1440 px, in Rumi and Jawi, with no sideways scrolling |

### 16.2 Colour Tokens

All colours are CSS variables in `frontend/src/index.css`, switched by `<html data-theme="light|dark">` and used through Tailwind names (`bg-surface`, `text-ink-2`, `border-line`, `bg-primary` …). No page hard-codes a colour.

| Token | Light | Dark | Used for |
|-------|-------|------|----------|
| `bg` | `#fbf6ec` (warm cream) | `#0f1412` | Page background |
| `surface` | `#ffffff` | `#171d1a` | Cards, top bar, inputs |
| `surface-2` / `surface-3` | `#f8f2e6` / `#eee5d3` | `#1d2420` / `#27302b` | Inner panels, progress-bar tracks |
| `line` / `line-strong` | `#ece2cf` / `#d8cab0` | `#29322d` / `#3a453f` | Borders |
| `ink` / `ink-2` / `ink-3` | `#17241d` / `#435047` / `#5d6a62` | `#eef3f0` / `#c3ccc7` / `#99a49e` | Headings / body / captions |
| `primary` | `#0b6b45` (deep emerald) | `#22b07a` | Main buttons, links, focus ring |
| `on-primary` | `#ffffff` | `#04241a` | Text on primary buttons |
| `brand` / `brand-2` | `#0a4a32` / `#0f6040` | `#0b2e22` / `#0f3d2c` | Sidebar and the green hero cards (continue, score, progress) |
| `nav-active` | `#fbf3df` with `#0a4a32` text | same | The active sidebar item |
| `gold` / `on-gold` | `#f3b641` / `#3a2905` | same | The one warm call to action, progress fill on green cards |
| `accent` | `#f59e0b` (amber) | `#fbbf24` | Streak, daily mission, partial mistakes |
| `danger` / `info` | red / sky | red / sky | Wrong criteria, errors / notes, read-only topics |

Contrast was checked for every text/background pair: `ink`, `ink-2` and `ink-3` on `bg` and `surface` are at least 4.5:1 in both themes; white on `primary` is about 6.5:1, white on `brand` about 10:1 and `on-gold` on `gold` about 8:1. On the green sidebar and cards the focus ring turns gold so it stays visible.

**Subject colours** (tokens `fiqh`, `jawi`, `tajwid`, each with `-soft` and `-ink` versions) are used for the subject tiles, topic number badges and mastery bars, as in the mockups:

| Subject | Colour | Tile |
|---------|--------|------|
| Ibadah (Fiqh) | Green | 🕌 |
| Jawi | Amber | the word جاوي |
| Tajwid | Violet | 📖 |

### 16.3 Typography & Components

| Element | Style |
|---------|-------|
| Rumi font | `Plus Jakarta Sans` (variable, 200–800): modern rounded sans, clear for children and professional for adults |
| Jawi font | `Noto Naskh Arabic`, line height 1.9–2: the textbook style |
| Icons | `lucide-react` line icons for controls and section titles; emoji only for illustrations (subject tiles, badges, avatars) |
| `.btn-primary` / `.btn-gold` / `.btn-secondary` | 48 px high, 12 px corners, flat with a soft shadow; gold for the single main call to action; grey "not yet" look when disabled |
| `.btn-choice` | Betul / Salah and word-chip buttons; pressed state is emerald |
| `.card` / `.card-brand` | 16 px corners and a soft shadow / deep green gradient hero card with a faint mosque skyline |
| `.field` | Text inputs with an emerald focus ring |
| `PageNav` | "← Kembali" pill plus breadcrumb with a home icon; the current page sits in a gold pill |
| Shared pieces | `Brand` (logo: an open book under a gold dome + "KafAI" wordmark + UPKK badge), `SubjectIcon`, `ScorePill` (green ≥ 80%, amber ≥ 50%, red below), `MasteryBar`, `TrendChart` (one-line SVG chart with hover values and a hidden table for screen readers), `MosqueScene` (decorative skyline) |

Animations: `animate-floaty` (mascot), `animate-pop` (XP changes), `animate-indeterminate` (checking bar), confetti on 3 stars and celebrations. All stop when the device asks for reduced motion.

### 16.4 Navigation

- **Desktop:** a dark green sidebar (Utama, Kemajuan Saya, the three subjects with their mastery %, Tanya Bulan, Admin in researcher mode; Rumi/Jawi, theme, sound and server status at the bottom) and a top bar with **topic search** (Rumi or Jawi titles), XP, streak and the pupil's avatar and name.
- **Tablet:** the sidebar becomes an icon rail. **Phone:** top bar, slide-in drawer and a bottom tab bar (Utama, Kemajuan, Tanya Bulan, Menu).
- **Where am I?** The current subject stays highlighted on its topic and practice pages, and every inner page has a breadcrumb.
- **Focus mode** in practice: icon rail and no top bar.

### 16.5 Pages

| Page | Content (mockup screen) |
|------|-------------------------|
| Landing `/landing` | Hero "Belajar daripada setiap jawapan." with the photo of KAFA children, problem and solution, 4 steps (Belajar → Berlatih → Faham → Maju), benefits for pupils and teachers (teacher dashboard marked "Akan datang"), subjects, UPKK alignment, call to action (1) |
| Login `/login` | Green brand panel with Bulan; *Murid* (name, class, one of 10 animal avatars), *Guru* ("Akan datang") and *Admin* (password) tabs |
| Dashboard `/` | Greeting and Misi hari ini; "Sambung belajar" card; "Disyorkan untuk kamu"; subject cards; recent activity; weekly score chart; topics to improve (2) |
| Subject `/subjek/:id` | Subject progress (mastered / learning / not started), insight (strongest, needs work, tried), topic cards per Bab with Mula / Sambung / Ulang kaji, then recommended, weak and mastered lists (3) |
| Lesson `/topik/:id` | Lesson header, the textbook note (open), source card, topic progress ring, level list, gold "Mula Latihan", next topic (4) |
| Practice `/latihan/...` | Question (5), checking screen (6) and result (7): Section 16.6 |
| Progress `/kemajuan` | Tabs *Gambaran kemajuan* (overall progress, recommended topic, XP / streak / topics tried, subject bars, weekly chart, weak topics, rank and badges) and *Sejarah pembelajaran* (history table) (8) |
| Admin `/admin/...` | The same shell in English: Evaluation & system setup, Books & syllabus |

"Dikuasai" (mastered) means mastery of at least 70%, the same bar that unlocks the next Tahap (`lib/insights.ts`). Recommendations list the weakest tried topics first, then new topics in textbook order.

### 16.6 Practice & Feedback (`/latihan`)

1. **Header:** chips for KAFA, the subject and the topic with its Tahap, and "Soalan 2/5" with one dot per question: green (3 stars), gold (2), ringed (1), pulsing gold (current), grey (to come).
2. **Question card:** large bold question, marks chip, *Dengar soalan* (text-to-speech), show the question in the other script, and a **Petunjuk** button that reveals the hint (how many points to mention, or "tulis dalam huruf Jawi").
3. **Answer area:** Betul/Salah buttons, word chips for fill-in-the-blank (lettered (a), (b)), multiple choice A–D, a textarea with a character count, and the on-screen **Jawi keyboard** (opens automatically for Jawi questions; the six Jawi-only letters چ ڠ ڤ ݢ ۏ ڽ are tinted). Enter checks a short answer; "Semak Jawapan" is full width.
4. **Checking screen:** Bulan, "Menyemak jawapan kamu…", the three steps (membaca jawapan, menyemak nota KAFA, menyediakan maklum balas) and an indeterminate bar, since the real progress is unknown; kept for at least 0.65 s so it does not flicker.
5. **Result (`ResultCard.tsx`)**, in the order of the brief:
   - *Result:* "Cemerlang / Usaha yang baik / Jangan putus asa, ⟨name⟩!" with the encouragement, then a green score card (marks, verdict pill, stars, +XP).
   - *Explanation:* *Apa yang kamu buat dengan baik* (criteria met), *Apa yang perlu dibaiki* (missed / partial criteria, repeated-mistake warning), *Kenapa?* (the LLM marker's own feedback, when the live scorer is an LLM), *Jawapan betul* (Rumi + Jawi), *Berdasarkan nota KAFA kamu* (topic and textbook page, Baca Nota) and *Langkah seterusnya*. On phones the less urgent sections start folded.
   - *Action:* Ulang kaji nota / Ke tahap seterusnya / Soalan seterusnya.
   - **"Bagaimana AI berfikir"** (the 5-step ReAct trace) appears only in researcher mode.
6. **Round summary:** stars per question, total stars, perfect answers, XP, and Main lagi / next level / other topic.

### 16.7 Motivation (Gamification)

| Feature | Rule |
|---------|------|
| Stars | 3 = 100%, 2 = at least 50%, 1 for trying |
| XP | 10 × stars + 2 per answer |
| Ranks | 6 ranks by XP: 🌱 Pelajar Baharu (0), 📚 Pelajar Rajin (50), ⭐ Bintang Kecil (150), 🌟 Bintang KAFA (300), 🎓 Pakar Muda (500), 🏆 Juara UPKK (800) |
| Streak | 🔥 days in a row with at least one answer |
| Badges | 5 badges (Section 4.2), shown on the progress page shelf |
| **Misi hari ini** | Daily goal of 5 answers, shown as 5 bars under the greeting on the dashboard (counted from today's attempts in local time, `lib/daily.ts`) |
| Celebrations | "Hebat!" dialog with confetti for a new rank, unlocked level or new badge |
| Sound | Short Web Audio tones for tap / correct / partial / wrong / level up / finish; mute button in settings |

### 16.8 Accessibility & Bilingual Support

- **Rumi ⇄ Jawi:** every UI string exists in both scripts; Jawi mode sets `dir="rtl"` and the layout mirrors (logical CSS), including the sidebar side, breadcrumb arrows and progress-bar direction.
- **Contrast:** at least 4.5:1 for text in both themes (Section 16.2); white text only on the dark part of coloured banners and in large bold sizes.
- **Keyboard:** skip link to the content, visible 3 px focus ring, Enter / Ctrl+Enter to check answers, Escape closes the chat panel, menu drawer and dialogs; Tab stays inside dialogs.
- **Screen readers:** landmarks (sidebar menu, breadcrumb, main), `aria-current` on the active page, `aria-pressed` on toggles, `aria-live` for results and chat, progress bars with values, avatar options and icon-only rail items with text names.
- **Reduced motion:** all CSS and Framer Motion animations stop when the device asks for it.

### 16.9 Verification

- TypeScript (`tsc -b`), ESLint and the production build (`vite build`) pass.
- `scripts/e2e_ui.py` (real backend and models) passes with no console or server errors: login → subject → topic note → practice → celebration → result → AI trace → round summary → Jawi keyboard → Betul/Salah → word chips → progress → Jawi mode → mobile.
- Every page was checked by screenshot in light and dark, at 1280 px (desktop) and 390 px (phone), and in Jawi (RTL) mode.

---

## 17. Admin Part (Evaluation, System Setup, Books & Syllabus)

For teachers and the researcher, in English like the evaluation page; the pupil pages stay in Malay (Rumi / Jawi).

### 17.1 Sign-in

- Login page → **Admin** tab → admin password (`KAFA_ADMIN_PASSWORD` in `.env`, git-ignored). The pupils' sidebar shows a 🛡️ Admin link in researcher mode.
- The server returns a token valid for 12 hours, signed with HMAC (`backend/app/admin_auth.py`). The key mixes a random secret (`storage/admin_secret`) with the password, so **changing the password signs every admin out**. A wrong password waits 1 s (slows guessing).
- Routes `/admin/penilaian` (Evaluation & system setup) and `/admin/buku` (Books & syllabus) have their own layout (`AdminLayout.tsx`) and load only when an admin opens them.

### 17.2 System setup (Evaluation page, first tab)

| Part | What it does |
|------|--------------|
| Marking system pupils get now | The live configuration, e.g. `b2` or `proposed:luna:R3:A2:on` (`backend/app/live_config.py`, saved in `storage/runtime_settings.json`; without one, `KAFA_SCORER`) |
| Choose a configuration | System (B1–B4, Proposed), LLM (Haiku 5.5, GPT-6 Luna, Llama 3.1 8B, Qwen3-4B with its availability), RAG type (R1–R3), ReAct type (A1–A3), memory on/off; options that do not apply are greyed out |
| Results of this configuration | QWK, exact, within 1 mark, MAE, faithfulness (E2), success, API spend, time per answer for each data set it was evaluated on, plus its RAG type's RAG-evaluation numbers |
| Run evaluation | The same run as `eval/experiments.py`, as a background job with a progress bar (`admin_eval.py`, `jobs.py`); the cost is estimated first (free when the answers are cached); results appear on the page when it ends (`eval/results/experiments/admin__*.json`) |
| Use for pupils | Makes the configuration live from the next answer (with a confirmation); an API failure still falls back to B2 |
| All evaluated configurations | Every result ranked by QWK, with *Select* to load it into the chooser |

### 17.3 Books & syllabus (`backend/app/library.py`)

A book's files in `data/` **are** the syllabus: textbook notes in `data/knowledge/` (searched by RAG, read by pupils) with their practice questions, and exercise-book questions in `data/questions/` linked to topics. The three Year 5 textbooks are registered as **built-in** books.

Adding a book is a **document ingestion pipeline**:

| Step | Term | In this system |
|------|------|----------------|
| 1 | Digitisation | Upload a PDF: a scan or phone photos of the pages (image-only PDF) |
| 2 | Rendering | Every page → JPEG, long edge 1,568 px (PyMuPDF) |
| 3 | OCR by a vision LLM (*vision-LLM transcription*) | Claude Haiku 5.5 reads each page image: Jawi as printed + Rumi, Arabic exactly with harakat, `[TIDAK JELAS]` instead of guessing (rules of `data/knowledge/_format.md`) |
| 4 | Segmentation | One call over all pages decides where topics start (a page alone cannot tell a topic title from a section heading) and carries the bab forward |
| 5 | Structuring + metadata | Draft notes with front-matter (`book_id`, pages, `verified: false`); a textbook topic also gets 6 practice questions with rubrics (GPT-6 Luna). An exercise-book question is linked to its topic by hybrid retrieval and gets a reference answer and rubric from that topic's note; questions without an answer are left out and listed |
| 6 | Human-in-the-loop verification | The teacher compares each draft with its page image side by side, edits it, marks notes *checked by a teacher*; errors (front-matter, rubric marks, unknown topic) block publishing; warnings point to `[TIDAK JELAS]` and Jawi words with Latin letters |
| 7 | Publish = chunking + embedding + indexing | Files copied into `data/`; only the changed topics and questions are re-indexed (`kb/update.py`), so search never stops |

**Remove** moves a book's files to `storage/books/<id>/removed/` and takes its chunks out of the index (pupils' progress stays in SQLite); **Restore** brings them back. Measured on copies of the data: removing the Tajwid textbook took 0.7 s (339 → 172 chunks), restoring it 9.7 s. Reading two real textbook pages cost $0.005 and gave one topic note and 6 questions; about **$0.001 per page** plus the questions.

After a syllabus change, re-run the RAG and marking evaluations: the System setup tab shows when the syllabus last changed. `scripts/validate_data.py` checks whatever notes are in the syllabus now.

### 17.4 Files

| File | Role |
|------|------|
| `backend/app/admin_api.py` | Admin routes |
| `backend/app/admin_auth.py` | Password, token, `require_admin` |
| `backend/app/live_config.py` | Live marking system and model availability |
| `backend/app/admin_eval.py` | Data sets, cost estimate, evaluation job |
| `backend/app/library.py` | Books: upload, AI reading, drafts, publish / remove / restore |
| `backend/app/kb/update.py` | Re-index only the changed topics and questions |
| `backend/app/jobs.py`, `runtime.py` | Background jobs; runtime settings file |
| `frontend/src/pages/admin/SystemSetup.tsx`, `pages/admin/Books.tsx` | The two admin pages |
| `frontend/src/components/AdminLayout.tsx`, `session/AdminContext.tsx` | Admin layout, sign-in state and route guard |
| `backend/tests/test_admin.py` | Sign-in, live system, textbook and exercise book from upload to syllabus and back (fake model, temporary folders) |

---

*Document updated: 25 October 2026 (admin part: system setup, books & syllabus).*

