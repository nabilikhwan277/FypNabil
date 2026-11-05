# Human vs AI marking by subject (system: proposed:luna:R3:A2:off)

## 1. Agreement (QWK on the 0–4 band, 95% CI)

| | All (n=50) | Ibadah (n=18) | Jawi (n=14) | Tajwid (n=18) |
|---|---|---|---|---|
| Teacher G1 vs G2 | 0.497 [0.256, 0.718] | 0.442 [0.021, 0.736] | 0.644 [0.183, 0.926] | 0.425 [-0.000, 0.792] |
| Teacher G1 vs G3 | 0.516 [0.255, 0.747] | 0.213 [-0.270, 0.668] | 0.675 [0.185, 0.955] | 0.668 [0.292, 0.908] |
| Teacher G2 vs G3 | 0.334 [0.064, 0.569] | 0.172 [-0.364, 0.598] | 0.615 [0.104, 0.935] | 0.276 [-0.147, 0.673] |
| **Teachers (mean of pairs)** | **0.449** | **0.276** | **0.645** | **0.456** |
| System vs G1 | 0.760 [0.572, 0.904] | 0.626 [0.201, 0.907] | 0.695 [0.266, 1.000] | 0.921 [0.793, 1.000] |
| System vs G2 | 0.464 [0.236, 0.676] | 0.536 [0.121, 0.757] | 0.321 [-0.100, 0.762] | 0.526 [0.113, 0.832] |
| System vs G3 | 0.555 [0.304, 0.764] | 0.462 [0.008, 0.821] | 0.366 [-0.046, 0.832] | 0.775 [0.451, 0.974] |
| System vs final marks | 0.755 [0.576, 0.895] | 0.742 [0.458, 0.901] | 0.527 [0.055, 0.908] | 0.947 [0.847, 1.000] |
| **System (mean over teachers)** | **0.593** | **0.541** | **0.461** | **0.741** |

## Criterion level (ya / separa / tidak)

| | All (n=50) | Ibadah (n=18) | Jawi (n=14) | Tajwid (n=18) |
|---|---|---|---|---|
| Teachers: all 3 the same | 35% | 27% | 50% | 33% |
| Teachers: all 3 different | 9 | 5 | 2 | 2 |
| Teachers: Cohen's kappa (mean of pairs) | 0.273 | 0.131 | 0.393 | 0.278 |
| System vs final: agreement | 71% | 69% | 60% | 82% |
| System vs final: Cohen's kappa | 0.509 | 0.462 | 0.328 | 0.696 |

## 2. How often a partial mark (separa) is given

| | All (n=50) | Ibadah (n=18) | Jawi (n=14) | Tajwid (n=18) |
|---|---|---|---|---|
| Teacher G1 | 5% | 4% | 7% | 5% |
| Teacher G2 | 25% | 29% | 13% | 28% |
| Teacher G3 | 19% | 9% | 33% | 20% |
| final | 17% | 18% | 17% | 15% |
| system | 3% | 2% | 0% | 5% |

## 3. Where the system differs from the final marks (number of criteria)

| | All (n=50) | Ibadah (n=18) | Jawi (n=14) | Tajwid (n=18) |
|---|---|---|---|---|
| more lenient (LLM) | 15 | 8 | 3 | 4 |
| stricter (LLM) | 12 | 6 | 3 | 3 |
| stricter (hard rule) | 6 | 0 | 6 | 0 |
| **Total** | **33 of 114** | **14 of 45** | **12 of 30** | **7 of 39** |

## Examples (criteria where the system and the final marks differ)

### Ibadah

**T008** · Nyatakan tiga fadhilat solat istikharah.
- Pupil answer: 1. Hati jadi aman dan tak risau. 2. Kita tak jadi bongkak. 3. Kita percaya apa yang Allah dah tetapkan untuk kita, jadi akidah terjaga.
- Criterion: Memberi ketenangan kepada hati
- Teachers: G1 separa, G2 separa, G3 separa → final **separa** · System: **ya** (more lenient, llm)
- System's reason: Hati menjadi aman dan tidak risau membawa maksud hati mendapat ketenangan.
- Comment G2: boleh diterima, tapi seeloknya jawapan sebijik didalam buku
- Comment G3: Setiap jawapan mesti sama dengan buku teks/skema jawapan

