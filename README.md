# Intelligent KAFA UPKK Learning Assistant

A web-based prototype that assesses Year 5 KAFA pupils' text answers in **Ibadah (Fiqh), Jawi and Tajwid** and returns a score, the mistakes, the correct answer with its textbook page, and a next-step suggestion. It combines retrieval-augmented generation (RAG) over the official textbooks, a controlled ReAct loop, two-layer rubric scoring and a per-pupil learning memory. The interface works in both Rumi and Jawi script.

Final Year Project, Bachelor of Information Systems (Hons.) Intelligent Systems Engineering, UiTM. Author: Muhammad Nabil Ikhwan bin Ahmad Safuwan. Supervisor: Dr. Ezzatul Akmal binti Kamaru-Zaman.

> **Prototype.** There is no authentication: a pupil is identified by name + class only. Run it on a single computer or a trusted school network. The textbook notes are AI-assisted transcriptions and are marked `verified: false` until a teacher has checked them (`data/REVIEW_CHECKLIST.md`).

## What it does
- 48 textbook topics, 382 questions at three levels: Tahap 1 short answer, Tahap 2 structured, Tahap 3 essay.
- A 5-step ReAct loop per answer: read the rubric → search the textbook → score each criterion → recall the pupil's history → build feedback. Every step is shown to the pupil as "Bagaimana AI berfikir".
- Rubric scoring: exact Jawi spelling, Betul/Salah and keyword rules first, then multilingual semantic similarity for everything else.
- Learning memory: mastery per topic, levels unlocking at 70%, XP, streaks, badges and repeated-mistake reminders.
- Pupil UI: game-style map, note reader, on-screen Jawi keyboard, Rumi/Jawi switch, works on phones.

## Requirements
| Item | Tested with |
|---|---|
| OS | Windows 11 |
| Python | 3.12 |
| Node.js | 20 or newer (tested on 26) |
| GPU | NVIDIA with ≥ 6 GB VRAM (RTX 3050 6 GB). CPU works but is slower: set `KAFA_DEVICE=cpu` |
| Disk | ~6 GB for the models |

## Setup
From the project folder (`FypNabil/`), in PowerShell:

```powershell
# 1. Python environment
python -m venv .venv
.venv\Scripts\pip install torch==2.6.0 --index-url https://download.pytorch.org/whl/cu124
.venv\Scripts\pip install -r backend\requirements.txt

# 2. Models (first run downloads ~5 GB into models/, then works offline)
.venv\Scripts\python scripts\smoke_llm.py
$env:HF_HUB_OFFLINE="1"

# 3. Knowledge base (ChromaDB, ~25 s)
.venv\Scripts\python -m backend.app.kb.ingest

# 4. Frontend
cd frontend; npm install; cd ..
```

## Run
Use two terminals:

```powershell
# Terminal 1: backend API on http://127.0.0.1:8000 (models load in the background)
$env:HF_HUB_OFFLINE="1"; .venv\Scripts\uvicorn backend.app.main:app --port 8000

# Terminal 2: web app on http://localhost:5173
cd frontend; npm run dev
```

Open http://localhost:5173, type a name and class, and pick a subject. The status pill shows "AI sedang bersedia…" until the models have loaded, which takes 10–30 s. API documentation is at http://127.0.0.1:8000/docs.

## Tests and checks
```powershell
.venv\Scripts\python -m pytest -q                 # 57 backend tests
.venv\Scripts\python scripts\validate_data.py     # notes + question bank
cd frontend; npm run build; npm run lint          # frontend
.venv\Scripts\python scripts\e2e_ui.py            # browser walkthrough (both servers running)
```

## Reproduce the evaluation
| Step | Command | Output |
|---|---|---|
| Retrieval | `python eval\retrieval_eval.py train` (or `test`) | `eval/results/retrieval_*.md` |
| Cache scoring signals | `python eval\scoring_features.py train 200` then `... test` | `eval/cache/` |
| Tune on train | `python eval\tune_scoring.py` | `eval/results/tuning.md`, `backend/app/assess/scoring_config.json` |
| Evaluate on test | `python eval\evaluate.py 60` | `eval/results/evaluation_test.md` |
| Teacher marks | `python scripts\teacher_sheet.py export` → teacher fills `teacher_met` → `import file.csv` → `scoring_features.py teacher` → `evaluate.py 0 teacher` | `eval/results/evaluation_teacher.md` |
| Usability (SUS) | fill in `docs/sus_responses.csv`, then `python scripts\sus_score.py docs\sus_responses.csv` | `eval/results/sus.md` |

Current results use **silver labels** (AI-written and rule-built answers, see `data/silver/README.md`), not teacher marks.

## Project structure
```
backend/app/        FastAPI app
  assess/           rubric (Layer A), decision rules, judges, feedback, ReAct loop, pipeline
  kb/               chunking, ChromaDB store, BM25, hybrid retriever
  memory/db.py      SQLite learning memory
  prompts/          LLM prompt templates
backend/tests/      pytest suite (fake models, no GPU needed)
frontend/src/       React + Vite + Tailwind pupil app
data/knowledge/     48 topic notes (Rumi + Jawi)
data/questions/     question bank with rubrics
data/splits/        train / test question ids
data/silver/        silver answers for tuning/evaluation
eval/               evaluation scripts and results
scripts/            data validation, figures, demos, teacher/SUS kits
docs/               thesis figures and drafts, SUS questionnaire
IMPLEMENTATION_PLAN.md   phase-by-phase plan and status
```

## Configuration
Environment variables with the `KAFA_` prefix override `backend/app/config.py`. Examples:
- `KAFA_DEVICE=cpu`
- `KAFA_PRELOAD_MODELS=false`
- `KAFA_LLM_ENCOURAGEMENT=true`
- `KAFA_SQLITE_PATH=storage/other.db`

The scoring method is chosen in `backend/app/assess/scoring_config.json`, which `eval/tune_scoring.py` writes.

## Data and copyright
The textbooks (Buku Teks Ibadah KAFA JAKIM Tahun 5, Buku Teks Jawi and Tajwid JAIS Tahun 5) are used for private academic research only. The PDFs (`text book/`), page images (`data/raw/`) and downloaded models are excluded from version control by `.gitignore`. Do not publish the transcribed notes without permission from the publishers.
