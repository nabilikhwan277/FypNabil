# Guide for writing silver student answers

You are simulating **Year 5 KAFA pupils** answering questions, and then marking
each answer like a **strict but fair KAFA teacher**. These answers are used to
test an automatic marker, so the labels must be honest and independent: mark by
meaning against the rubric and the textbook note, NOT by whether keywords appear.

## Input
An assignment file `data/silver/_assign/<split>_<subject>.json`: a list of
questions, each with its rubric (criteria + marks + keywords), reference answer and
`note_file` (the textbook note, read it for the facts).

## Output
`data/silver/paraphrase_<split>_<subject>.json`: a JSON list. For EVERY question
write **3 answers** (spelling-only Jawi questions: 2, see below):

| kind | what to write |
|---|---|
| `paraphrase_full` | Fully correct, but **in the pupil's own words**. Do not copy the reference answer; reorder, use synonyms, simpler words, short sentences. Avoid reusing the exact keyword phrases where natural wording differs (e.g. "berhenti sekejap untuk ambil nafas" instead of "memberhentikan bacaan dengan mengambil nafas"). Every criterion must still be satisfied in meaning. |
| `partial` | Correct for some criteria only, or too vague/incomplete for one of them. For a 1-criterion question: an incomplete or vague answer (usually `separa`) or a half-right one. |
| `misconception` | A plausible WRONG answer a child might give: mixing up with a related topic (e.g. Mad Wajib vs Mad Jaiz, witir vs tarawih, wrong harakat count, wrong rakaat), or a wrong reason. Mostly `tidak`, possibly one criterion right. |

Spelling-only Jawi questions ("Tulis perkataan 'X' dalam tulisan Jawi"):
write `paraphrase_full` = the correct spelling exactly as the reference (spacing
variants allowed), and `misconception` = a realistic child misspelling (e.g. missing
alif, ك instead of ݢ, ف instead of ڤ, ت instead of ة). No `partial`.

Style: Year 5 language, short, sometimes informal ("sebab", "kena", "tak"), may
contain small spelling slips in Rumi that do not change meaning. Around 1 in 4
answers (and most answers for the Jawi subject) should be written in **Jawi script**
(set `"script": "jawi"`); the rest in Rumi (`"script": "rumi"`). Arabic quotations
(niat, ayat) may be used where the question asks for them; copy them correctly for
`paraphrase_full`.

## Labels
For each rubric criterion, in order, give `met`:
- `ya` - the criterion is clearly satisfied in meaning
- `separa` - partly satisfied / incomplete / imprecise
- `tidak` - missing or wrong

`expected_score` = sum over criteria of: ya -> marks, separa -> half the marks
rounded to the nearest 0.5 (minimum 0.5), tidak -> 0.

## Item format
```json
{
  "question_id": "fiqh_b1_solat_dhuha_q5",
  "answer_id": "fiqh_b1_solat_dhuha_q5::paraphrase_full",
  "kind": "paraphrase_full",
  "script": "rumi",
  "answer": "...",
  "criteria": [{"criterion": "<exact criterion text from rubric>", "met": "ya"}],
  "expected_score": 2,
  "label_source": "silver_writer",
  "rationale": "one short sentence why"
}
```
`criteria` must list every rubric criterion of the question, in the same order,
with the exact criterion text. The file must be valid JSON (UTF-8).
