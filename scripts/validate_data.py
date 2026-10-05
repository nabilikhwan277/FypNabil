"""Validate the KAFA knowledge notes and question bank (Phase 1).

Checks:
  - every expected topic has a note with valid front-matter
  - every note has a question file (latihan files have no note)
  - question JSON parses, required fields present, ids unique
  - max_marks == sum of rubric marks
  - each topic has >= 3 L1, >= 2 L2, >= 1 L3 questions
  - latihan questions point to an existing related_topic_id
  - reports [TIDAK JELAS] markers and verified status

Usage: python scripts/validate_data.py
Exit code 1 if any ERROR is found.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
KB = ROOT / "data" / "knowledge"
QB = ROOT / "data" / "questions"

EXPECTED = {
    "fiqh": [
        "fiqh_b1_pengenalan", "fiqh_b1_solat_rawatib", "fiqh_b1_solat_dhuha",
        "fiqh_b1_solat_hajat", "fiqh_b1_solat_istikharah", "fiqh_b1_solat_tahajud",
        "fiqh_b1_solat_taubat", "fiqh_b1_solat_tarawih", "fiqh_b1_solat_witir",
        "fiqh_b1_solat_hari_raya", "fiqh_b1_solat_gerhana",
        "fiqh_b2_pengertian_puasa", "fiqh_b2_fadhilat_puasa", "fiqh_b2_batal_puasa",
        "fiqh_b2_puasa_wajib_sunat", "fiqh_b2_hikmah_puasa",
    ],
    "jawi": [
        "jawi_b1_imbuhan_an_nun", "jawi_b1_imbuhan_an_alif_nun", "jawi_b1_imbuhan_an_hamzah_nun",
        "jawi_b2_imbuhan_i_ya", "jawi_b2_imbuhan_i_hamzah_ya",
        "jawi_b3_pinjaman_arab", "jawi_b3_pinjaman_inggeris",
        "jawi_b4_akronim_melayu", "jawi_b4_akronim_inggeris", "jawi_b4_akronim_dilafaz",
    ],
    "tajwid": [
        "tajwid_b1_mad_bahagian", "tajwid_b2_mad_asli_kalimi", "tajwid_b2_mad_asli_harfi",
        "tajwid_b3_mad_fari_pengenalan", "tajwid_b3_mad_wajib_muttasil", "tajwid_b3_mad_jaiz_munfasil",
        "tajwid_b3_mad_badal", "tajwid_b3_mad_silah_tawilah", "tajwid_b3_mad_farq",
        "tajwid_b3_mad_tazim", "tajwid_b3_mad_lazim_kalimi_muthaqqal",
        "tajwid_b3_mad_lazim_kalimi_mukhaffaf", "tajwid_b3_mad_lazim_harfi_muthaqqal",
        "tajwid_b3_mad_lazim_harfi_mukhaffaf", "tajwid_b3_mad_aridh_lissukun", "tajwid_b3_mad_lin",
        "tajwid_b3_mad_iwadh", "tajwid_b3_mad_tamkin", "tajwid_b3_mad_silah_qasirah",
        "tajwid_b4_tingkatan_mad", "tajwid_b5_waqaf", "tajwid_b6_ibtida",
    ],
}
LATIHAN = {"fiqh_b1_latihan", "fiqh_b2_latihan"}
# Intro notes are reading material; questions optional.
QUESTIONS_OPTIONAL = {"fiqh_b1_pengenalan"}

NOTE_KEYS = {"id", "subject", "year", "bab", "topic_rumi", "topic_jawi", "source", "pdf_pages", "verified"}
Q_KEYS = {"id", "level", "type", "origin", "question_rumi", "reference_answer_rumi",
          "rubric", "max_marks", "source_pages"}
TYPE_FOR_LEVEL = {1: "short", 2: "structured", 3: "essay"}

errors, warnings = [], []


def err(msg):
    errors.append(msg)


def warn(msg):
    warnings.append(msg)


def read_front_matter(path: Path):
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not m:
        return None, text
    return yaml.safe_load(m.group(1)), text


def main() -> int:
    all_topics = {t for ts in EXPECTED.values() for t in ts}
    stats = {"notes": 0, "question_files": 0, "questions": 0, "unclear": 0, "verified": 0}
    level_totals = Counter()
    seen_qids = set()

    # ---- notes ----
    for subject, topics in EXPECTED.items():
        for tid in topics:
            path = KB / subject / f"{tid}.md"
            if not path.exists():
                err(f"missing note: {path.relative_to(ROOT)}")
                continue
            stats["notes"] += 1
            fm, text = read_front_matter(path)
            if fm is None:
                err(f"{tid}: no front-matter")
                continue
            missing = NOTE_KEYS - fm.keys()
            if missing:
                err(f"{tid}: front-matter missing {sorted(missing)}")
            if fm.get("id") != tid:
                err(f"{tid}: front-matter id is {fm.get('id')!r}")
            if fm.get("subject") != subject:
                err(f"{tid}: subject is {fm.get('subject')!r}")
            n_unclear = text.count("TIDAK JELAS")
            if n_unclear:
                stats["unclear"] += n_unclear
                warn(f"{tid}: {n_unclear} [TIDAK JELAS] marker(s)")
            if fm.get("verified") is True:
                stats["verified"] += 1

    # unexpected note files
    for p in KB.glob("*/*.md"):
        if p.stem not in all_topics:
            warn(f"unexpected note file: {p.relative_to(ROOT)}")

    # ---- questions ----
    for subject, topics in EXPECTED.items():
        files = {p.stem: p for p in (QB / subject).glob("*.json")}
        for tid in topics:
            if tid not in files and tid not in QUESTIONS_OPTIONAL:
                err(f"missing question file: data/questions/{subject}/{tid}.json")
        for stem, path in files.items():
            if stem not in all_topics and stem not in LATIHAN:
                warn(f"unexpected question file: {path.relative_to(ROOT)}")
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                err(f"{stem}: invalid JSON ({e})")
                continue
            stats["question_files"] += 1
            if data.get("topic_id") != stem:
                err(f"{stem}: topic_id is {data.get('topic_id')!r}")
            qs = data.get("questions", [])
            levels = Counter()
            for q in qs:
                qid = q.get("id", "?")
                stats["questions"] += 1
                missing = Q_KEYS - q.keys()
                if missing:
                    err(f"{qid}: missing {sorted(missing)}")
                    continue
                if not (q.get("question_jawi") or "").strip():
                    warn(f"{qid}: no question_jawi")
                if qid in seen_qids:
                    err(f"{qid}: duplicate question id")
                seen_qids.add(qid)
                if q["level"] not in (1, 2, 3):
                    err(f"{qid}: level {q['level']!r}")
                elif q["type"] != TYPE_FOR_LEVEL[q["level"]]:
                    warn(f"{qid}: level {q['level']} but type {q['type']!r}")
                if q["origin"] not in ("generated", "textbook"):
                    err(f"{qid}: origin {q['origin']!r}")
                total = sum(r.get("marks", 0) for r in q["rubric"])
                if total != q["max_marks"]:
                    err(f"{qid}: max_marks {q['max_marks']} != rubric sum {total}")
                if not q["rubric"]:
                    err(f"{qid}: empty rubric")
                for r in q["rubric"]:
                    if not r.get("criterion"):
                        err(f"{qid}: rubric item without criterion")
                    if not r.get("keywords"):
                        warn(f"{qid}: criterion {r.get('criterion')!r} has no keywords")
                if stem in LATIHAN:
                    rel = q.get("related_topic_id")
                    if rel not in all_topics:
                        err(f"{qid}: related_topic_id {rel!r} not a known topic")
                levels[q["level"]] += 1
                level_totals[q["level"]] += 1
            if stem not in LATIHAN and (levels[1] < 3 or levels[2] < 2 or levels[3] < 1):
                err(f"{stem}: level counts L1={levels[1]} L2={levels[2]} L3={levels[3]} (need 3/2/1)")

    # ---- report ----
    expected_notes = len(all_topics)
    print("=" * 60)
    print(f"Notes:           {stats['notes']}/{expected_notes}")
    print(f"Question files:  {stats['question_files']}")
    print(f"Questions:       {stats['questions']}  (L1={level_totals[1]} L2={level_totals[2]} L3={level_totals[3]})")
    print(f"Verified notes:  {stats['verified']}/{stats['notes']}")
    print(f"[TIDAK JELAS]:   {stats['unclear']}")
    print("=" * 60)
    for w in warnings:
        print("WARN ", w)
    for e in errors:
        print("ERROR", e)
    print(f"\n{len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
