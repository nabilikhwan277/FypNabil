# Implementation Plan: Intelligent KAFA UPKK Learning Assistant

A hybrid LLM + RAG system that assesses answers and gives feedback for UPKK Year 5 **Ibadah (Fiqh), Jawi and Tajwid**.

---

## 0. Summary of decisions

| Item | Decision |
|---|---|
| Users | Year 5 KAFA students (the teacher dashboard is saved for later) |
| Subjects / scope | Every topic in the three Year 5 textbooks (Ibadah KAFA JAKIM, Jawi JAIS, Tajwid JAIS) |
| Language | Bahasa Melayu, switchable between **Jawi** and **Rumi** (Jawi is shown right-to-left) |
| Input | Text only, with an on-screen Jawi keyboard |
| Question levels | Tahap 1 short answer → Tahap 2 structured → Tahap 3 essay |
| LLM | `mesolitica/Malaysian-Llama-3.2-1B-Instruct`, run locally through Hugging Face `transformers` |
| Embeddings | Multilingual model: `BAAI/bge-m3`, with `intfloat/multilingual-e5-base` as the fallback |
| Vector database | ChromaDB (runs on the laptop, stored on disk) |
| Student memory | SQLite |
| Backend | Python + FastAPI |
| Frontend | React + Vite + Tailwind CSS + Framer Motion, designed like a game |
| Hardware | RTX 3050 6 GB, 16 GB RAM, Windows |
| Out of scope | Voice, images, handwriting, ablation study, teacher dashboard (later) |

---

## 1. System architecture

```
┌───────────── React frontend (student) ─────────────────────────────┐
│ Login → Subject map → Topic → Question → Result                    │
│ XP / stars / streak / badges, Jawi ⇄ Rumi toggle                  │
│ AI Chat Assistant (ask before you practise)                        │
└──────────────────────────┬─────────────────────────────────────────┘
                           │ REST (JSON)
┌──────────────────────────▼─────────────────────────────────────────┐
│ FastAPI backend                                                     │
│  pipeline.assess(student, question, answer)                        │
│  chat.ask(student, question_text, history)  ← NEW Phase 9.2       │
│   1. Retrieve  ── ChromaDB (textbook chunks)                       │
│   2. ReAct     ── controlled Thought/Action loop                   │
│   3. Rubric    ── rule layer + LLM judge layer                     │
│   4. Feedback  ── adaptive, based on mastery                       │
│   5. Memory    ── SQLite update                                     │
└──────┬──────────────┬──────────────┬───────────────────────────────┘
       │              │              │
  Malaysian-Llama   ChromaDB       SQLite
  3.2-1B (GPU)      + bge-m3       (students, attempts,
                                    mistakes, mastery)
```

---

## 2. Folder structure

```
FypNabil/
├── IMPLEMENTATION_PLAN.md
├── README.md
├── text book/                  # official PDFs (source, not redistributed)
├── scraper/
├── data/
│   ├── knowledge/<subject>/    # verified topic notes (.md, Jawi + Rumi)
│   ├── questions/<subject>/    # questions + reference answers + rubrics (.json)
│   ├── silver/                 # synthetic training labels
│   └── splits/                 # train/test ids
├── backend/
│   ├── app/
│   │   ├── main.py             # FastAPI routes (including /api/chat)
│   │   ├── config.py
│   │   ├── schemas.py
│   │   ├── llm.py
│   │   ├── kb/ingest.py, retriever.py
│   │   ├── assess/rubric.py, react.py, feedback.py, pipeline.py, …
│   │   ├── chat.py             # AI chat helper (NEW Phase 9.2)
│   │   └── memory/db.py
│   └── tests/
├── frontend/
│   └── src/
│       ├── pages/              # Login, Home, Subject, Topic, Practice, Progress
│       ├── components/         # Layout, Mascot, Logo, ChatBox (NEW), ui.tsx, …
│       ├── sound/SoundContext.tsx
│       ├── session/            # StudentContext, ProgressContext
│       ├── lib/rank.ts, quick.ts
│       └── i18n/strings.ts
├── docs/
│   ├── thesis/chapter3_revised.md, chapter4_results_draft.md
│   ├── SUS_soal_selidik.md
│   └── figures/
├── eval/
└── scripts/
```

---

## Phase 1: Knowledge acquisition and data preparation ✅ DONE

48 topic notes (Jawi + Rumi) and 382 questions across 3 subjects.
`scripts/validate_data.py` passes with 0 errors.

| Subject | Topic notes | Questions |
|---|---|---|
| Ibadah (Fiqh) | 16 | — |
| Jawi | 10 | — |
| Tajwid | 22 | — |
| **Total** | **48/48** | **382** (L1 204 / L2 131 / L3 47) |

**⏳ Still needed:** teacher verification (`verified: true`), real student answer collection.

---

## Phase 2: Environment and project setup ✅ DONE

