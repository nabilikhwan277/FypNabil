from pathlib import Path

import numpy as np
import pytest

from backend.app.config import get_settings
from backend.app.kb.chunking import (chunk_bilingual, chunk_note, chunk_semantic, chunk_subsection, chunk_table_rows,
                                     chunk_window, load_note, parse_note)

SAMPLE = """---
id: tajwid_b2_mad_asli_kalimi
subject: tajwid
year: 5
bab: 2
topic_rumi: Mad Asli Kalimi
topic_jawi: مد اصلي كلمي
source: buku.pdf
pdf_pages: [15, 16]
verified: false
---

# Mad Asli Kalimi | مد اصلي كلمي

(Unit 1)

## Pengertian
**Rumi:** Mad Asli ialah mad yang dibaca dua harakat.
**Jawi:** مد اصلي اياله مد يڠ دباچ دوا حركة.

## Kadar Harakat
Dua harakat. | دوا حركة.
### Sub
more text here to make it long enough for the minimum length

## Kosong
x
"""


def test_parse_note_front_matter():
    n = parse_note(SAMPLE)
    assert n.topic_id == "tajwid_b2_mad_asli_kalimi"
    assert n.meta["pdf_pages"] == [15, 16]


def test_parse_note_requires_front_matter():
    with pytest.raises(ValueError):
        parse_note("# no front matter")


def test_chunks_one_per_h2_and_keep_h3_with_parent():
    chunks = chunk_note(parse_note(SAMPLE))
    sections = [c.metadata["section"] for c in chunks]
    # "(Unit 1)" is too short for Ringkasan, "Kosong" is dropped (below MIN_CHARS)
    assert sections == ["Pengertian", "Kadar Harakat"]
    kadar = chunks[1]
    assert "### Sub" in kadar.text
    assert kadar.text.startswith("Topik: Mad Asli Kalimi | مد اصلي كلمي\nBahagian: Kadar Harakat")


def test_chunk_metadata_is_scalar_for_chroma():
    for c in chunk_note(parse_note(SAMPLE)):
        assert c.metadata["pdf_pages"] == "15,16"
        assert c.metadata["subject"] == "tajwid"
        assert all(isinstance(v, (str, int, float, bool)) for v in c.metadata.values())


def test_long_section_is_split_with_overlap():
    paras = "\n\n".join(f"Perenggan {i} " + "x" * 300 for i in range(10))
    text = SAMPLE.replace("Dua harakat. | دوا حركة.", paras)
    chunks = [c for c in chunk_note(parse_note(text), max_chars=1000) if c.metadata["section"] == "Kadar Harakat"]
    assert len(chunks) > 1
    assert all(len(c.text) < 1200 for c in chunks)
    # overlap: last paragraph of piece n reappears at the start of piece n+1
    first_last_para = chunks[0].text.split("\n\n")[-1]
    assert first_last_para in chunks[1].text
    assert len({c.id for c in chunks}) == len(chunks)


TABLE_NOTE = SAMPLE.replace("Dua harakat. | دوا حركة.", "Contoh:\n\n| Rumi | Jawi |\n|---|---|\n"
                            + "\n".join(f"| kata{i} | كات{i} |" for i in range(7)))


def test_numeric_overlap_carries_the_tail():
    paras = "\n\n".join(" ".join(f"p{i}w{j}" for j in range(60)) for i in range(10))
    note = parse_note(SAMPLE.replace("Dua harakat. | دوا حركة.", paras))
    none = [c for c in chunk_note(note, max_chars=1000, overlap=0) if c.metadata["section"] == "Kadar Harakat"]
    some = [c for c in chunk_note(note, max_chars=1000, overlap=100) if c.metadata["section"] == "Kadar Harakat"]
    tail = none[0].text[-60:].strip()
    assert tail not in none[1].text and tail in some[1].text


def test_window_cuts_by_size_and_overlaps():
    note = parse_note(SAMPLE.replace("Dua harakat. | دوا حركة.", " ".join(f"w{i}" for i in range(400))))
    chunks = chunk_window(note, size=300, overlap=100)
    assert len(chunks) > 3
    body = [c.text.split("\n\n", 1)[1] for c in chunks]
    assert all(len(b) <= 300 for b in body)
    assert body[1][:20] in body[0]                     # the next window starts inside the previous one
    assert all(c.metadata["section"] in {"Pengertian", "Kadar Harakat", "Kosong"} for c in chunks)
    assert len({c.id for c in chunks}) == len(chunks)


def test_subsection_splits_at_h3():
    note = parse_note(SAMPLE.replace("Dua harakat. | دوا حركة.", "Dua harakat panjangnya, iaitu kadar bacaan biasa."))
    texts = [c.text for c in chunk_subsection(note) if c.metadata["section"] == "Kadar Harakat"]
    assert len(texts) == 2 and texts[1].split("\n\n", 1)[1].startswith("### Sub")


def test_table_rows_repeat_caption_and_header():
    rows = [c.text for c in chunk_table_rows(parse_note(TABLE_NOTE), rows=3) if "| kata" in c.text]
    assert len(rows) == 3                              # 7 rows in groups of 3
    assert all("Contoh:" in t and "| Rumi | Jawi |" in t for t in rows)
    assert "kata6" in rows[-1] and "kata0" not in rows[-1]


def test_bilingual_keeps_rumi_with_jawi():
    note = parse_note(SAMPLE + "\n## Panjang\n" + "\n".join(
        f"**Rumi:** Ayat Rumi nombor {i} yang agak panjang.\n**Jawi:** ايات جاوي نومبور {i}." for i in range(20)))
    for c in chunk_bilingual(note, size=200):
        body = c.text.split("\n\n", 1)[1]
        assert body.count("**Rumi:**") == body.count("**Jawi:**")


def test_semantic_cuts_where_meaning_changes():
    note = parse_note(SAMPLE.replace("Dua harakat. | دوا حركة.", "\n".join(
        [f"puasa ayat {i} " + "a" * 60 for i in range(6)] + [f"solat ayat {i} " + "b" * 60 for i in range(6)])))

    def fake_embed(texts):                             # 2 topics: puasa vs everything else
        return np.array([[1.0, 0.0] if "puasa" in t else [0.0, 1.0] for t in texts])
    chunks = chunk_semantic(note, fake_embed, min_chars=50, percentile=10)
    assert any("puasa ayat 5" in c.text and "solat" not in c.text for c in chunks)


def test_all_methods_chunk_real_notes():
    files = sorted(Path(get_settings().knowledge_dir).glob("*/*.md"))
    for f in files[:: 6]:
        note = load_note(f)
        for chunks in (chunk_window(note), chunk_subsection(note), chunk_table_rows(note), chunk_bilingual(note)):
            assert chunks and len({c.id for c in chunks}) == len(chunks)


def test_all_real_notes_chunk_cleanly():
    kb = get_settings().knowledge_dir
    files = sorted(Path(kb).glob("*/*.md"))
    assert len(files) == 48
    ids = set()
    for f in files:
        chunks = chunk_note(load_note(f))
        assert chunks, f"no chunks for {f.name}"
        for c in chunks:
            assert c.id not in ids
            ids.add(c.id)