**T008** · Nyatakan tiga fadhilat solat istikharah.
- Pupil answer: 1. Hati jadi aman dan tak risau. 2. Kita tak jadi bongkak. 3. Kita percaya apa yang Allah dah tetapkan untuk kita, jadi akidah terjaga.
- Criterion: Menghilangkan sifat sombong
- Teachers: G1 tidak, G2 separa, G3 separa → final **separa** · System: **ya** (more lenient, llm)
- System's reason: Tidak menjadi bongkak bermaksud menghilangkan sifat sombong.
- Comment G2: boleh diterima, tapi seeloknya jawapan sebijik didalam buku
- Comment G3: Setiap jawapan mesti sama dengan buku teks/skema jawapan

**T008** · Nyatakan tiga fadhilat solat istikharah.
- Pupil answer: 1. Hati jadi aman dan tak risau. 2. Kita tak jadi bongkak. 3. Kita percaya apa yang Allah dah tetapkan untuk kita, jadi akidah terjaga.
- Criterion: Menjaga akidah / yakin dengan ketentuan Allah
- Teachers: G1 ya, G2 separa, G3 separa → final **separa** · System: **ya** (more lenient, llm)
- System's reason: Percaya pada ketetapan Allah menunjukkan akidah terjaga dan yakin dengan ketentuan-Nya.
- Comment G2: boleh diterima, tapi seeloknya jawapan sebijik didalam buku
- Comment G3: Setiap jawapan mesti sama dengan buku teks/skema jawapan

**T010** · Apakah maksud wiladah?
- Pupil answer: Darah yang keluar dari perempuan lepas ada anak.
- Criterion: Menyatakan melahirkan anak
- Teachers: G1 separa, G2 ya, G3 ya → final **ya** · System: **separa** (stricter, llm)
- System's reason: Mengaitkan wiladah dengan selepas mempunyai anak, tetapi maksudnya bukan darah yang keluar.
- Comment G2: betul dan sama maksud

**T012** · Bilakah waktu solat witir?
- Pupil answer: Sebelum solat isyak sampai terbit fajar.
- Criterion: Hingga terbit fajar
- Teachers: G1 tidak, G2 tidak, G3 ya → final **tidak** · System: **ya** (more lenient, llm)
- System's reason: Murid menyatakan waktu witir hingga terbit fajar.

**T013** · Apakah hukum puasa? Jelaskan.
- Pupil answer: Hukum puasa semuanya wajib, tiada puasa yang sunat.
- Criterion: Menyatakan wajib
- Teachers: G1 tidak, G2 separa, G3 tidak → final **tidak** · System: **ya** (more lenient, llm)
- System's reason: Menyatakan puasa wajib.
- Comment G2: kena sertakan lebih perinci akan puasa apa yg hendak ditanya. contoh apakah contoh puasa sunat?

### Jawi

**T001** · Kenapakah ejaan 'pakaian' menggunakan huruf 'ن' sahaja bagi imbuhan '-an'? Tuliskan juga ejaan Jawinya.
- Pupil answer: Sebab pakai habis dengan huruf ya. Ejaan ڤاكاءين
- Criterion: Menyatakan peraturan: ditulis dengan 'ن' sahaja
- Teachers: G1 separa, G2 separa, G3 separa → final **separa** · System: **tidak** (stricter, llm)
- System's reason: Tidak menyatakan imbuhan -an ditulis dengan huruf ن sahaja.
- Comment G2: T001 K2

**T003** · Tulis perkataan 'kesilauan' dalam tulisan Jawi.
- Pupil answer: كسيلاون
- Criterion: Mengeja 'kesilauan' dengan betul (كسيلاوان)
- Teachers: G1 tidak, G2 separa, G3 ya → final **separa** · System: **tidak** (stricter, rule)
- System's reason: ejaan Jawi dibandingkan tepat

**T011** · Jawikan perkataan bergaris: Doktor Fahmi bertugas di Hospital Kuala Lumpur (HKL) sebagai pakar ortopedik. Tulis ejaan Jawi bagi 'Doktor'.
- Pupil answer: Doktor
- Criterion: Mengeja دوكتور dalam ejaan penuh
- Teachers: G1 ya, G2 ya, G3 ya → final **ya** · System: **tidak** (stricter, rule)
- System's reason: ejaan Jawi dibandingkan tepat
- Comment G2: betui. Murid kena pastikan perkataan itu dalam pinjaman bahasa inggeris / arab

**T027** · Apakah yang terdapat di Mardi Agroteknologi Park?
- Pupil answer: Kat situ ada banyak jenis bunga ros, buah strawberi dan macam-macam buah lain.
- Criterion: Menyebut bunga ros
- Teachers: G1 ya, G2 separa, G3 separa → final **separa** · System: **ya** (more lenient, llm)
- System's reason: Murid menyebut bunga ros.

