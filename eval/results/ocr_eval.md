# Reading scanned textbook pages (Phase 2.3 / 2.4)

10 pages (7 whole notes: fiqh_b2_fadhilat_puasa p59, fiqh_b2_batal_puasa p60, fiqh_b2_puasa_wajib_sunat p61, fiqh_b2_hikmah_puasa p62, tajwid_b3_mad_iwadh p59,60, tajwid_b3_mad_silah_qasirah p63, jawi_b4_akronim_dilafaz p77,78,79). Reference: the knowledge notes (AI-transcribed, checked against the page, not yet teacher-verified). Only Arabic-script text is scored. CER / WER: lower is better (above 100% = more wrong text than the reference holds); F1: higher is better.

## Overall

| Method | Jawi CER | Jawi WER | Jawi word F1 | Arabic CER (with harakat) | Arabic CER (letters only) | Arabic word F1 | [TIDAK JELAS] | Seconds / page | Cost / page |
|---|---|---|---|---|---|---|---|---|---|
| PyMuPDF text layer | 100.0% | 100.0% | 0.00 | 100.0% | 100.0% | 0.00 | 0 | 0.1 | $0.0000 |
| Tesseract (ara) | 60.8% | 88.7% | 0.20 | 91.8% | 90.6% | 0.03 | 0 | 2.4 | $0.0000 |
| Tesseract (Arabic script) | 65.1% | 85.0% | 0.22 | 93.7% | 92.1% | 0.00 | 0 | 1.6 | $0.0000 |
| Claude Haiku 5.5 vision | 22.4% | 41.0% | 0.69 | 26.1% | 24.5% | 0.48 | 0 | 14.5 | $0.0017 |
| GPT-6 Luna vision | 23.8% | 45.1% | 0.65 | 14.0% | 7.6% | 0.44 | 3 | 29.1 | $0.0016 |

## Jawi CER per subject

| Method | Ibadah | Jawi | Tajwid |
|---|---|---|---|
| PyMuPDF text layer | 100.0% | 100.0% | 100.0% |
| Tesseract (ara) | 58.4% | 52.0% | 72.7% |
| Tesseract (Arabic script) | 57.0% | 70.3% | 76.5% |
| Claude Haiku 5.5 vision | 14.4% | 41.4% | 22.5% |
| GPT-6 Luna vision | 13.3% | 49.0% | 24.1% |

## Jawi CER per kind of page (2.4)

| Method | picture | quran | table | text |
|---|---|---|---|---|
| PyMuPDF text layer | 100.0% | 100.0% | 100.0% | 100.0% |
| Tesseract (ara) | 86.6% | 72.7% | 52.0% | 53.6% |
| Tesseract (Arabic script) | 85.7% | 76.5% | 70.3% | 52.0% |
| Claude Haiku 5.5 vision | 17.6% | 22.5% | 41.4% | 13.8% |
| GPT-6 Luna vision | 16.4% | 24.1% | 49.0% | 12.7% |

## Per note

