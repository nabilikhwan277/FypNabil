from pathlib import Path

import pytest

from backend.app.config import get_settings
from backend.app.kb.chunking import chunk_note, load_note, parse_note

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
