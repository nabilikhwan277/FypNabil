# Why the RAG types failed (a failure = declined, or factual correctness < 0.5)

| RAG type | Cause | All | Ibadah | Jawi | Tajwid |
|---|---|---|---|---|---|
| **R1** | **failed / questions** | **8 / 45** | **3 / 15** | **2 / 15** | **3 / 15** |
| | limit cut | 4 | 0 | 2 | 2 |
| | partly found | 4 | 3 | 0 | 1 |
| **R2** | **failed / questions** | **10 / 45** | **4 / 15** | **2 / 15** | **4 / 15** |
| | limit cut | 3 | 0 | 2 | 1 |
| | partly found | 7 | 4 | 0 | 3 |
| **R3** | **failed / questions** | **6 / 45** | **3 / 15** | **0 / 15** | **3 / 15** |
| | limit cut | 1 | 0 | 0 | 1 |
| | partly found | 5 | 3 | 0 | 2 |

Causes: *limit cut* = the evidence was retrieved but dropped by the context limit; *wrong section* = retrieval missed it; *partly found* = the answer is spread over sections and only some were read; *answer model* = everything was read but the answer was declined or wrong.

## Examples

### R1

- **fiqh_b1_solat_witir_q6** (partly found; evidence read 70%; 4 of 4 read; declined): Aminah ingin mendirikan solat witir tiga rakaat iaitu dua rakaat dan diikuti satu rakaat. Terangkan pengertian solat witir, tuliskan kedua-dua lafaz niat yang perlu digunakannya beserta maksud, dan nyatakan satu fadhilat solat witir.
  - Answer: Data ini tiada dalam pangkalan data saya.
  - Reference: Solat witir didirikan selepas solat isyak hingga terbit fajar; witir ertinya ganjil; bilangannya 1, 3, 5, 7, 9 atau 11 rakaat. Niat dua rakaat: أُصَلِّي سُنَّةَ ٱلْوِتْرِ رَكْعَتَيْنِ لِلَّهِ تَعَالَى
- **fiqh_b1_solat_gerhana_q7** (partly found; evidence read 6%; 2 of 4 read; declined): Pada suatu malam berlaku gerhana bulan. Terangkan solat yang disunatkan pada ketika itu dari segi pengertian, lafaz niat, dan cara pelaksanaan rakaat pertamanya yang membezakannya daripada solat sunat biasa.
  - Answer: Data ini tiada dalam pangkalan data saya.
  - Reference: Solat gerhana bulan (khusuf) ialah solat yang didirikan kerana terjadinya gerhana, sebanyak dua rakaat dengan empat rukuk dan empat sujud, secara berjemaah atau bersendirian. Niat: أُصَلِّي سُنَّةَ ٱل
- **fiqh_b2_puasa_wajib_sunat_q6** (partly found; evidence read 67%; 2 of 4 read; declined): Bezakan puasa wajib dan puasa sunat dengan memberikan dua contoh bagi setiap satu. Kemudian terangkan siapakah yang disunatkan berpuasa pada 9 Zulhijjah.
  - Answer: Data ini tiada dalam pangkalan data saya.
  - Reference: Hukum puasa wajib atau sunat bergantung pada jenis puasa. Contoh puasa wajib: puasa Ramadan, qada, kafarah, nazar. Contoh puasa sunat: enam hari Syawal, Isnin dan Khamis, Tasu'a dan Asyura, Nisfu Syaa
- **jawi_b2_imbuhan_i_hamzah_ya_q5** (limit cut; evidence read 0%; 1 of 4 read; declined): Huruf apakah digunakan untuk mengeja imbuhan '-i' pada suku kata terbuka dengan vokal 'a' dan 'u'?
  - Answer: Data ini tiada dalam pangkalan data saya.
  - Reference: Huruf '-ءي' (hamzah ya)
- **jawi_b1_imbuhan_an_nun_q11** (limit cut; evidence read 0%; 1 of 4 read; declined): Apakah yang terdapat di Mardi Agroteknologi Park?
  - Answer: Data ini tiada dalam pangkalan data saya.
  - Reference: Pelbagai jenis bunga ros, strawberi dan pelbagai jenis buah-buahan
