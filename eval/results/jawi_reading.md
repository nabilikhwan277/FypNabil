# Jawi reading test (Phase 3.2)

30 words from the Jawi textbook tables: 15 spelling (Rumi → Jawi) and 15 reading (Jawi → Rumi). Exact = same as the textbook (harakat removed, letter variants unified); CER = character error rate (lower is better).

| Model | Spelling exact | Spelling CER | Reading exact | Reading CER | All exact | Failed calls |
|---|---|---|---|---|---|---|
| GPT-6 Luna | 53% | 10% | 87% | 2% | 70% | 0 |
| Claude Haiku 5.5 | 40% | 15% | 73% | 10% | 57% | 0 |
| Llama 3.1 8B | 13% | 33% | 20% | 42% | 17% | 0 |
| Fanar 9B (open-weight) | 13% | 29% | 20% | 35% | 17% | 0 |
| Qwen3-4B fine-tuned (LoRA r8, 2 epochs) | 7% | 38% | 20% | 31% | 13% | 0 |
| Qwen3-4B fine-tuned (LoRA r16, 2 epochs) | 7% | 46% | 20% | 30% | 13% | 0 |
| Qwen3-4B fine-tuned (LoRA r16, 1 epoch) | 7% | 46% | 20% | 28% | 13% | 0 |
| Qwen3-4B fine-tuned (LoRA r8, 1 epoch) | 7% | 45% | 20% | 29% | 13% | 0 |
| SEA-LION v3 9B (open-weight) | 0% | 90% | 20% | 30% | 10% | 0 |
| Qwen3-4B (open-weight) | 7% | 34% | 7% | 32% | 7% | 0 |

## Items and replies

