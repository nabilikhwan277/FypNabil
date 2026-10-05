# Scoring sanity check (train split, synthetic answers)

| Case | Group | n | Mean % | Full marks | Zero | LLM calls/answer | Median ms | p95 ms |
|---|---|---|---|---|---|---|---|---|
| correct_rumi | all | 256 | 98.8 | 0.965 | 0.000 | 0.03 | 61 | 179 |
| correct_rumi | fiqh | 90 | 99.3 | 0.978 | 0.000 | 0.02 | 58 | 194 |
| correct_rumi | jawi | 41 | 94.1 | 0.829 | 0.000 | 0.07 | 74 | 170 |
| correct_rumi | tajwid | 125 | 100.0 | 1.000 | 0.000 | 0.02 | 61 | 144 |
| correct_rumi | L1 | 126 | 100.0 | 1.000 | 0.000 | 0.0 | 55 | 66 |
| correct_rumi | L2 | 92 | 97.7 | 0.946 | 0.000 | 0.05 | 74 | 144 |
| correct_rumi | L3 | 38 | 97.4 | 0.895 | 0.000 | 0.08 | 144 | 264 |
| correct_jawi | all | 306 | 99.3 | 0.971 | 0.000 | 0.02 | 59 | 157 |
| correct_jawi | fiqh | 90 | 99.3 | 0.967 | 0.000 | 0.03 | 59 | 181 |
| correct_jawi | jawi | 91 | 99.0 | 0.956 | 0.000 | 0.02 | 58 | 153 |
| correct_jawi | tajwid | 125 | 99.5 | 0.984 | 0.000 | 0.02 | 59 | 148 |
| correct_jawi | L1 | 163 | 100.0 | 1.000 | 0.000 | 0.0 | 55 | 64 |
| correct_jawi | L2 | 105 | 98.8 | 0.962 | 0.000 | 0.03 | 72 | 126 |
| correct_jawi | L3 | 38 | 97.4 | 0.868 | 0.000 | 0.11 | 149 | 906 |
| wrong | all | 306 | 2.6 | 0.010 | 0.944 | 1.4 | 63 | 4557 |
| wrong | fiqh | 90 | 3.0 | 0.011 | 0.944 | 1.42 | 66 | 3825 |
| wrong | jawi | 91 | 0.5 | 0.000 | 0.978 | 0.9 | 60 | 4009 |
| wrong | tajwid | 125 | 3.8 | 0.016 | 0.920 | 1.74 | 81 | 4155 |
| wrong | L1 | 163 | 0.6 | 0.006 | 0.994 | 0.0 | 56 | 70 |
| wrong | L2 | 105 | 4.7 | 0.019 | 0.914 | 2.59 | 2047 | 6353 |
| wrong | L3 | 38 | 5.3 | 0.000 | 0.816 | 4.08 | 3096 | 7538 |

## Layer usage

- **correct_rumi**: A-keyword 554, A-spelling 49, A-truefalse 8, B-guard 4, B-llm 4
- **correct_jawi**: A-keyword 555, A-spelling 130, A-truefalse 8, B-guard 7
- **wrong**: B-guard 388, A-none 140, A-spelling 130, A-keyword 18, B-fallback 9, A-truefalse 8, B-llm 7

## Raw LLM judge verdicts (before guard)

- **correct_rumi**: ya 8
- **correct_jawi**: ya 7
- **wrong**: None 9, separa 1, ya 394

## correct_not_full (18 shown)