- **tajwid_b3_mad_tazim_q7** (partly found; evidence read 17%; 3 of 4 read; declined): Terangkan hukum Mad Ta'zim meliputi pengertian, kadar harakat dan sebab dinamakan, serta berikan satu contoh ayat al-Quran beserta nama surah dan nombor ayatnya.
  - Answer: Data ini tiada dalam pangkalan data saya.
  - Reference: Mad Ta'zim ialah apabila terdapat kalimah لَآ yang menunjukkan penafian bertemu dengan kalimah إِلَٰهَ. Kadarnya empat atau lima harakat. Dinamakan Mad Ta'zim kerana membesar dan memuliakan Allah. Con
- **tajwid_b3_mad_lin_q2** (limit cut; evidence read 0%; 1 of 4 read; declined): Bilakah berlakunya hukum Mad Lin?
  - Answer: Data ini tiada dalam pangkalan data saya.
  - Reference: Hanya ketika mewaqafkan ayat
- **tajwid_b5_waqaf_q7** (limit cut; evidence read 0%; 1 of 4 read; declined): Apakah maksud waqaf berikut: Hasan, Qabih, Kafi?
  - Answer: Data ini tiada dalam pangkalan data saya.
  - Reference: Waqaf Hasan: menghentikan bacaan pada tempat yang masih tergantung dari segi lafaz dan makna tetapi boleh difahami. Waqaf Qabih: menghentikan bacaan pada tempat yang tidak difahami ertinya atau boleh 

### R2

- **fiqh_b1_solat_witir_q6** (partly found; evidence read 70%; 3 of 4 read; declined): Aminah ingin mendirikan solat witir tiga rakaat iaitu dua rakaat dan diikuti satu rakaat. Terangkan pengertian solat witir, tuliskan kedua-dua lafaz niat yang perlu digunakannya beserta maksud, dan nyatakan satu fadhilat solat witir.
  - Answer: Data ini tiada dalam pangkalan data saya.
  - Reference: Solat witir didirikan selepas solat isyak hingga terbit fajar; witir ertinya ganjil; bilangannya 1, 3, 5, 7, 9 atau 11 rakaat. Niat dua rakaat: أُصَلِّي سُنَّةَ ٱلْوِتْرِ رَكْعَتَيْنِ لِلَّهِ تَعَالَى
- **fiqh_b1_solat_taubat_q6** (partly found; evidence read 44%; 2 of 4 read; declined): Seorang rakan anda menyesal atas dosa yang telah dilakukannya. Terangkan kepadanya pengertian solat taubat, waktu yang digalakkan untuk mendirikannya, lafaz niatnya dan dua fadhilatnya.
  - Answer: Data ini tiada dalam pangkalan data saya.
  - Reference: Solat taubat didirikan dua rakaat ketika seseorang ingin bertaubat kepada Allah SWT atas segala dosa. Digalakkan apabila telah berazam untuk bertaubat, sebaik-baiknya sebelum bertaubat kepada Allah SW
- **fiqh_b1_solat_gerhana_q7** (partly found; evidence read 72%; 1 of 4 read; declined): Pada suatu malam berlaku gerhana bulan. Terangkan solat yang disunatkan pada ketika itu dari segi pengertian, lafaz niat, dan cara pelaksanaan rakaat pertamanya yang membezakannya daripada solat sunat biasa.
  - Answer: Data ini tiada dalam pangkalan data saya.
  - Reference: Solat gerhana bulan (khusuf) ialah solat yang didirikan kerana terjadinya gerhana, sebanyak dua rakaat dengan empat rukuk dan empat sujud, secara berjemaah atau bersendirian. Niat: أُصَلِّي سُنَّةَ ٱل
