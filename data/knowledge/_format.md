# Knowledge note + question format (for transcription agents)

Source page images: `data/raw/<book>/pages/page_NNN.webp` (NNN = PDF page, 3 digits).
Books: `fiqh` (Ibadah KAFA JAKIM Tahun 5), `jawi` (JAIS Jawi Tahun 5), `tajwid` (JAIS Tajwid Tahun 5).
All books are written in Jawi script.

## Rules
1. Transcribe ONLY what the textbook says. Do not add outside facts, dalil, or opinions.
2. Quran verses, hadith, doa, lafaz niat: copy the Arabic exactly as printed (keep harakat if printed).
   If any word is unclear write `[TIDAK JELAS]`. Never guess religious text.
3. Every section gives the Jawi text (faithful to the book) AND a Rumi (Latin Malay) version.
4. Skip decorative text, page numbers, QR codes, headers like "Bagus dan Faham" unless they carry content.
5. Pictures with meaning (e.g. steps of solat, examples in a table) -> describe in text.
6. One markdown file per topic (unit/sub-topic in the contents page). Chapter intro pages go into the first topic of that chapter, or a `<bab>_pengenalan` file if substantial.
7. Textbook exercises (Latihan / Aktiviti) -> put them in the question file with `"origin": "textbook"`.

## Note file: `data/knowledge/<subject>/<topic_id>.md`
`topic_id` = `<subject>_b<bab>_<slug>` e.g. `tajwid_b2_mad_asli_kalimi`, `fiqh_b1_solat_dhuha`, `jawi_b1_imbuhan_an_nun`.

```markdown
---
id: tajwid_b2_mad_asli_kalimi
subject: tajwid            # fiqh | jawi | tajwid
year: 5
bab: 2
bab_rumi: Mad Asli
bab_jawi: مد اصلي
topic_rumi: Mad Asli Kalimi
topic_jawi: مد اصلي كلمي
source: e-BOOK Buku Teks JAIS TAJWID TAHUN 5.pdf
pdf_pages: [15, 16]
book_pages: [6, 7]
verified: false            # a teacher must check before use
---

# Mad Asli Kalimi | مد اصلي كلمي

## Pengertian
**Rumi:** ...
**Jawi:** ...

## Isi Penting
- **Rumi:** ... | **Jawi:** ...

## Contoh
- ... (Arabic example exactly as printed, plus explanation in Rumi and Jawi)

## (other headings the book uses: Hukum, Cara Bacaan, Kadar Harakat, Syarat, Rukun,
##  Waktu, Lafaz Niat, Kelebihan/Fadhilat, Hikmah, Nilai/Amalan ...)
```

## Question file: `data/questions/<subject>/<topic_id>.json`
Per topic: at least 3 level-1, 2 level-2, 1 level-3 questions, answerable ONLY from the note.
- level 1 = short answer (1 word / 1 phrase), 1-2 marks
- level 2 = structured (list / explain 2-3 points), 3-4 marks
- level 3 = essay-style (explain + example / apply), 5-6 marks

```json
{
  "topic_id": "tajwid_b2_mad_asli_kalimi",
  "subject": "tajwid",
  "questions": [
    {
      "id": "tajwid_b2_mad_asli_kalimi_q1",
      "level": 1,
      "type": "short",               
      "origin": "generated",
      "question_rumi": "Berapakah kadar harakat bacaan Mad Asli?",
      "question_jawi": "...",
      "reference_answer_rumi": "Dua harakat",
      "reference_answer_jawi": "...",
      "rubric": [
        {"criterion": "Menyatakan kadar dua harakat", "marks": 1, "keywords": ["2 harakat", "dua harakat"]}
      ],
      "max_marks": 1,
      "source_pages": [15]
    }
  ]
}
```
`type`: short | structured | essay. `origin`: generated | textbook.
`max_marks` must equal the sum of rubric marks. Keywords: Rumi and Jawi spellings a correct answer would contain.