**T027** · Apakah yang terdapat di Mardi Agroteknologi Park?
- Pupil answer: Kat situ ada banyak jenis bunga ros, buah strawberi dan macam-macam buah lain.
- Criterion: Menyebut strawberi / buah-buahan
- Teachers: G1 ya, G2 separa, G3 separa → final **separa** · System: **ya** (more lenient, llm)
- System's reason: Murid menyebut buah strawberi dan macam-macam buah lain.

**T041** · Terangkan cara mengeja imbuhan '-i' dengan huruf '-ي'. Dalam jawapan anda, jelaskan maksud suku kata tertutup, vokal yang terlibat, dan tukarkan kata dasar 'marah', 'bayang' dan 'ubat' kepada kata berimbuhan '-i' seperti dalam buku (dimarahi, dibayangi, ubati) dalam tulisan Jawi.
- Pupil answer: ايمبوهن -i دتوليس دڠن همزة دان ي (ءي). سوكو كات ترتوتوڤ اياله سوكو كات يڠ هابيس دڠن ۏوكل. دمارهءي، دبايڠءي، اوبتءي
- Criterion: Peraturan: dieja dengan huruf '-ي' sahaja
- Teachers: G1 ya, G2 ya, G3 ya → final **ya** · System: **tidak** (stricter, rule)
- System's reason: ejaan Jawi dibandingkan tepat

### Tajwid

**T019** · Terangkan kepentingan mempelajari tingkatan mad. Jelaskan dengan contoh kalimah yang diberikan dalam buku.
- Pupil answer: Kita kena ikut tingkatan yang paling rendah. Contohnya مِمَّا يَشَآءُ ketika waqaf ada Mad 'Aridh Lissukun dan Mad Wajib Muttasil, jadi kita baca ikut Mad 'Aridh Lissukun.
- Criterion: Contoh kalimah مِمَّا يَشَآءُ ketika waqaf
- Teachers: G1 ya, G2 tidak, G3 tidak → final **tidak** · System: **ya** (more lenient, llm)
- System's reason: Contoh مِمَّا يَشَآءُ ketika waqaf dinyatakan dengan betul.

**T019** · Terangkan kepentingan mempelajari tingkatan mad. Jelaskan dengan contoh kalimah yang diberikan dalam buku.
- Pupil answer: Kita kena ikut tingkatan yang paling rendah. Contohnya مِمَّا يَشَآءُ ketika waqaf ada Mad 'Aridh Lissukun dan Mad Wajib Muttasil, jadi kita baca ikut Mad 'Aridh Lissukun.
- Criterion: Menyebut dua hukum: Mad 'Aridh Lissukun dan Mad Wajib Muttasil
- Teachers: G1 ya, G2 tidak, G3 separa → final **separa** · System: **ya** (more lenient, llm)
- System's reason: Kedua-dua hukum Mad 'Aridh Lissukun dan Mad Wajib Muttasil disebut.

**T022** · Nyatakan kadar panjang bacaan Mad Wajib Muttasil.
- Pupil answer: 4 atau 5 harakat, kadang-kadang boleh lagi panjang.
- Criterion: Empat atau lima harakat
- Teachers: G1 ya, G2 separa, G3 separa → final **separa** · System: **ya** (more lenient, llm)
- System's reason: Menyatakan kadar empat atau lima harakat dengan betul.

**T022** · Nyatakan kadar panjang bacaan Mad Wajib Muttasil.
- Pupil answer: 4 atau 5 harakat, kadang-kadang boleh lagi panjang.
- Criterion: Keadaan: hamzah di tengah/hujung kalimah, wasal atau waqaf
- Teachers: G1 tidak, G2 separa, G3 ya → final **separa** · System: **tidak** (stricter, llm)
- System's reason: Tidak menyatakan keadaan hamzah atau bacaan wasal dan waqaf.

**T022** · Nyatakan kadar panjang bacaan Mad Wajib Muttasil.
- Pupil answer: 4 atau 5 harakat, kadang-kadang boleh lagi panjang.
- Criterion: Keadaan: hamzah di hujung kalimah, waqaf sahaja
- Teachers: G1 tidak, G2 separa, G3 separa → final **separa** · System: **tidak** (stricter, llm)
- System's reason: Tidak menyatakan hamzah di hujung kalimah ketika waqaf sahaja.

**T028** · Berikan pengertian Mad 'Iwadh.
- Pupil answer: برهنتي ڤد ڤركاتاٴن يڠ اد تنوين.
- Criterion: Berbaris tanwin di atas
- Teachers: G1 tidak, G2 ya, G3 ya → final **ya** · System: **separa** (stricter, llm)
- System's reason: Menyebut tanwin, tetapi tidak menyatakan tanwin di atas.