- `.venv` (Python 3.12), PyTorch 2.6.0+cu124, transformers 4.48.3, chromadb 1.5.9
- Models downloaded to `models/` — run offline with `HF_HUB_OFFLINE=1`
- Frontend: React 19, Vite 6, Tailwind 4, Framer Motion 12, React Router 7
- `npm run build` and `npm run lint` pass

---

## Phase 3: Knowledge base construction ✅ DONE

339 chunks from 48 notes → `storage/chroma` (ChromaDB).
Hybrid retrieval: bge-m3 dense + BM25, fused with RRF.

| Query type | Hybrid R@4 |
|---|---|
| Rumi, same subject | 0.990 |
| Jawi, same subject | 0.958 |
| Rumi, all subjects | 0.977 |

---

## Phase 4: Hybrid framework design ✅ DONE

Controlled 5-step ReAct loop. Two-layer rubric (rules + LLM judge).
Adaptive feedback templates. SQLite mastery tracking.

---

## Phase 5: Model configuration and integration ✅ DONE

Tuned on silver labels (446 answers). Deployed config: `no_llm_sim`.

| Config | Exact score | QWK |
|---|---|---|
| Phase 4 baseline | 0.849 | 0.921 |
| **no_llm_sim (deployed)** | **0.841** | **0.920** |

LLM judge AUC: 0.55–0.56 (near chance). Replaced by bge-m3 similarity (AUC 0.82).

---

## Phase 6: System development ✅ DONE

### 6.1 Backend API
All routes working: `/api/auth/login`, `/api/subjects`, `/api/topics/{id}/note`,
`/api/questions/next`, `/api/answers`, `/api/progress/{id}`, `/api/health`, `/api/avatars`.
57 backend tests pass.

### 6.2 Frontend — UI/UX refresh ✅ DONE (September 2026)

**App renamed** from "Pembantu KAFA" → **"Intelligent KAFA UPKK Learning Assistant"**

Major redesign for Year 5 pupils: game-like, mascot "Bulan" (round moon SVG), celebrations, sounds.

