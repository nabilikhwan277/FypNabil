# Chapter 3 – Revised sections (draft for the thesis)

This file replaces the parts of Chapter 3 that no longer match what was built. Sections 3.1–3.5 can stay as they are. Figures are in `docs/figures/`.

## What changed and why (for you and your supervisor)

| Thesis (proposal) | Built system | Reason |
|---|---|---|
| Llama 3.1 through Ollama | Malaysian-Llama-3.2-1B-Instruct (mesolitica) through Hugging Face `transformers` | Fine-tuned on Malaysian and Jawi data, better on MalayMMLU than its base model (41.3% vs 37.9%), fits a 6 GB laptop GPU |
| LLM judges the answer | LLM judge tested; rubric points decided by rules + multilingual semantic similarity | Measured: the 1B judge could not tell right from wrong points (Section 3.10) |
| Streamlit interface | React + FastAPI web app | Game-style design for Year 5 pupils, works on phones, full Jawi (right-to-left) interface, on-screen Jawi keyboard |
| Google Antigravity | Kiro (AI-assisted IDE), Visual Studio Code | Tools actually used; **edit to match what you used** |
| Sentence Transformers (unspecified model) | BAAI/bge-m3 via sentence-transformers | Multilingual, handles Malay and Arabic script |
| Rubric in CSV/JSON/SQLite | Rubric in JSON per topic, memory in SQLite | As proposed |
| Evaluation with sample student answers | Silver answer set now; teacher-marked set prepared | No teacher-marked answers were available yet |

---

## 3.6 Data Collection

