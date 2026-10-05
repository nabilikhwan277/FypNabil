# Silver answer sets (NOT teacher-marked)

These answers were created so Phase 5 (tuning) and Phase 7 (evaluation) could run
before teacher-marked student answers exist. They are a **development estimate**,
not the thesis ground truth.

| File | How it was made | How it was labelled |
|---|---|---|
| `programmatic_{train,test}.json` | Built by `scripts/make_silver_programmatic.py` from each question's reference answer: the reference itself (Rumi/Jawi), a one-letter Jawi misspelling, a Rumi word for a "tulis dalam Jawi" item, a changed number, a flipped Betul/Salah, "saya tidak tahu", another topic's answer | By construction (full marks or zero) |
| `paraphrase_{train,test}_{subject}.json` | Written by an AI (Claude) simulating Year 5 pupils, following `_writer_guide.md`: a full answer in the pupil's own words, a partial answer, and a misconception, about 1 in 4 in Jawi script | The same AI acting as a strict teacher, per rubric criterion (ya / separa / tidak) |

| Split | Programmatic | Paraphrase | Questions |
|---|---|---|---|
| train | 1283 (200 sampled for tuning) | 263 | 90 of 306 |
| test | 322 | 163 | 56 of 76 |

Known limitations:
- The paraphrase labels come from one AI marker, not a teacher, so they share that marker's biases.
- The answers are AI-written. Real pupils make different mistakes (spelling, very short answers, mixed scripts).
- The programmatic answers are easy by design; they test known failure modes, not typical answers.

To replace these with teacher marks, run `scripts/teacher_sheet.py export`, have a teacher fill in
`teacher_met`, then `import`. See the script's docstring.