- **fiqh_b2_puasa_wajib_sunat_q6** (partly found; evidence read 58%; 2 of 4 read; declined): Bezakan puasa wajib dan puasa sunat dengan memberikan dua contoh bagi setiap satu. Kemudian terangkan siapakah yang disunatkan berpuasa pada 9 Zulhijjah.
  - Answer: Data ini tiada dalam pangkalan data saya.
  - Reference: Hukum puasa wajib atau sunat bergantung pada jenis puasa. Contoh puasa wajib: puasa Ramadan, qada, kafarah, nazar. Contoh puasa sunat: enam hari Syawal, Isnin dan Khamis, Tasu'a dan Asyura, Nisfu Syaa
- **jawi_b2_imbuhan_i_hamzah_ya_q10** (limit cut; evidence read 0%; 1 of 4 read; declined): Apakah jenis roket yang digunakan oleh angkasawan negara?
  - Answer: Data ini tiada dalam pangkalan data saya.
  - Reference: Roket Soyuz TMA-11
- **jawi_b1_imbuhan_an_nun_q11** (limit cut; evidence read 0%; 1 of 4 read; declined): Apakah yang terdapat di Mardi Agroteknologi Park?
  - Answer: Data ini tiada dalam pangkalan data saya.
  - Reference: Pelbagai jenis bunga ros, strawberi dan pelbagai jenis buah-buahan
- **tajwid_b3_mad_lazim_harfi_muthaqqal_q8** (partly found; evidence read 22%; 1 of 4 read; declined): Terangkan Mad Lazim Harfi Muthaqqal meliputi pengertian, cara bacaan dan maksud setiap perkataan pada namanya, serta berikan satu misal beserta nama surahnya.
  - Answer: Data ini tiada dalam pangkalan data saya.
  - Reference: Mad Lazim Harfi Muthaqqal ialah apabila huruf mad bertemu dengan huruf mati dalam satu huruf di permulaan surah (fawatih al-suwar) dan diidghamkan ke dalam huruf berikutnya. Ia dibaca dengan idgham be
- **tajwid_b3_mad_tazim_q7** (partly found; evidence read 67%; 3 of 4 read; declined): Terangkan hukum Mad Ta'zim meliputi pengertian, kadar harakat dan sebab dinamakan, serta berikan satu contoh ayat al-Quran beserta nama surah dan nombor ayatnya.
  - Answer: Data ini tiada dalam pangkalan data saya.
  - Reference: Mad Ta'zim ialah apabila terdapat kalimah لَآ yang menunjukkan penafian bertemu dengan kalimah إِلَٰهَ. Kadarnya empat atau lima harakat. Dinamakan Mad Ta'zim kerana membesar dan memuliakan Allah. Con
- **tajwid_b5_waqaf_q7** (limit cut; evidence read 0%; 1 of 4 read; declined): Apakah maksud waqaf berikut: Hasan, Qabih, Kafi?
  - Answer: Data ini tiada dalam pangkalan data saya.
  - Reference: Waqaf Hasan: menghentikan bacaan pada tempat yang masih tergantung dari segi lafaz dan makna tetapi boleh difahami. Waqaf Qabih: menghentikan bacaan pada tempat yang tidak difahami ertinya atau boleh 
- **tajwid_b3_mad_tamkin_q6** (partly found; evidence read 71%; 3 of 4 read; declined): Terangkan hukum Mad Tamkin meliputi pengertian dan kadar harakatnya, serta nyatakan dua kalimah Mad Tamkin beserta nama surah dan nombor ayatnya.
  - Answer: Data ini tiada dalam pangkalan data saya.
  - Reference: Mad Tamkin ialah apabila bertemu dua huruf ya di dalam satu kalimah, ya pertama berbaris bawah dan bertasydid manakala ya kedua mati. Kadarnya dua harakat dan ia termasuk dalam bahagian Mad Asli. Cont

### R3

