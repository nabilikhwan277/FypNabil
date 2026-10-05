# Soal Selidik Kebolehgunaan (SUS) | System Usability Scale

Untuk murid Tahun 5 atau guru selepas menggunakan Intelligent KAFA UPKK Learning Assistant sekurang-kurangnya 10 minit
(cuba sekurang-kurangnya satu topik bagi setiap subjek). Bagi murid, guru boleh membacakan soalan.

**Skala:** 1 = Sangat tidak setuju · 2 = Tidak setuju · 3 = Tidak pasti · 4 = Setuju · 5 = Sangat setuju

| No. | Pernyataan | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|---|
| 1 | Saya rasa saya mahu selalu menggunakan sistem ini. | | | | | |
| 2 | Sistem ini susah dan berbelit-belit. | | | | | |
| 3 | Sistem ini mudah digunakan. | | | | | |
| 4 | Saya perlukan bantuan orang lain untuk menggunakan sistem ini. | | | | | |
| 5 | Bahagian-bahagian sistem ini (nota, soalan, maklum balas) berfungsi dengan baik bersama. | | | | | |
| 6 | Banyak perkara dalam sistem ini yang tidak konsisten / mengelirukan. | | | | | |
| 7 | Saya rasa kebanyakan murid boleh belajar menggunakan sistem ini dengan cepat. | | | | | |
| 8 | Sistem ini menyusahkan untuk digunakan. | | | | | |
| 9 | Saya yakin semasa menggunakan sistem ini. | | | | | |
| 10 | Saya perlu belajar banyak perkara sebelum boleh menggunakan sistem ini. | | | | | |

**Soalan tambahan (tidak termasuk dalam skor SUS):**
- A. Maklum balas sistem membantu saya faham kesilapan saya. (1–5)
- B. Papan kekunci Jawi mudah digunakan. (1–5)
- C. Apa yang paling kamu suka? Apa yang perlu diperbaiki? (jawapan bertulis)

Peranan: ☐ Murid ☐ Guru · Kelas: ______ · Tarikh: ______

## Cara mengira (untuk pengkaji)
Masukkan jawapan ke dalam `docs/sus_responses.csv` (lajur `respondent,role,q1..q10,a,b,comment`),
kemudian jalankan:

```
.venv\Scripts\python scripts\sus_score.py docs\sus_responses.csv
```

Skor SUS = 2.5 × [ Σ(soalan ganjil − 1) + Σ(5 − soalan genap) ], julat 0–100.
Purata ≥ 68 dianggap di atas purata; ≥ 80 dianggap baik.