| Method | Note | Kind | Jawi CER | Jawi F1 | Arabic CER | [TIDAK JELAS] |
|---|---|---|---|---|---|---|
| PyMuPDF text layer | fiqh_b2_fadhilat_puasa | text | 100.0% | 0.00 | 100.0% | 0 |
| PyMuPDF text layer | fiqh_b2_batal_puasa | text | 100.0% | 0.00 | – | 0 |
| PyMuPDF text layer | fiqh_b2_puasa_wajib_sunat | text | 100.0% | 0.00 | – | 0 |
| PyMuPDF text layer | fiqh_b2_hikmah_puasa | picture | 100.0% | 0.00 | – | 0 |
| PyMuPDF text layer | tajwid_b3_mad_iwadh | quran | 100.0% | 0.00 | 100.0% | 0 |
| PyMuPDF text layer | tajwid_b3_mad_silah_qasirah | quran | 100.0% | 0.00 | 100.0% | 0 |
| PyMuPDF text layer | jawi_b4_akronim_dilafaz | table | 100.0% | 0.00 | – | 0 |
| Tesseract (ara) | fiqh_b2_fadhilat_puasa | text | 60.1% | 0.18 | 32.1% | 0 |
| Tesseract (ara) | fiqh_b2_batal_puasa | text | 60.2% | 0.28 | – | 0 |
| Tesseract (ara) | fiqh_b2_puasa_wajib_sunat | text | 36.5% | 0.47 | – | 0 |
| Tesseract (ara) | fiqh_b2_hikmah_puasa | picture | 86.6% | 0.13 | – | 0 |
| Tesseract (ara) | tajwid_b3_mad_iwadh | quran | 72.2% | 0.16 | 100.0% | 0 |
| Tesseract (ara) | tajwid_b3_mad_silah_qasirah | quran | 74.0% | 0.00 | 91.6% | 0 |
| Tesseract (ara) | jawi_b4_akronim_dilafaz | table | 52.0% | 0.22 | – | 0 |
| Tesseract (Arabic script) | fiqh_b2_fadhilat_puasa | text | 61.3% | 0.25 | 38.7% | 0 |
| Tesseract (Arabic script) | fiqh_b2_batal_puasa | text | 46.6% | 0.36 | – | 0 |
| Tesseract (Arabic script) | fiqh_b2_puasa_wajib_sunat | text | 38.1% | 0.42 | – | 0 |
| Tesseract (Arabic script) | fiqh_b2_hikmah_puasa | picture | 85.7% | 0.22 | – | 0 |
| Tesseract (Arabic script) | tajwid_b3_mad_iwadh | quran | 75.9% | 0.16 | 99.7% | 0 |
| Tesseract (Arabic script) | tajwid_b3_mad_silah_qasirah | quran | 78.6% | 0.00 | 97.3% | 0 |
| Tesseract (Arabic script) | jawi_b4_akronim_dilafaz | table | 70.3% | 0.13 | – | 0 |
| Claude Haiku 5.5 vision | fiqh_b2_fadhilat_puasa | text | 17.5% | 0.64 | 34.9% | 0 |
| Claude Haiku 5.5 vision | fiqh_b2_batal_puasa | text | 9.1% | 0.74 | – | 0 |
| Claude Haiku 5.5 vision | fiqh_b2_puasa_wajib_sunat | text | 10.0% | 0.78 | – | 0 |
| Claude Haiku 5.5 vision | fiqh_b2_hikmah_puasa | picture | 17.6% | 0.55 | – | 0 |
| Claude Haiku 5.5 vision | tajwid_b3_mad_iwadh | quran | 19.8% | 0.75 | 19.2% | 0 |
| Claude Haiku 5.5 vision | tajwid_b3_mad_silah_qasirah | quran | 31.1% | 0.63 | 40.9% | 0 |
| Claude Haiku 5.5 vision | jawi_b4_akronim_dilafaz | table | 41.4% | 0.77 | – | 0 |
| GPT-6 Luna vision | fiqh_b2_fadhilat_puasa | text | 16.0% | 0.60 | 2.8% | 0 |
| GPT-6 Luna vision | fiqh_b2_batal_puasa | text | 9.8% | 0.72 | – | 0 |
| GPT-6 Luna vision | fiqh_b2_puasa_wajib_sunat | text | 8.4% | 0.72 | – | 0 |
| GPT-6 Luna vision | fiqh_b2_hikmah_puasa | picture | 16.4% | 0.62 | – | 0 |
| GPT-6 Luna vision | tajwid_b3_mad_iwadh | quran | 23.4% | 0.69 | 16.2% | 0 |
| GPT-6 Luna vision | tajwid_b3_mad_silah_qasirah | quran | 26.0% | 0.74 | 12.1% | 0 |
| GPT-6 Luna vision | jawi_b4_akronim_dilafaz | table | 49.0% | 0.47 | – | 3 |
