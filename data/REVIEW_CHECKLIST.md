# Senarai Semakan Guru | Teacher Review Checklist

I (the AI) transcribed every note from the textbook page images. A teacher or ustaz(ah) must check them before the system uses them. Tick each item, fix the file if needed, then set `verified: true` in the front-matter of each note once the whole note has been checked.

Run `python scripts/validate_data.py` after any edit.

## A. Items that could not be read (`[TIDAK JELAS]`)
- [ ] `fiqh/fiqh_b1_solat_dhuha.md`: 1 unclear word
- [ ] `jawi/jawi_b1_imbuhan_an_alif_nun.md`: 1 unclear word
- [ ] `jawi/jawi_b2_imbuhan_i_hamzah_ya.md`: ماءنسي (manusia), book p34
- [ ] `jawi/jawi_b3_pinjaman_inggeris.md`: "Old Town Cafe" Jawi spelling, book p49
- [ ] `tajwid/tajwid_b2_mad_asli_kalimi.md`: 1 unclear word
- [ ] `tajwid/tajwid_b4_tingkatan_mad.md`: the small mark on مِمَّا يَشَآءُ, book p56
- [ ] `tajwid/tajwid_b5_waqaf.md`: the مـ sign in Yunus:65 is not visible in the image; the ∴ ∴ marks in al-Baqarah:2 are faint

## B. Arabic text to check against the book
- [ ] All lafaz niat in Fiqh Bab 1 (the harakat on الْإِسْتِخَارَةِ in particular)
- [ ] Takbir raya and tasbih (`fiqh_b1_solat_hari_raya.md`)
- [ ] Doa in the Jawi notes (e.g. رَبِّ ٱغْفِرْ لِى..., the doa for boarding a vehicle)
- [ ] Every Quran example in the Tajwid notes (harakat, small signs, pause marks)
- [ ] The "asal" forms for Mad Badal (ءَأۡدَمُ, أُؤۡتِيَ, إِئۡمَانًا)

## C. Answers the book does not print (worked out by the AI; please confirm)
- [ ] `fiqh_b1_latihan` q8 (Salah: missing the 7 takbir does not cancel the solat). This comes from general fiqh, not from the book.
- [ ] `fiqh_b1_latihan` q11 (Betul: tahajud is also called qiamullail). The book doesn't state this.
- [ ] `tajwid_b4_tingkatan_mad`: which mad is "strongest" or "weakest" (taken from the order of the martabat table)
- [ ] `tajwid_b3_mad_lazim_harfi_muthaqqal`: 6 harakat, taken from the Mad Lazim introduction (book p31)
- [ ] Jawi akronim answers not printed in the book: JPJ, KSSR, LHDN, SK, SPM, GPK, SMS, CCTV, LRT, JAKIM, TABIKA
- [ ] Fill-in-the-blank answers in `jawi_b4_akronim_inggeris`

## D. Jawi spelling and letter shapes
The book's font draws some letters in shapes that look like other letters. The notes use the standard Jawi letters. Please confirm:
- [ ] Final ک printed → written as ك (بڠك, ڤوستاك, ريڤوبليك)
- [ ] ݢ / ڠ / ڽ / ڤ that look like ک / غ / ث / ف
- [ ] ۏ versus و in اونيۏرسيتي, ۏي, كونۏوكيشن
- [ ] ايچ versus ايج (the letter "h")
- [ ] Final letter printed separately in kata pinjaman rule iii (تيك س, ݢول ف); both forms are accepted when marking
- [ ] Akronim: dots written without spaces (د.ب.ڤ); both forms are accepted when marking

## E. Rumi transliteration
The Jawi textbook has no Rumi text. All Rumi in the Jawi notes is the AI's transliteration.
- [ ] Spot-check a few pages in each Jawi note (e.g. "merakui" from راکو)

## Sign-off
| Subject | Reviewed by | Date | Notes |
|---|---|---|---|
| Ibadah (Fiqh) | | | |
| Jawi | | | |
| Tajwid | | | |