- `fiqh_b1_solat_dhuha_q6` correct_rumi 66.7% layers=['A-keyword', 'B-guard', 'A-keyword'] missed=['Keadaan kedua yang betul']
- `fiqh_b1_solat_dhuha_q6` correct_jawi 66.7% layers=['A-keyword', 'B-guard', 'A-keyword'] missed=['Keadaan kedua yang betul']
- `fiqh_b1_solat_gerhana_q7` correct_jawi 83.3% layers=['A-keyword', 'A-keyword', 'A-keyword', 'A-keyword', 'A-keyword', 'B-guard'] missed=['Rukuk dan sujud dalam tempoh yang lama']
- `fiqh_b1_solat_hari_raya_q5` correct_rumi 66.7% layers=['A-keyword', 'A-keyword', 'B-guard'] missed=['Mana-mana fadhilat ketiga yang betul']
- `fiqh_b1_solat_witir_q6` correct_jawi 83.3% layers=['A-keyword', 'A-keyword', 'A-keyword', 'B-guard'] missed=['Satu fadhilat']
- `jawi_b1_imbuhan_an_alif_nun_q7` correct_rumi 66.7% layers=['A-keyword', 'A-keyword', 'A-spelling', 'A-keyword', 'A-spelling'] missed=["Ayat contoh mengandungi kata '-ان' yang dieja betul (cth. ڤالوان, دروان, ڤرݢوروان, كسيلاوان, ݢوراوان)"]
- `jawi_b1_imbuhan_an_nun_q5` correct_rumi 50.0% layers=['A-keyword', 'A-spelling', 'A-keyword', 'A-spelling'] missed=['Contoh betul bagi jenis pertama (cth. ڤوجين, تارين, بلاين, ڤاكاين)', 'Contoh betul bagi jenis kedua (cth. سوكتن, تاڤيسن, سبوتن, كأخلاصن)']
- `jawi_b2_imbuhan_i_hamzah_ya_q8` correct_rumi 83.3% layers=['A-keyword', 'A-spelling', 'B-llm', 'A-spelling', 'A-keyword', 'B-guard'] missed=['Kumpulan 2: hukum ک dan ݢ']
- `jawi_b2_imbuhan_i_hamzah_ya_q8` correct_jawi 83.3% layers=['A-keyword', 'A-spelling', 'B-guard', 'A-spelling', 'A-keyword', 'A-keyword'] missed=["Peraturan dikatai: letak 'ا' terlebih dahulu diikuti '-ءي'"]
- `jawi_b2_imbuhan_i_ya_q9` correct_rumi 33.3% layers=['A-keyword', 'A-spelling', 'A-spelling'] missed=['Kata kedua betul dari syair', 'Kata ketiga betul dari syair']
- `jawi_b3_pinjaman_inggeris_q9` correct_rumi 66.7% layers=['A-keyword', 'A-spelling', 'A-keyword', 'A-spelling', 'A-keyword', 'A-spelling'] missed=['Contoh betul bagi kaedah kedua', 'Contoh betul bagi kaedah ketiga']
- `jawi_b3_pinjaman_inggeris_q9` correct_jawi 66.7% layers=['A-keyword', 'A-spelling', 'A-keyword', 'A-spelling', 'A-keyword', 'A-spelling'] missed=['Contoh betul bagi kaedah kedua', 'Contoh betul bagi kaedah ketiga']
- `jawi_b4_akronim_inggeris_q8` correct_rumi 83.3% layers=['B-guard', 'A-keyword', 'A-keyword', 'A-keyword', 'A-spelling', 'A-spelling'] missed=['Menyatakan cara penulisan kedua-dua bahasa berbeza']
- `jawi_b4_akronim_inggeris_q8` correct_jawi 83.3% layers=['A-keyword', 'A-keyword', 'A-keyword', 'B-guard', 'A-spelling', 'A-spelling'] missed=['Menyebut bahasa Melayu menggunakan huruf abjad Jawi']
- `jawi_b4_akronim_melayu_q7` correct_rumi 75.0% layers=['A-keyword', 'A-keyword', 'A-spelling', 'A-spelling'] missed=['Contoh kedua betul']
- `jawi_b4_akronim_melayu_q7` correct_jawi 75.0% layers=['A-keyword', 'A-keyword', 'A-spelling', 'A-spelling'] missed=['Contoh kedua betul']
- `tajwid_b1_mad_bahagian_q7` correct_jawi 66.7% layers=['A-keyword', 'A-keyword', 'B-guard'] missed=['Menyatakan mad terbahagi kepada dua']
- `tajwid_b3_mad_farq_q4` correct_jawi 66.7% layers=['A-keyword', 'B-guard', 'A-keyword'] missed=['Di permulaan kalimah']

## wrong_not_zero (17 shown)