| Item | Asked | Textbook | Claude Haiku 5.5 | GPT-6 Luna | Llama 3.1 8B | Fanar 9B (open-weight) | SEA-LION v3 9B (open-weight) | Qwen3-4B (open-weight) | Qwen3-4B fine-tuned (LoRA r8, 2 epochs) | Qwen3-4B fine-tuned (LoRA r16, 2 epochs) | Qwen3-4B fine-tuned (LoRA r16, 1 epoch) | Qwen3-4B fine-tuned (LoRA r8, 1 epoch) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| spell01 | merajai | مراجاءي | ✗ مرجاي | ✗ مراجي | ✗ ميراجي | ✗ مَرَاجِي | ✗ مَرَجَاءِ | ✗ مريجى | ✗ مَرَاجَى | ✗ مَرَاجَى | ✗ مَرَاجَى | ✗ مَرَاجَى |
| spell02 | generasi | ݢينراسي | ✗ generasi (Jawi: جنرسي)  Hmm, that's wron | ✓ ڬينراسي | ✗ ݣنراسين | ✗ جِنَرَاسِي | ✗ générationé | ✗ جِنَرَسِي | ✗ جَنَرَاسِي | ✗ جَنَرَسِي | ✗ جَنَّسَة | ✗ جَنَرَاسِي |
| spell03 | rakaat | ركعة | ✓ رَكْعَة | ✗ راكعت | ✗ رَكْعَات | ✗ رَكَاتْ | ✗ رَكَاتْ | ✗ رَاكَت | ✗ رَكَات | ✗ رَكَّات | ✗ رَكَع | ✗ رَكَات |
| spell04 | belai | بلاي | ✓ بلاي | ✓ بلاي | ✗ بلائی | ✓ بِلَايْ | ✗ 블레이 | ✓ بلاي | ✗ بَلَى | ✗ بَلَى | ✗ بَلَى | ✗ بَلَى |
| spell05 | deru | درو | ✗ دروء | ✓ درو | ✗ دَرُؤ | ✓ دِرُو | ✗ ḍeru | ✗ ديرو | ✓ دَرُو | ✓ دَرُو | ✓ دَرُو | ✓ دَرُو |
| spell06 | vaksin | ۏكسين | ✗ ۏاکسين | ✗ ۏاكسين | ✗ واکسین | ✗ ڤاكْسِينْ | ✗ waksin | ✗ فَكْسِن | ✗ ڤاكسين | ✗ وَكْسِن | ✗ ڤاكسين | ✗ ڤاكسين |
| spell07 | dikatai | دکاتاءي | ✗ ديكاتاي | ✗ دکاتاي | ✗ ڊڪتاي | ✗ دِكَاتِي | ✗ dikatahi | ✗ ديك٢تَي | ✗ دِكَتَى | ✗ ذٗكٗتَى | ✗ دِكَتَى | ✗ دِكَتَى |
| spell08 | patriotisme | ڤاتريوتيسمى | ✓ ڤاتريوتيسمي | ✗ ڤاتريوتيسم | ✗ ڤاتريوتيسم | ✗ پتريوتيسم | ✗ patriotisme | ✗ ڤاٗتريٗتىمٗس | ✗ ڤاٗتريٗتىٗم | ✗ تَبَدَّىٰنَتَنَنَنَنَنَنَنَنَنَنَنَنَنَن | ✗ بَطَلَةٍ | ✗ بَطَالِيَة |
| spell09 | cintai | چينتاءي | ✗ cinta  Wait — the user asked for "cintai | ✗ چينتاي | ✗ چينتاي | ✗ چنتاي | ✗ cinai | ✗ چيناي | ✗ عِنْتَى | ✗ عِنْتَى | ✗ تَعَلَّمْ | ✗ اِحِبْ |
| spell10 | tragedi | تراݢيدي | ✗ Malay "tragedi" in Jawi: ترجادی  Wait —  | ✓ تراݢيدي | ✗ تراجيدي | ✗ تَرَاجِيدِي | ✗ tragedi | ✗ تَرَدِي | ✗ تَرَدِيدِي | ✗ تَرَدِيدِي | ✗ تَرَدِيدِي | ✗ تَرَدِيدِي |
| spell11 | jutaan | جوتاءن | ✗ جوتأن | ✓ جوتاءن | ✓ جوتاءن | ✗ جُوَاتَانْ | ✗ jujutan | ✗ جوتاان | ✗ جُمْلَة | ✗ جُمْعَةٌ | ✗ جُمْعَةٌ | ✗ مئات |
| spell12 | basikal | باسيكل | ✗ بسيكل | ✓ باسيکل | ✓ باسيكل | ✗ بَسِيقَلْ | ✗ baskal | ✗ باصيكل | ✗ بَسِكَل | ✗ بَسِكَل | ✗ بَسِكَل | ✗ بَسِكَل |
| spell13 | dibayangi | دبايڠي | ✓ dبايڠي  Wait, let me write it correctly  | ✓ دبايڠي | ✗ ڈيبايڠي | ✗ دِبَايَانْجِي | ✗ dibayangi | ✗ دِبَيَانِي | ✗ دِبَيَّانِي | ✗ دِبَيَنِيَتَنَ | ✗ دِبَيَانِي | ✗ تُبَيَّنَ |
| spell14 | skrip | سكريڤ | ✓ skrip  Wait, I should answer with Jawi s | ✓ سکريڤ | ✗ سڪريب | ✗ سْكْرِيبْ | ✗ ꧋ꦏꦿꦶꦥ꧀ | ✗ سكريب | ✗ سَكْرِب | ✗ سَكْرِب | ✗ سَكْرِب | ✗ سَكْرِب |
| spell15 | sangkaan | سڠكاءن | ✓ سڠکاءن | ✗ ساڠکاءن | ✗ Sangkān | ✗ سَانْكَانْ | ✗ سڠkaan | ✗ سڠكاان | ✗ سَنْكَان | ✗ سَنْكَان | ✗ سَنْكَان | ✗ سَنْكَان |
| read01 | دريتا | derita | ✗ Kata Jawi "دريتا" dibaca **Derita**.Deri | ✓ Derita | ✗ Drietah | ✗ Dariti | ✗ Laut | ✗ Dritaa | ✗ dari ta | ✗ dari | ✗ dari | ✗ dariita |
| read02 | دڤرستوجوءي | dipersetujui | ✓ **Dipersetujui** | ✓ dipersetujui | ✗ Saya tidak dapat menulis perkataan Jawi  | ✗ Dewanstogewi | ✗ Devarstujowi | ✗ Dipertingkatkan | ✗ Dipertemukan dengan kamu. | ✗ Dipertingkatkan. | ✗ dipertingkatkan | ✗ Dipertemukan dengan kamu. |
| read03 | بايڠ | bayang | ✓ **Bayang** | ✓ bayang | ✗ Baiyang | ✗ Bayan | ✓ Bayang | ✗ Baiŋ | ✗ Baiŋ. | ✗ Banyak. | ✗ Baiŋ | ✗ Baiŋ |
| read04 | لڠکڤ | lengkap | ✓ lengkap | ✓ lengkap | ✗ Lingkup | ✗ "الكوڤ" | ✗ Melangkawi | ✗ Lengkup | ✗ Lengkup | ✗ langkup | ✗ langkup | ✗ lengkup |
| read05 | اوبت | ubat | ✓ ubat | ✓ ubat | ✗ Saya tidak dapat membantu dengan permint | ✗ Opat | ✗ Obat | ✗ Obt | ✗ Obt | ✗ Obat | ✗ obt | ✗ Obt |
| read06 | بالوتي | baluti | ✓ baluti | ✓ baluti | ✗ Baluati | ✓ Baluti | ✗ Baluati | ✗ Baloeti | ✗ baloeti | ✗ baloeti | ✗ baloeti | ✗ baloeti |
| read07 | ريندوءي | rindui | ✓ **rindui** | ✓ Rindui | ✗ Rindu | ✗ Rindau'i | ✗ Rindou'i | ✗ Rindoei | ✗ Rinandoi | ✗ Rinandoi | ✗ Rindu. | ✗ Rinandoi |
| read08 | ماجو | maju | ✓ Maju | ✓ maju | ✗ ماجو | ✓ Maju | ✓ Maju | ✓ Maju | ✓ maju | ✓ maju | ✓ maju | ✓ maju |
| read09 | درا | dera | ✗ dara | ✗ dara | ✗ Dara | ✗ Darā' | ✗ Dara | ✗ Dara | ✗ dara | ✗ dari | ✗ dara | ✗ dara |
| read10 | دمورکاءي | dimurkai | ✓ **dimurkai** | ✓ dimurkai | ✗ Maaf, saya tidak dapat membantu dengan p | ✗ Demorkasi | ✗ Demokrasi | ✗ Dumurkai | ✗ dumurkai | ✗ dumurkai | ✗ dumurkai | ✗ dumurkai |
| read11 | مڠهنتوءي | menghantui | ✗ menghentui | ✓ menghantui | ✗ Menghentu'yo. | ✗ Masentui | ✗ Menggantungi | ✗ Menghentoi | ✗ Menghentuikan | ✗ menghentai | ✗ menghentai | ✗ menghentai |
| read12 | سوكتن | sukatan | ✓ Sukatan | ✓ sukatan | ✗ Sokten | ✓ Sukatan | ✗ Sukaten | ✗ Sokten | ✗ sukatn | ✗ sukten | ✗ sukatn | ✗ sukatn |
| read13 | ميكانيسمى | mekanisme | ✓ Mekanisme | ✗ Mekanisma | ✓ mekanisme | ✗ Mekanisma | ✗ Mekanismi | ✗ mechanisme | ✓ mekanisme | ✓ mekanisme | ✓ mekanisme | ✓ mekanisme |
| read14 | تاري | tari | ✓ tari | ✓ tari | ✓ tari | ✗ Tarikh | ✓ Tari | ✗ Tarii | ✓ tari | ✓ tari | ✓ tari | ✓ tari |
| read15 | ماره | marah | ✗ **Mara** | ✓ marah | ✓ Marah | ✗ Mara | ✗ Marahi | ✗ Mareh | ✗ Mara. | ✗ Mara. | ✗ Mara. | ✗ Mara. |