- **fiqh_b1_solat_witir_q6** (partly found; evidence read 70%; 3 of 3 read; declined): Aminah ingin mendirikan solat witir tiga rakaat iaitu dua rakaat dan diikuti satu rakaat. Terangkan pengertian solat witir, tuliskan kedua-dua lafaz niat yang perlu digunakannya beserta maksud, dan nyatakan satu fadhilat solat witir.
  - Answer: Data ini tiada dalam pangkalan data saya.
  - Reference: Solat witir didirikan selepas solat isyak hingga terbit fajar; witir ertinya ganjil; bilangannya 1, 3, 5, 7, 9 atau 11 rakaat. Niat dua rakaat: أُصَلِّي سُنَّةَ ٱلْوِتْرِ رَكْعَتَيْنِ لِلَّهِ تَعَالَى
- **fiqh_b1_solat_taubat_q6** (partly found; evidence read 56%; 3 of 3 read; declined): Seorang rakan anda menyesal atas dosa yang telah dilakukannya. Terangkan kepadanya pengertian solat taubat, waktu yang digalakkan untuk mendirikannya, lafaz niatnya dan dua fadhilatnya.
  - Answer: Data ini tiada dalam pangkalan data saya.
  - Reference: Solat taubat didirikan dua rakaat ketika seseorang ingin bertaubat kepada Allah SWT atas segala dosa. Digalakkan apabila telah berazam untuk bertaubat, sebaik-baiknya sebelum bertaubat kepada Allah SW
- **fiqh_b1_solat_gerhana_q7** (partly found; evidence read 28%; 3 of 3 read; declined): Pada suatu malam berlaku gerhana bulan. Terangkan solat yang disunatkan pada ketika itu dari segi pengertian, lafaz niat, dan cara pelaksanaan rakaat pertamanya yang membezakannya daripada solat sunat biasa.
  - Answer: Data ini tiada dalam pangkalan data saya.
  - Reference: Solat gerhana bulan (khusuf) ialah solat yang didirikan kerana terjadinya gerhana, sebanyak dua rakaat dengan empat rukuk dan empat sujud, secara berjemaah atau bersendirian. Niat: أُصَلِّي سُنَّةَ ٱل
- **tajwid_b3_mad_lazim_harfi_muthaqqal_q8** (partly found; evidence read 56%; 3 of 3 read; declined): Terangkan Mad Lazim Harfi Muthaqqal meliputi pengertian, cara bacaan dan maksud setiap perkataan pada namanya, serta berikan satu misal beserta nama surahnya.
  - Answer: Data ini tiada dalam pangkalan data saya.
  - Reference: Mad Lazim Harfi Muthaqqal ialah apabila huruf mad bertemu dengan huruf mati dalam satu huruf di permulaan surah (fawatih al-suwar) dan diidghamkan ke dalam huruf berikutnya. Ia dibaca dengan idgham be
- **tajwid_b3_mad_tazim_q7** (partly found; evidence read 33%; 3 of 3 read): Terangkan hukum Mad Ta'zim meliputi pengertian, kadar harakat dan sebab dinamakan, serta berikan satu contoh ayat al-Quran beserta nama surah dan nombor ayatnya.
  - Answer: Mad Ta'zim ialah bacaan yang membesar dan memuliakan Allah, dengan kadar empat atau lima harakat. Dinamakan Mad Ta'zim kerana membesar dan memuliakan Allah; contohnya dalam Surah as-Saffat ayat 35.
  - Reference: Mad Ta'zim ialah apabila terdapat kalimah لَآ yang menunjukkan penafian bertemu dengan kalimah إِلَٰهَ. Kadarnya empat atau lima harakat. Dinamakan Mad Ta'zim kerana membesar dan memuliakan Allah. Con
- **tajwid_b5_waqaf_q7** (limit cut; evidence read 0%; 2 of 3 read; declined): Apakah maksud waqaf berikut: Hasan, Qabih, Kafi?
  - Answer: Data ini tiada dalam pangkalan data saya.
  - Reference: Waqaf Hasan: menghentikan bacaan pada tempat yang masih tergantung dari segi lafaz dan makna tetapi boleh difahami. Waqaf Qabih: menghentikan bacaan pada tempat yang tidak difahami ertinya atau boleh 