- `fiqh_b1_solat_tahajud_q1` wrong 100.0% layers=['A-keyword'] missed=[]
- `fiqh_b1_solat_tarawih_q5` wrong 66.7% layers=['A-keyword', 'B-guard'] missed=['Maksud niat']
- `fiqh_b1_solat_tarawih_q6` wrong 33.3% layers=['B-guard', 'B-guard', 'B-guard', 'B-llm'] missed=['Menyatakan solat bersama imam hingga imam selesai', 'Ganjaran qiam semalaman / bersolat sepanjang malam', 'Menasihati Ali menunggu hingga selesai']
- `fiqh_b1_solat_taubat_q6` wrong 50.0% layers=['A-keyword', 'B-guard', 'A-keyword', 'B-guard'] missed=['Waktu: apabila berazam untuk bertaubat', 'Dua fadhilat']
- `fiqh_b2_pengertian_puasa_q7` wrong 16.7% layers=['B-guard', 'A-keyword', 'B-guard', 'B-guard', 'B-guard', 'B-guard'] missed=['Menahan diri daripada makan, minum dan perkara yang membatalkan', 'Seruan kepada orang yang beriman', 'Diwajibkan berpuasa', 'Sebagaimana diwajibkan atas umat sebelum', 'Supaya bertakwa']
- `jawi_b1_imbuhan_an_nun_q7` wrong 16.7% layers=['A-spelling', 'B-guard', 'A-keyword', 'B-guard', 'A-spelling', 'A-spelling'] missed=["Kata dasar berakhir dengan huruf '-ي'", "Menyebut suku kata terbuka dengan vokal 'i' dan diftong 'ai'", "Menyebut vokal 'a', 'i', 'e' taling, 'u', 'o'", 'Mengeja belaian: بلاين', 'Mengeja tapisan: تاڤيسن']
- `jawi_b2_imbuhan_i_ya_q7` wrong 33.3% layers=['A-keyword', 'B-guard', 'B-guard'] missed=["Menyebut vokal 'i'", "Menyebut vokal 'u'"]
- `tajwid_b3_mad_aridh_lissukun_q4` wrong 33.3% layers=['A-keyword', 'B-guard', 'B-guard'] missed=['Bertemu dengan huruf mati', 'Kerana waqaf (berhenti bacaan)']
- `tajwid_b3_mad_fari_pengenalan_q5` wrong 100.0% layers=['B-llm', 'B-llm', 'B-llm', 'B-llm'] missed=[]
- `tajwid_b3_mad_fari_pengenalan_q7` wrong 16.7% layers=['B-guard', 'B-guard', 'B-llm', 'B-guard'] missed=['Bahagian pertama: hamzah sebelum atau selepas huruf mad', 'Dua contoh hukum bahagian pertama', 'Dua contoh hukum bahagian kedua']
- `tajwid_b3_mad_jaiz_munfasil_q4` wrong 25.0% layers=['B-guard', 'B-guard', 'B-guard', 'B-llm'] missed=['Ulama qiraat mengharuskan dibaca dua harakat atau lebih', 'Riwayat Hafs: empat atau lima harakat', 'Munfasil: berpisah']
- `tajwid_b3_mad_lazim_harfi_mukhaffaf_q7` wrong 25.0% layers=['B-guard', 'A-keyword', 'B-guard', 'B-guard'] missed=['Mad = memanjangkan bacaan', 'Harfi = satu huruf', 'Mukhaffaf = tidak diidghamkan']
- `tajwid_b3_mad_lazim_harfi_mukhaffaf_q8` wrong 33.3% layers=['A-keyword', 'B-guard', 'B-guard', 'B-guard'] missed=['Cara bacaan: tanpa idgham dan tanpa dengung', 'Kadar enam harakat', 'Dua misal yang betul beserta surah']
- `tajwid_b3_mad_lazim_harfi_muthaqqal_q5` wrong 100.0% layers=['A-keyword', 'A-keyword', 'A-keyword'] missed=[]
- `tajwid_b3_mad_lazim_kalimi_mukhaffaf_q8` wrong 33.3% layers=['A-keyword', 'B-guard', 'B-guard', 'B-guard'] missed=['Hukum tanpa idgham dan kadar enam harakat', 'Tempat: Surah Yunus ayat 51 dan 91', 'Contoh ayat yang betul']
- `tajwid_b3_mad_lazim_kalimi_muthaqqal_q6` wrong 75.0% layers=['A-keyword', 'A-keyword', 'B-guard', 'A-keyword'] missed=['Kalimi = satu kalimah']
- `tajwid_b3_mad_lin_q4` wrong 33.3% layers=['B-guard', 'B-guard', 'A-keyword'] missed=['Menyebut huruf lin', 'Bertemu dengan huruf mati']