| Component / Feature | Status |
|---|---|
| `index.css` — gradient background, chunky buttons (`.btn-primary/secondary/choice`), `.card`, `.chip`, `.field`, custom animations (twinkle, floaty, wiggle, pop) | ✅ |
| `Mascot.tsx` — moods: happy, thinking, celebrate, encourage, wave; `SpeechBubble`, `MascotSay` | ✅ |
| `Logo.tsx` — SVG star logo | ✅ |
| `Confetti.tsx` — reduced-motion aware | ✅ |
| `Modal.tsx` — focus trap, Escape, backdrop close, `decor` prop | ✅ |
| `sound/SoundContext.tsx` — Web Audio tones (tap, correct, partial, wrong, levelup, finish), localStorage on/off | ✅ |
| `hooks/useSpeech.ts` — speechSynthesis, Malay/Indonesian voice, shown only if voice exists | ✅ |
| `session/ProgressContext.tsx` — shared XP/streak/badges, `refresh()` after each answer | ✅ |
| `lib/rank.ts` — 6 ranks (Pelajar Baharu → Juara UPKK), `rankFor(xp)` | ✅ |
| `lib/quick.ts` — quick-answer chips: Betul/Salah, word-fill blanks, composeBlanks | ✅ |
| `components/ui.tsx` — Stars, MasteryBar, ProgressRing, Card, Spinner (mascot thinking), ErrorBox (mascot encourage), Arrow | ✅ |
| `components/subjects.ts` — per-subject colours (hero/solid/edge/soft/ring/text/bar/hex/track) | ✅ |
| `components/RankCard.tsx` — rank with XP bar | ✅ |
| `components/CelebrationModal.tsx` — "Hebat!" dialog for new rank / level / badge | ✅ |
| `components/RoundSummary.tsx` — 5-question round summary | ✅ |
| `components/ResultCard.tsx` — stars, verdict, XP chip, correct answer, AI trace | ✅ |
| `components/Layout.tsx` — Logo + two-line brand, XP/streak chips, ApiStatus, SoundToggle, ScriptToggle, desktop nav, mobile bottom tab bar, skip link | ✅ |
| `pages/Login.tsx` — MascotSay wave, avatar tiles | ✅ |
| `pages/Home.tsx` — hero greeting, RankCard, "Sambung" card, subject rings, h2 "Pilih subjek" | ✅ |
| `pages/Subject.tsx` — hero, zigzag path, bab ribbons, "Mula di sini!" on recommended node | ✅ |
| `pages/Topic.tsx` — hero, level cards ("Mula Latihan"), note toggle (#note-panel) | ✅ |
| `pages/Practice.tsx` — 5-question rounds, quick-answer chips, hint system, listen (TTS), Enter to submit, checking overlay (≥ 650 ms), celebration modal, round summary | ✅ |
| `pages/Progress.tsx` — rank hero, stat cards (Mata XP, streak), trophy shelf, subject rings, recent attempts | ✅ |
| `backend/app/memory/db.py` — concurrent-safe reads (RLock, all reads locked) | ✅ |
| `scripts/e2e_ui.py` — updated: checks "Semak Jawapan", celebration modal, round summary, word chips, Betul/Salah buttons, Jawi mode | ✅ |

**e2e walkthrough passes with no console errors or server errors.**
`npm run build`, `tsc -b`, `eslint` all pass. 57 pytest tests pass.

---

## Phase 7: System evaluation ✅ DONE (silver labels)

Run on held-out test split (485 answers).

| Group | Exact score | QWK |
|---|---|---|
| All | 0.841 | 0.920 |
| Tahap 1 | 0.938 | 0.953 |
| Tahap 2 | 0.785 | 0.866 |
| Tahap 3 | 0.635 | 0.931 |

- Consistency (same answer × 3): **100%**
- Latency — Tahap 1 median: **56 ms**, Tahap 3: **154 ms**
- Retrieval Recall@4 (test): Rumi 1.000, Jawi 0.934

**⏳ Still needed:** teacher-marked answers, SUS questionnaire (≥ 10 students).

---

## Phase 8: Documentation ✅ DONE

| Deliverable | File |
|---|---|
| Examiner README | `README.md` |
| Thesis chapters | Word files outside this repository (the old Markdown drafts were removed) |
| Figures (PNG 2×) | `docs/figures/` |
| SUS questionnaire | `docs/SUS_soal_selidik.md` + `scripts/sus_score.py` |
| Teacher kit | `scripts/teacher_sheet.py` |

UI screenshots (from `scripts/e2e_ui.py`) → `eval/results/ui_*.png`
→ copied to `docs/figures/` by `scripts/render_figures.py`.

---

## Phase 9: Extensions *(in progress)*

### 9.1 UI/UX refresh ✅ DONE (see Phase 6.2)

### 9.2 AI Chat Assistant ✅ DONE (September 2026)

Students can ask free-form questions about any KAFA/UPKK topic **before** practising, directly from the Home page. Bulan the mascot answers using the existing RAG pipeline (same KB as the assessor).

**Architecture:**
- `POST /api/chat` — takes `{student_id, message, subject?, history[]}`, retrieves up to 4 relevant note chunks with `search_notes()`, formats a prompt with the retrieved context, calls the LLM (`max_new_tokens=300`, `repetition_penalty=1.15`, `no_repeat_ngram_size=4`), and returns `{reply, sources[]}`.
- The reply is grounded in the textbook (same guard as feedback: only use retrieved context). Sources show which topic + page.
- History (last 3 turns) is included in the prompt so follow-up questions work.
- Rate-limited: maximum 10 messages per session; resets on login.
- `frontend/src/components/ChatBox.tsx` — floating chat panel on Home page, collapsible. Mascot "thinking" dots while waiting. Jawi/Rumi aware (sends current script to backend).

**New backend file:** `backend/app/chat.py`
**New frontend component:** `frontend/src/components/ChatBox.tsx`
**New backend route:** `POST /api/chat`

### 9.3 Teacher dashboard *(planned)*
- Class progress overview, weak topics heatmap.
- Override AI score on individual attempts.
- Overrides stored as new training data.

### 9.4 Deployment *(planned)*
- Docker container (backend + static frontend build).
- Run on a school server or Azure (student-grade).
- Proper authentication (school login).

### 9.5 Text-to-speech for notes *(planned)*
- Use Malay TTS (e.g. Azure Neural TTS) to read notes aloud.
- Useful for lower-literacy students.

---

## Order of work

```
Phase 1 (data) ──► Phase 2 (setup) ──► Phase 3 (KB)
                         │
                         └──► Phase 6.2 UI (parallel)
Phase 3 ──► Phase 4 ──► Phase 5 ──► Phase 6.1 (API) ──► Phase 7 (eval) ──► Phase 8
                                                                                │
                                                                     Phase 9.2 (chat)
                                                                     Phase 9.3 (teacher)
                                                                     Phase 9.4 (deploy)
```

---

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| 1B model judges unreliably | Replaced by similarity scoring (no_llm_sim); LLM only for encouragement text and chat |
| Transcription mistakes | Teacher verification required; `[TIDAK JELAS]` markers |
| Jawi input on devices | On-screen Jawi keyboard; answer in Rumi also accepted |
| Not enough real student answers | Silver labels used; teacher-marked set needed before viva |
| GPU memory / latency | fp16; one model instance; requests queued; mascot animation covers wait |
| Copyright of textbooks | Private research use; not in public repo |
| No authentication (prototype) | Localhost / school LAN only; add auth before public deploy |
| Chat LLM hallucination | Answers grounded by retrieved chunks; sources shown; disclaimer shown in UI |