The learning materials are the three official Year 5 textbooks used in KAFA classes: *Buku Teks Ibadah KAFA JAKIM Tahun 5* (66 pages), *Buku Teks Jawi JAIS Tahun 5* (80 pages) and *Buku Teks Tajwid JAIS Tahun 5* (74 pages). The whole syllabus of the three books was included, because the UPKK examination covers every topic. This gives 16 Ibadah topics (the sunat prayers and fasting), 10 Jawi topics (the imbuhan *-an* and *-i*, loan words and acronyms) and 22 Tajwid topics (the types of mad, the ranking of mad, waqaf and ibtida').

Assessment questions were prepared for every topic at three levels: Tahap 1 short answers, Tahap 2 structured answers and Tahap 3 essay-style answers. Exercises printed in the textbooks were included and marked as textbook questions. Each question has a reference answer in Rumi and Jawi and a marking rubric. The rubric lists the criteria, the marks for each criterion and the keywords a correct answer would contain. In total 382 questions were prepared: 204 at Tahap 1, 131 at Tahap 2 and 47 at Tahap 3.

## 3.7 Data Preprocessing

All three textbooks were available only as image-based PDF files with no text layer (Figure 3.6). The pages were extracted as images, and the content of each topic was transcribed into a structured note with AI assistance. Each note keeps the Jawi text of the book together with a Rumi version. Quranic verses, lafaz niat, doa and takbir were copied exactly as printed, and any word that could not be read clearly was marked [TIDAK JELAS] instead of being guessed. Each note records its subject, bab, topic title and the textbook pages it came from, and carries a *verified* flag that a teacher sets after checking it. A review checklist lists the unclear words, the Arabic text and the answers that had to be inferred, so the checking can be done efficiently.

A validation script checks the whole dataset:
- every topic has a note
- every question has a rubric whose marks add up to the question's total
- each topic has at least three Tahap 1, two Tahap 2 and one Tahap 3 question.

The questions were then split with the hold-out method into a training set of 306 questions and a test set of 76 questions, stratified by subject and level. The training set was used for all configuration and tuning; the test set was used only once, for the final evaluation.

## 3.8 Knowledge Base Construction

Each note was divided into chunks at its section headings (for example *Pengertian*, *Kadar Harakat*, *Lafaz Niat*). Long sections were split further at paragraph boundaries with a small overlap. Each chunk starts with its topic and section title in Rumi and Jawi, so it still makes sense when retrieved on its own. The 48 notes produced 339 chunks.

The chunks were converted into vector embeddings with the multilingual model BAAI/bge-m3 and stored in ChromaDB, together with the subject, topic, section and page numbers as metadata. The reference answers of all 382 questions were stored in a second collection for similarity scoring.

Early tests showed that bge-m3 retrieves Jawi-script queries less accurately than Rumi ones. The retriever was therefore made **hybrid**: the semantic search result is combined with a BM25 keyword search using Reciprocal Rank Fusion. The retriever searches the question's own topic first and fills any remaining places from the rest of the subject.

## 3.9 Hybrid Framework Design

The framework combines retrieval-augmented generation, ReAct reasoning, rubric-based evaluation and student learning memory (Figure 3.2). Because the language model is small (1 billion parameters), the ReAct loop is **controlled**: the programme, not the model, decides the order of the steps. Each step records a *thought*, an *action* and an *observation*, and this trace is saved and shown to the pupil (Figure 3.3). The five steps are:

1. **get_question**: read the rubric criteria, marks and reference answer.
2. **search_notes**: retrieve the four most relevant textbook chunks (RAG).
3. **score_rubric**: decide each criterion.
4. **get_history**: read the pupil's mastery of the topic and repeated mistakes.
5. **generate_feedback**: build the feedback.

The attempt is then saved and the learning memory updated.

**Rubric-based evaluation** works in two layers (Figure 3.4).
- **Layer A** applies deterministic rules:
  - a Jawi spelling criterion must match the reference spelling exactly after normalisation (harakat removed and font-only letter variants unified);
  - a Betul/Salah criterion must state the right choice;
  - a criterion is met when one of its rubric keywords appears in the answer, unless the answer contradicts the numbers in the reference answer (for example "enam harakat" instead of "dua harakat").
- **Layer B** decides the criteria that Layer A cannot settle, using the method selected in the configuration stage (Section 3.10).

Each criterion is decided as met (*ya*), partly met (*separa*) or not met (*tidak*). The marks are added up by the programme, never by the language model.

**Student learning memory** is stored in SQLite (Figure 3.5):
- Mastery of each topic is an exponential moving average of the pupil's scores (0.7 × previous + 0.3 × new).
- The next level of a topic unlocks when the last three attempts at the current level average at least 70%.
- A criterion the pupil misses twice in the same topic is recorded as a repeated mistake and mentioned in later feedback.
- The pupil also earns stars, XP, a daily streak and badges to encourage regular practice.

**Adaptive feedback** is built from templates in Rumi and Jawi. It contains:
- the score and stars;
- the criteria that were missed;
- the correct answer, with the textbook page it comes from;
- any repeated mistake;
- a next step that depends on mastery: re-read the note and try Tahap 1 when mastery is below 40%, try a similar question up to 70%, or move to the next level once it unlocks.

Every fact in the feedback comes from the rubric, the reference answer or the note, so the feedback cannot contain invented content.

## 3.10 Model Configuration and Integration

The language model is **Malaysian-Llama-3.2-1B-Instruct** by Mesolitica, run locally in 16-bit precision with the Hugging Face `transformers` library. It is a version of Llama 3.2 1B that was further trained on a Malaysian instruction dataset, and it supports standard Malay, Jawi and Malaysian religious context. On the MalayMMLU benchmark it scores 41.3% against 37.9% for the original Llama 3.2 1B. It needs about 2.8 GB of GPU memory; together with the bge-m3 embedding model the peak is about 5.4 GB, which fits the 6 GB laptop GPU used for development. Because it runs locally, no paid API is needed and pupils' answers never leave the machine.

A smoke test showed that the model gives wrong facts when asked without context, but answers correctly when the relevant textbook passage is included in the prompt. This confirms the need for retrieval grounding.

Three ways of using the model to judge a rubric criterion were implemented and compared:
- **a generative judge**, which writes a verdict in JSON, protected by a similarity guard;
- **a probability judge**, which reads the model's first-token probabilities for YA, SEPARA and TIDAK, with and without three worked examples;
- **a hybrid** of the probability judge and semantic similarity.

These were compared with methods that use no language model: semantic similarity between the answer and the criterion, keyword and content-word overlap, and combinations of them. Every method was tuned on the training set only.

On the training set, the generative judge answered "ya" for every criterion, whether the silver label was right or wrong, and the probability judge separated right from wrong criteria only slightly better than chance (AUC 0.55). Semantic similarity separated them clearly better (AUC 0.76–0.82). The lowest error was therefore reached without the language model: Layer B awards a Tahap 2/3 criterion when the bge-m3 similarity between the answer and the criterion is at least 0.65 and no number is contradicted. At Tahap 1 only the Layer A rules apply. The selected configuration is stored in a configuration file, so the language-model judge can be switched back on without changing the code.

The framework remains hybrid:
- RAG grounds each assessment in the textbook and supplies the source page;
- a multilingual embedding model performs the semantic part of the rubric evaluation;
- the controlled ReAct loop links retrieval, rubric evaluation and learning memory.

The finding that a 1B-parameter model cannot reliably judge rubric criteria is itself a result of this study (Chapter 4).

## 3.11 System Development

**Tools**
- The system was developed in Python 3.12 for the backend and TypeScript for the user interface, using the Kiro AI-assisted development environment and Visual Studio Code. *(Edit to match the tools you actually used.)*
- **Backend** (FastAPI):
  - `transformers` and PyTorch for the language model
  - `sentence-transformers` with bge-m3 for embeddings
  - ChromaDB as the vector database
  - SQLite for the student learning memory
  - It exposes endpoints for login, the subject and topic catalogue, topic notes, adaptive question selection, answer assessment and progress.
- **Web application:** React with Vite, Tailwind CSS and Framer Motion.

**Screens.** The interface was designed for Year 5 pupils (Figures 3.7–3.14):
- a login screen with animal avatars
- a map of the three subjects
- a topic path for each subject, like a game level map
- a topic page with the textbook note and three level cards
- a practice screen with an on-screen Jawi keyboard, which includes the letters چ ڠ ڤ ݢ ۏ ڽ
- a result card with stars, mistakes, the correct answer, the textbook source and a "Bagaimana AI berfikir" panel showing the ReAct trace
- a progress page with XP, streak, badges and mastery per topic.

**Language and devices.** The whole interface can be switched between Rumi and Jawi, with right-to-left layout in Jawi mode, and it works on phones and tablets.

**Accessibility.** Labelled controls, visible focus, text next to every colour cue, touch targets of at least 48 pixels, and a reduced-motion setting.

**Testing.** The prototype has 57 automated backend tests and an automated browser walkthrough of the full flow.

## 3.12 System Evaluation

The evaluation covers five areas:
- scoring agreement
- retrieval quality
- consistency
- performance
- usability.

**Evaluation data.** Teacher-marked pupil answers were not yet available, so a **silver** evaluation set was prepared from the test questions (485 answers):

| Part | What it is | How it was labelled |
|---|---|---|
| Rule-built answers | The reference answer itself; a Jawi spelling with one wrong letter; a Rumi word given for a "write in Jawi" question; a changed number; a flipped Betul/Salah; "saya tidak tahu"; another topic's answer | Correct mark known by construction |
| AI-written answers | Pupil-style answers written by an AI: a full answer in the pupil's own words, a partial answer and a common misconception, about one in four in Jawi script | Each rubric criterion marked by the same AI acting as a strict teacher |

A matching training set was used for tuning. A marking sheet and import script were prepared so the same evaluation can be repeated with teacher marks.

**Measures**
- **Scoring agreement:**
  - the share of answers given exactly the expected mark, and within one mark
  - mean absolute error
  - quadratic weighted kappa (QWK)
  - the share of answers over- and under-marked
  - all reported by level, subject and answer type.
- **Retrieval:** whether the correct topic appears in the top four results (Recall@4).
- **Consistency:** each answer was assessed three times and checked for an identical score.
- **Performance:** response time per level, and the share of assessments completed without error.
- **Usability:** measured with the System Usability Scale (SUS) questionnaire in Malay, answered by pupils or teachers after using the system; a mean score of 68 or above is considered above average.
- **Feedback quality:** a teacher rates a sample of feedback for accuracy, relevance and clarity.
