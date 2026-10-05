# System Detail: Intelligent KAFA UPKK Learning Assistant

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
| **Model ID** | `mesolitica/Malaysian-Llama-3.2-1B-Instruct` |
| **Source** | Hugging Face (downloaded offline to `models/`) |
| **Parameters** | 1 billion |
| **Purpose** | Encouragement text generation (optional), AI Chat answers |
| **Precision** | float16 on CUDA |
| **VRAM usage** | ~2.8 GB (peak ~5.4 GB with embedder loaded together) |
| **Speed** | 15–30 tokens/s on RTX 3050; short answers 0.6–1.7 s |
| **Why this model** | Fine-tuned on Malaysian Malay and Jawi text; MalayMMLU score 41.3% vs 37.9% base |
| **Cache directory** | `models/` |

**Important:** The LLM is **NOT used for rubric scoring** because the 1B model always says "ya" (AUC 0.55, near-chance). Scoring uses embedding similarity instead.

The LLM is used for:
1. **AI Chat** (`/api/chat`) — answers student questions grounded in retrieved textbook chunks
2. **Encouragement line** (optional, off by default) — a short 1–2 sentence motivational sentence after each result

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

**How it works:**

1. Student types a question (max 500 characters)
2. `search_notes(question, subject, k=4)` retrieves 4 relevant textbook chunks
3. Prompt is built: retrieved chunks + conversation history (last 3 turns) + student's question
4. LLM generates a reply (max 300 tokens, temperature 0.3, repetition penalty 1.15)
5. Reply is cleaned (echo removal, repetition trimming)
6. Sources (topic name + page number) are attached to the response

**Rate limit:** 10 questions per session (resets on login).

**Prompt structure (`backend/app/prompts/chat.txt`):**
```
System: You are Bulan, a friendly KAFA study assistant...
Context: [4 retrieved textbook chunks]
History: [last 3 conversation turns]
Student question: [current message]
Bulan's answer:
```

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

**CORS:** `http://localhost:5173` and `http://127.0.0.1:5173` only (dev only).

**API docs:** http://127.0.0.1:8000/docs (Swagger UI auto-generated by FastAPI)

---

## 10. Frontend

Framework: **React 19**, **Vite 6.4**, **TypeScript**, **Tailwind CSS 4**, **Framer Motion 12**

Dev server: `http://localhost:5173`

### 10.1 Pages

| Route | Page | Description |
|-------|------|-------------|
| `/login` | Login | Name + class + avatar picker |
| `/` | Home | Greeting, rank, "Sambung" card, 3 subject rings |
| `/subjek/:id` | Subject | Zigzag path of topics, grouped by bab |
| `/topik/:id` | Topic | Level cards, note toggle |
| `/latihan/:topicId/:level` | Practice | 5-question round, result, celebration |
| `/kemajuan` | Progress | XP, streak, badges, mastery charts |

### 10.2 Key Frontend Components

| Component | Purpose |
|-----------|---------|
| `Mascot.tsx` | Animated moon mascot "Bulan" (5 moods) |
| `ChatBox.tsx` | Floating AI chat panel |
| `JawiKeyboard.tsx` | On-screen Jawi keyboard (auto-shows for Jawi questions) |
| `ResultCard.tsx` | Stars, verdict, correct answer, AI trace |
| `CelebrationModal.tsx` | "Hebat!" dialog for new rank/level/badge |
| `RoundSummary.tsx` | End-of-5-question-round summary |
| `Layout.tsx` | Header (logo, XP chip, sound toggle), mobile bottom tab bar |
| `SoundContext.tsx` | Web Audio tones (tap, correct, partial, wrong, levelup, finish) |
| `ProgressContext.tsx` | Shared XP/streak across all pages |

### 10.3 Script Toggle (Jawi ⇄ Rumi)

The entire UI switches between Bahasa Melayu in:
- **Rumi** (Latin script, LTR) — default
- **Jawi** (Arabic script, RTL) — `html dir="rtl" lang="ms-Arab"`

Every UI string has both versions in `frontend/src/i18n/strings.ts`. Question text and answers automatically detect direction with `textDir()`.

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
│   │       ├── chat.txt                  ← AI chat prompt template
│   │       ├── judge_criterion.txt       ← LLM judge prompt (evaluation only)
│   │       └── encourage.txt             ← LLM encouragement prompt
│   └── tests/                            ← 57 pytest tests
│
├── frontend/
│   └── src/
│       ├── pages/                        ← Login, Home, Subject, Topic, Practice, Progress
│       ├── components/                   ← Mascot, ChatBox, JawiKeyboard, ResultCard, …
│       ├── api/client.ts                 ← fetch wrappers
│       ├── api/types.ts                  ← TypeScript type definitions
│       ├── i18n/strings.ts               ← all UI strings (Rumi + Jawi)
│       ├── session/                      ← StudentContext, ProgressContext
│       ├── sound/SoundContext.tsx         ← Web Audio tones
│       └── lib/rank.ts, quick.ts         ← rank/XP helpers, quick-answer logic
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
| Chat response time (LLM) | ~3–8 s |
| Success rate (180 test runs) | 100% |
| SQLite DB size | 108 KB |
| ChromaDB size | 7.9 MB |
| Models total | 7.06 GB |

---

*Document auto-generated from the live codebase. Last updated: September 2026.*
