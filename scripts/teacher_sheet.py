"""Teacher marking kit: two or more KAFA teachers mark the same answers blind.

No real pupil answers are needed. The answer set is built from
  - AI-written pupil-style answers from the TEST silver set (full / partial /
    misconception, sampled evenly per subject),
  - a few rule-built answers that test known failure modes (Jawi typo,
    swapped number, Rumi for a Jawi item, flipped Betul/Salah),
  - researcher-written answers in data/teacher/researcher_answers.json:
    fluent-but-wrong "keyword illusion" answers and pupil-style answers
    (very short, shorthand, spelling slips, mixed script).
The teachers supply the marks, so the labels are human even though the
answers are not from real pupils. Answers are shuffled and get opaque IDs
(T001, ...); how each one was made is kept in teacher_set_key.json only.

1) export: write one sheet per teacher plus the hidden key.
       .venv\\Scripts\\python scripts\\teacher_sheet.py export
   -> data/teacher/marking_guru_A.csv, marking_guru_B.csv, teacher_set_key.json
   Each teacher fills `teacher_met` with ya / separa / tidak, on their own.

2) agree: compare the filled sheets of 2 or more teachers (inter-rater
   agreement) and write the sheet for the final decision. Each criterion gets
   the majority mark (more than half of the teachers); with no majority
   (e.g. 2-2) the row is left blank to settle together. More sheets can be
   added after the first two.
       .venv\\Scripts\\python scripts\\teacher_sheet.py agree guru_A.csv guru_B.csv
   -> data/teacher/marking_final.csv: rows where both agree are pre-filled;
      rows where they differ are blank and show both marks, for the teachers
      to settle together. Also writes data/teacher/agreement.md.

3) import: read the settled sheet into data/teacher/teacher_test.json, then
   run the evaluation on it:
       .venv\\Scripts\\python scripts\\teacher_sheet.py import data\\teacher\\marking_final.csv
       .venv\\Scripts\\python eval\\scoring_features.py teacher
       .venv\\Scripts\\python eval\\evaluate.py 0 teacher

Rows with an empty `teacher_met` are skipped (partially marked sheets work).

Google Form route (instead of giving teachers the CSV sheets):
  form       write data/teacher/google_form/create_form.gs; paste it into
             script.google.com and run createForm to build the form
  from-form  responses.csv   (the responses sheet, downloaded as CSV)
             -> guru_1_filled.csv, guru_2_filled.csv, ... (one per teacher
             name, any number of teachers), then runs agree
  report     after import + evaluation: eval/results/teacher_report.md

When the teachers disagree (blank rows in marking_final.csv):
  labels             labels/guru_N.json per teacher + labels/agreed.json (clear cases); from-form does this too
  adjudication-form  google_form/create_adjudication_form.gs: a short form with ONLY the disputed criteria
                     for a third teacher (same Apps Script steps as the main form)
  from-adjudication  responses.csv -> each disputed criterion gets the middle of all marks, then import
Compare the system with each teacher: eval/teacher_compare.py
"""
from __future__ import annotations

import csv
import json
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "eval"))

from backend.app.assess.decision import award  # noqa: E402
from backend.app.questions import load_questions  # noqa: E402

FIELDS = ["answer_id", "question_id", "subject", "level", "question", "reference_answer", "student_answer",
          "criterion_no", "criterion", "marks", "teacher_met", "teacher_comment"]
OUT_DIR = ROOT / "data" / "teacher"
RES = ROOT / "eval" / "results"
KEY = OUT_DIR / "teacher_set_key.json"
RESEARCHER = OUT_DIR / "researcher_answers.json"
VALID = {"ya", "separa", "tidak"}
ORD = {"tidak": 0, "separa": 1, "ya": 2}

PARAPHRASE_PER_SUBJECT = 8       # split evenly over full / partial / misconception
PROGRAMMATIC_KINDS = {"jawi_typo": 1, "number_swap": 1, "rumi_for_jawi": 1, "tf_flip": 1}
RESEARCHER_PER_KIND = {"keyword_illusion": 10, "pupil_style": 10}   # other kinds: all
SEED = 42


def _build_set() -> list[dict]:
    from silver import load_silver

    rng = random.Random(SEED)
    silver = load_silver("test")
    picked: list[dict] = []
    kinds = ("paraphrase_full", "partial", "misconception")
    for subject in ("fiqh", "jawi", "tajwid"):
        for n, kind in enumerate(kinds):
            want = PARAPHRASE_PER_SUBJECT // 3 + (1 if n < PARAPHRASE_PER_SUBJECT % 3 else 0)
            pool = [i for i in silver if i["family"] == "paraphrase" and i["kind"] == kind
                    and i["question_id"].startswith(subject)]
            picked += rng.sample(pool, min(want, len(pool)))
    for kind, want in PROGRAMMATIC_KINDS.items():
        pool = [i for i in silver if i["family"] == "programmatic" and i["kind"] == kind]
        picked += rng.sample(pool, min(want, len(pool)))
    items = [{"source": i["answer_id"], "question_id": i["question_id"], "kind": i["kind"],
              "script": i.get("script", ""), "answer": i["answer"]} for i in picked]
    seen = {(i["question_id"], i["answer"].strip()) for i in items}
    by_kind: dict[str, list] = defaultdict(list)
    for n, r in enumerate(json.loads(RESEARCHER.read_text(encoding="utf-8")), 1):
        if (r["question_id"], r["answer"].strip()) not in seen:     # same answer already in the silver sample
            by_kind[r["kind"]].append((n, r))
    for kind, pool in by_kind.items():
        for n, r in rng.sample(pool, min(RESEARCHER_PER_KIND.get(kind, len(pool)), len(pool))):
            items.append({"source": f"researcher::{n}", "question_id": r["question_id"], "kind": r["kind"],
                          "script": "", "answer": r["answer"], "note": r.get("note", "")})
    rng.shuffle(items)
    for n, it in enumerate(items, 1):
        it["answer_id"] = f"T{n:03d}"
    return items


def _write_sheet(path: Path, items: list[dict], qs: dict,
                 mets: dict[tuple[str, int], str] | None = None, comments: dict[str, str] | None = None) -> int:
    mets, comments, rows = mets or {}, comments or {}, 0
    with path.open("w", newline="", encoding="utf-8-sig") as fh:   # BOM so Excel shows Jawi correctly
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        for it in items:
            q = qs[it["question_id"]]
            for n, c in enumerate(q["rubric"], 1):
                w.writerow({"answer_id": it["answer_id"], "question_id": q["id"], "subject": q["subject"],
                            "level": q["level"], "question": q["question_rumi"],
                            "reference_answer": q.get("reference_answer_rumi", ""), "student_answer": it["answer"],
                            "criterion_no": n, "criterion": c["criterion"], "marks": c["marks"],
                            "teacher_met": mets.get((it["answer_id"], n), ""),
                            "teacher_comment": comments.get(it["answer_id"], "") if n == 1 else ""})
                rows += 1
    return rows


def export() -> None:
    qs = load_questions()
    items = _build_set()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    KEY.write_text(json.dumps(items, indent=1, ensure_ascii=False), encoding="utf-8")
    for guru in ("A", "B"):
        rows = _write_sheet(OUT_DIR / f"marking_guru_{guru}.csv", items, qs)
    by_kind: dict[str, int] = defaultdict(int)
    for it in items:
        by_kind[it["kind"]] += 1
    print(f"{len(items)} answers, {rows} rows per sheet -> {OUT_DIR}")
    print("  " + ", ".join(f"{k}={v}" for k, v in sorted(by_kind.items())))
    print(f"hidden key -> {KEY} (do not give this to the teachers)")


def _read(path: Path) -> dict[tuple[str, int], dict]:
    with path.open(encoding="utf-8-sig") as fh:
        return {(r["answer_id"], int(r["criterion_no"])): r for r in csv.DictReader(fh)}


def _fleiss_kappa(ratings: list[list[int]], categories: int = 3) -> float:
    """Fleiss' kappa for items each rated by the same number of raters (ratings[i] = one item's marks)."""
    n = len(ratings[0])
    counts = [[r.count(c) for c in range(categories)] for r in ratings]
    p_items = [(sum(x * x for x in row) - n) / (n * (n - 1)) for row in counts]
    p_cats = [sum(row[c] for row in counts) / (len(ratings) * n) for c in range(categories)]
    p_bar, p_exp = sum(p_items) / len(p_items), sum(p * p for p in p_cats)
    return 1.0 if p_exp == 1 else (p_bar - p_exp) / (1 - p_exp)


def agree(paths: list[Path], out: Path, names: list[str] | None = None) -> None:
    """Agreement between 2 or more teachers' filled sheets, and the sheet for the final decision.

    The final mark for a criterion is the majority mark (more than half of the teachers);
    with no majority (e.g. 2-2 with four teachers) the row is left blank for discussion.
    """
    from itertools import combinations

    from sklearn.metrics import cohen_kappa_score

    qs = load_questions()
    sheets = [_read(p) for p in paths]
    names = names or [p.stem for p in paths]
    cols = [f"guru_{i}" for i in range(1, len(sheets) + 1)]
    met = lambda s, k: s[k]["teacher_met"].strip().lower()  # noqa: E731
    keys = [k for k in sheets[0] if all(k in s for s in sheets)]
    complete = [k for k in keys if all(met(s, k) in VALID for s in sheets)]
    grid = [[ORD[met(s, k)] for s in sheets] for k in complete]   # one row per criterion
    exact = sum(len(set(r)) == 1 for r in grid) / len(grid) if grid else 0.0
    pairs = list(combinations(range(len(sheets)), 2))
    kappas = [cohen_kappa_score([r[i] for r in grid], [r[j] for r in grid]) for i, j in pairs] if grid else [0.0]
    qwks = [cohen_kappa_score([r[i] for r in grid], [r[j] for r in grid], weights="quadratic") for i, j in pairs] if grid else [0.0]
    fleiss = _fleiss_kappa(grid) if grid else 0.0

    # answer-level: every teacher gave the same total score
    per_answer: dict[str, list[list[float]]] = defaultdict(list)
    for k in complete:
        marks = qs[sheets[0][k]["question_id"]]["rubric"][k[1] - 1]["marks"]
        per_answer[k[0]].append([award(marks, met(s, k)) for s in sheets])
    full = {aid: v for aid, v in per_answer.items() if len(v) == len(qs[sheets[0][(aid, 1)]["question_id"]]["rubric"])}
    same_score = sum(len({round(sum(col), 3) for col in zip(*v)}) == 1 for v in full.values())

    disagree = 0
    with out.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS + cols)
        w.writeheader()
        for k in keys:
            votes = [met(s, k) for s in sheets]
            valid = [v for v in votes if v in VALID]
            top = max(set(valid), key=valid.count) if valid else ""
            final = top if valid and valid.count(top) * 2 > len(sheets) else ""
            row = {f: sheets[0][k][f] for f in FIELDS}
            row.update(dict(zip(cols, votes)), teacher_met=final,
                       teacher_comment=" | ".join(c for s in sheets if (c := s[k]["teacher_comment"].strip())))
            disagree += final == ""
            w.writerow(row)

    many = len(sheets) > 2
    lines = [f"# Inter-rater agreement ({len(sheets)} teachers)", "",
             *[f"- {c}: {n}" for c, n in zip(cols, names)], "",
             f"- Criteria marked by every teacher: {len(complete)} of {len(keys)}",
             f"- Exact agreement (all teachers gave the same ya / separa / tidak): {exact:.1%}",
             f"- Cohen's kappa{' (mean of all teacher pairs)' if many else ''}: {sum(kappas) / len(kappas):.3f}",
             f"- Quadratic weighted kappa{' (mean of all teacher pairs)' if many else ''}: {sum(qwks) / len(qwks):.3f}",
             f"- Fleiss' kappa (all teachers together): {fleiss:.3f}",
             f"- Answers where every teacher gave the same total score: {same_score} of {len(full)}"
             + (f" ({same_score / len(full):.1%})" if full else ""),
             f"- Rows with no majority, left blank for discussion: {disagree}", "",
             "Final mark per criterion = the majority mark (more than half of the teachers).",
             "Reading kappa: below 0.40 weak, 0.41-0.60 moderate, 0.61-0.80 substantial, above 0.80 almost perfect."]
    if many:
        lines[-2:-2] = ["", "| Pair | Cohen's kappa | QWK |", "|---|---|---|",
                        *[f"| {cols[i]} vs {cols[j]} | {kp:.3f} | {qw:.3f} |" for (i, j), kp, qw in zip(pairs, kappas, qwks)], ""]
    (OUT_DIR / "agreement.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (OUT_DIR / "agreement.json").write_text(json.dumps({
        "raters": len(sheets), "names": names, "criteria_both": len(complete), "criteria_total": len(keys),
        "exact": round(exact, 3), "kappa": round(sum(kappas) / len(kappas), 3), "qwk": round(sum(qwks) / len(qwks), 3),
        "fleiss": round(fleiss, 3), "answers": len(full), "same_score": same_score, "to_discuss": disagree},
        indent=1, ensure_ascii=False), encoding="utf-8")
    print("\n".join(lines))
    print(f"\nsheet for the final decision -> {out}")


def _label_items(path: Path, column: str = "teacher_met", source: str = "teacher") -> tuple[list[dict], int]:
    """Answers whose every criterion has a valid mark in `column`, in the silver-set format."""
    qs = load_questions()
    key = {it["answer_id"]: it for it in json.loads(KEY.read_text(encoding="utf-8"))} if KEY.exists() else {}
    rows: dict[str, list[dict]] = defaultdict(list)
    with path.open(encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            rows[r["answer_id"]].append(r)
    out, skipped = [], 0
    for aid, rs in rows.items():
        q = qs.get(rs[0]["question_id"])
        mets = {int(r["criterion_no"]): (r.get(column) or "").strip().lower() for r in rs}
        if q is None or len(mets) != len(q["rubric"]) or any(m not in VALID for m in mets.values()):
            skipped += 1
            continue
        crit = [{"criterion": c["criterion"], "met": mets[n]} for n, c in enumerate(q["rubric"], 1)]
        k = key.get(aid, {})
        out.append({"question_id": q["id"], "answer_id": aid, "kind": k.get("kind", aid.split("::")[-1]),
                    "script": k.get("script", ""), "source": k.get("source", ""),
                    "answer": rs[0]["student_answer"], "criteria": crit,
                    "expected_score": sum(award(c["marks"], m["met"]) for c, m in zip(q["rubric"], crit)),
                    "label_source": source, "comment": " | ".join(r["teacher_comment"] for r in rs if r.get("teacher_comment"))})
    return out, skipped


def import_(path: Path) -> None:
    """The settled final marks -> data/teacher/teacher_test.json (the E1 reference)."""
    out, skipped = _label_items(path)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dest = OUT_DIR / "teacher_test.json"
    dest.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"imported {len(out)} fully-marked answers -> {dest} (skipped {skipped} incomplete)")


LABELS = OUT_DIR / "labels"


def labels() -> None:
    """One label set per teacher (labels/guru_N.json) and the clear cases where all teachers agree
    (labels/agreed.json), from marking_final.csv. Used by eval/teacher_compare.py and
    `experiments.py --labels`. The answers stay the same 50; only the reference marks differ."""
    final = OUT_DIR / "marking_final.csv"
    with final.open(encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    cols = sorted(c for c in rows[0] if re.fullmatch(r"guru_\d+", c))
    LABELS.mkdir(parents=True, exist_ok=True)
    names = (json.loads((OUT_DIR / "agreement.json").read_text(encoding="utf-8")).get("names")
             if (OUT_DIR / "agreement.json").exists() else None) or cols
    for col, name in zip(cols, names):
        items, _ = _label_items(final, column=col, source=f"teacher:{name}")
        (LABELS / f"{col}.json").write_text(json.dumps(items, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"{col} ({name}): {len(items)} answers -> {LABELS / (col + '.json')}")
    # agreed = answers where every teacher gave the same mark on every criterion
    tmp = LABELS / "_agreed.csv"
    with tmp.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]) + ["agreed"])
        w.writeheader()
        for r in rows:
            v = {r[c].strip().lower() for c in cols}
            w.writerow(r | {"agreed": v.pop() if len(v) == 1 else ""})
    items, _ = _label_items(tmp, column="agreed", source="teacher:agreed")
    tmp.unlink()
    (LABELS / "agreed.json").write_text(json.dumps(items, indent=1, ensure_ascii=False), encoding="utf-8")
    n_crit = sum(len({r[c].strip().lower() for c in cols}) == 1 for r in rows)
    print(f"agreed: {len(items)} answers fully agreed ({n_crit} of {len(rows)} criteria agreed) -> {LABELS / 'agreed.json'}")


ADJ_TITLE = "Penandaan Tambahan KAFA (Guru Ketiga)"
ADJ_INTRO = (
    "Terima kasih kerana membantu. Dua orang guru telah menanda jawapan ini tetapi tidak bersetuju pada kriteria "
    "di bawah. Sila tandakan setiap kriteria seorang diri, seperti anda menanda jawapan murid Tahun 5 dalam UPKK:\n"
    "  Ya - memenuhi kriteria sepenuhnya\n"
    "  Separa - memenuhi sebahagian sahaja (idea betul tetapi butiran penting tiada)\n"
    "  Tidak - tidak memenuhi kriteria\n\n"
    "Jawapan ini ialah contoh jawapan untuk kajian, bukan jawapan murid sebenar.")


def adjudication_form() -> None:
    """Short Google Form with ONLY the criteria the teachers disagreed on (blank in marking_final.csv)."""
    with (OUT_DIR / "marking_final.csv").open(encoding="utf-8-sig") as fh:
        todo = {(r["answer_id"], int(r["criterion_no"])) for r in csv.DictReader(fh) if not r["teacher_met"].strip()}
    if not todo:
        sys.exit("No disputed criteria: every row of marking_final.csv already has a mark.")
    dest = form(only=todo, title=ADJ_TITLE, intro=ADJ_INTRO, filename="create_adjudication_form.gs")
    print(f"{len(todo)} disputed criteria -> {dest}")


def from_adjudication(path: Path) -> None:
    """Add the third teacher's marks: each disputed criterion gets the MIDDLE of all marks
    (with 2 teachers + 1 adjudicator this is the majority, or 'separa' if all three differ),
    then import the settled marks as the E1 reference."""
    with path.open(encoding="utf-8-sig") as fh:
        responses = list(csv.DictReader(fh))
    latest = {}
    for r in responses:
        name = " ".join((r.get(FORM_NAME) or "").split())
        if name:
            latest[name.casefold()] = r
    if not latest:
        sys.exit(f"no responses in {path}")
    crit = re.compile(r"^(T\d{3}) K(\d+):")
    adj: dict[tuple[str, int], list[str]] = defaultdict(list)
    for r in latest.values():
        for col, val in r.items():
            if m := crit.match(col or ""):
                word = (val or "").split(" ")[0].strip().lower()
                if word in VALID:
                    adj[(m[1], int(m[2]))].append(word)
    final = OUT_DIR / "marking_final.csv"
    with final.open(encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    cols = [c for c in rows[0] if re.fullmatch(r"guru_\d+", c)]
    settled = still = 0
    for r in rows:
        r["adjudicator"] = "/".join(adj.get((r["answer_id"], int(r["criterion_no"])), []))
        if r["teacher_met"].strip():
            continue
        votes = sorted((ORD[v] for v in [*(r[c].strip().lower() for c in cols), *adj.get((r["answer_id"], int(r["criterion_no"])), [])]
                        if v in ORD))
        if len(votes) > len(cols):                       # the adjudicator marked this one
            r["teacher_met"] = {0: "tidak", 1: "separa", 2: "ya"}[votes[len(votes) // 2]]
            settled += 1
        else:
            still += 1
    with final.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"settled {settled} disputed criteria with the third teacher ({', '.join(r.get(FORM_NAME, '') for r in latest.values())});"
          f" {still} still blank")
    import_(final)


FORM_DIR = OUT_DIR / "google_form"
FORM_TITLE = "Penandaan Jawapan KAFA UPKK Tahun 5"
FORM_INTRO = (
    "Terima kasih kerana sudi membantu kajian Projek Tahun Akhir ini (lebih kurang 30 hingga 45 minit).\n\n"
    "Setiap halaman ialah SATU jawapan. Baca soalan, jawapan rujukan dan jawapan murid, kemudian pilih bagi "
    "setiap kriteria rubrik:\n"
    "  Ya - memenuhi kriteria sepenuhnya\n"
    "  Separa - memenuhi sebahagian sahaja (separuh markah)\n"
    "  Tidak - tidak memenuhi kriteria\n\n"
    "Tandakan seperti anda menanda jawapan murid Tahun 5 dalam UPKK. Sila tandakan seorang diri, tanpa "
    "berbincang dengan guru lain sehingga semua guru selesai.\n\n"
    "Jawapan ini ialah contoh jawapan yang disediakan untuk kajian, bukan jawapan murid sebenar. "
    "Tiada maklumat murid digunakan.")
FORM_CHOICES = ["Ya - memenuhi sepenuhnya", "Separa - sebahagian sahaja", "Tidak - tidak memenuhi"]
FORM_NAME = "Nama guru"
SUBJECT_NAMES = {"fiqh": "Ibadah (Fiqh)", "jawi": "Jawi", "tajwid": "Tajwid"}

GS_TEMPLATE = """// Creates the teacher marking Google Form. Generated by scripts/teacher_sheet.py form; do not edit.
// 1. Open https://script.google.com and click "New project".
// 2. Delete everything in the editor, paste this whole file, then click Save.
// 3. Choose the function createForm at the top and click Run (allow the permissions it asks for).
// 4. Open "Execution log": it prints the link to send to the teachers and the link to the responses sheet.

var FORM_TITLE = __TITLE__;
var FORM_INTRO = __INTRO__;
var CHOICES = __CHOICES__;
var NAME = __NAME__;
var ANSWERS = __ANSWERS__;

function createForm() {
  var form = FormApp.create(FORM_TITLE);
  form.setDescription(FORM_INTRO)
      .setProgressBar(true)
      .setPublishingSummary(false)
      .setAllowResponseEdits(true)
      .setShowLinkToRespondAgain(false);
  form.addTextItem().setTitle(NAME).setHelpText('Nama penuh anda (setiap guru menggunakan nama yang berbeza).').setRequired(true);

  ANSWERS.forEach(function (a, i) {
    form.addPageBreakItem()
        .setTitle('Jawapan ' + (i + 1) + ' daripada ' + ANSWERS.length + ' (' + a.id + ')')
        .setHelpText(a.subject + ' | Tahap ' + a.level + '\\n\\nSOALAN:\\n' + a.question +
                     '\\n\\nJAWAPAN RUJUKAN:\\n' + a.reference + '\\n\\nJAWAPAN MURID:\\n' + a.answer);
    a.criteria.forEach(function (c) {
      form.addMultipleChoiceItem()
          .setTitle(a.id + ' K' + c.no + ': ' + c.text + ' (' + c.marks + ' markah)')
          .setHelpText('Jawapan murid: ' + a.answer)
          .setChoiceValues(CHOICES)
          .setRequired(true);
    });
    form.addParagraphTextItem().setTitle(a.id + ' Komen (pilihan)');
  });

  var sheet = SpreadsheetApp.create(FORM_TITLE + ' (Respons)');
  form.setDestination(FormApp.DestinationType.SPREADSHEET, sheet.getId());
  Logger.log('Send this link to every teacher: ' + form.getPublishedUrl());
  Logger.log('Edit the form here: ' + form.getEditUrl());
  Logger.log('Responses sheet: ' + sheet.getUrl());
}
"""


def form(only: set[tuple[str, int]] | None = None, title: str = FORM_TITLE, intro: str = FORM_INTRO,
         filename: str = "create_form.gs") -> Path:
    """Apps Script that builds the marking Google Form; `only` limits it to some (answer, criterion) pairs."""
    qs = load_questions()
    items = json.loads(KEY.read_text(encoding="utf-8"))
    answers = []
    for it in items:
        q = qs[it["question_id"]]
        crits = [{"no": n, "text": c["criterion"], "marks": c["marks"]} for n, c in enumerate(q["rubric"], 1)
                 if only is None or (it["answer_id"], n) in only]
        if not crits:
            continue
        answers.append({"id": it["answer_id"], "subject": SUBJECT_NAMES.get(q["subject"], q["subject"]),
                        "level": q["level"], "question": q["question_rumi"],
                        "reference": q.get("reference_answer_rumi", ""), "answer": it["answer"], "criteria": crits})
    js = lambda v: json.dumps(v, ensure_ascii=False)  # noqa: E731  (JSON is valid JavaScript)
    script = (GS_TEMPLATE.replace("__TITLE__", js(title)).replace("__INTRO__", js(intro))
              .replace("__CHOICES__", js(FORM_CHOICES)).replace("__NAME__", js(FORM_NAME))
              .replace("__ANSWERS__", json.dumps(answers, ensure_ascii=False, indent=1)))
    FORM_DIR.mkdir(parents=True, exist_ok=True)
    dest = FORM_DIR / filename
    dest.write_text(script, encoding="utf-8")
    print(f"{len(answers)} answers, {sum(len(a['criteria']) for a in answers)} questions -> {dest}")
    return dest


def from_form(path: Path) -> None:
    """Split the downloaded Google Form responses CSV into one filled sheet per teacher, then run agree.

    Teachers are told apart by the "Nama guru" answer (case and spaces ignored), so any number of
    teachers can use the same form. If one teacher submits twice, the later response wins.
    """
    qs = load_questions()
    items = json.loads(KEY.read_text(encoding="utf-8"))
    with path.open(encoding="utf-8-sig") as fh:
        responses = list(csv.DictReader(fh))
    latest: dict[str, dict] = {}
    for r in responses:                       # rows are in submission order; a later edit wins
        name = " ".join((r.get(FORM_NAME) or "").split())
        if name:
            latest[name.casefold()] = r
    if len(latest) < 2:
        sys.exit(f"need responses from at least 2 teachers in {path}, found {len(latest)}")
    crit = re.compile(r"^(T\d{3}) K(\d+):")
    note = re.compile(r"^(T\d{3}) Komen")
    paths, names = [], []
    for i, r in enumerate(latest.values(), 1):
        mets, comments = {}, {}
        for col, val in r.items():
            if m := crit.match(col or ""):
                word = (val or "").split(" ")[0].strip().lower()
                mets[(m[1], int(m[2]))] = word if word in VALID else ""
            elif m := note.match(col or ""):
                comments[m[1]] = (val or "").strip()
        dest = OUT_DIR / f"guru_{i}_filled.csv"
        _write_sheet(dest, items, qs, mets, comments)
        names.append(" ".join(r[FORM_NAME].split()))
        paths.append(dest)
        print(f"guru_{i} ({names[-1]}): {sum(1 for v in mets.values() if v)} criteria -> {dest}")
    agree(paths, OUT_DIR / "marking_final.csv", names)
    print()
    labels()


def report() -> None:
    from evaluate import fmt_row

    res = json.loads((RES / "evaluation_teacher.json").read_text(encoding="utf-8"))["part_a"]
    agr_path = OUT_DIR / "agreement.json"
    agr = json.loads(agr_path.read_text(encoding="utf-8")) if agr_path.exists() else None
    key = {it["answer_id"]: it for it in json.loads(KEY.read_text(encoding="utf-8"))}
    teacher = {it["answer_id"]: it for it in json.loads((OUT_DIR / "teacher_test.json").read_text(encoding="utf-8"))}
    chosen = res["chosen"]["name"]
    c = res["configs"][chosen]
    o = c["overall"]
    head = ("| Group | n | Exact | Within 1 mark (2+ marks) | MAE (marks) | MAE % | QWK | Criterion acc | Over-marked | Under-marked |\n"
            "|---|---|---|---|---|---|---|---|---|---|")
    by_kind: dict[str, int] = defaultdict(int)
    by_subject: dict[str, int] = defaultdict(int)
    for it in teacher.values():
        by_kind[it["kind"]] += 1
        by_subject[it["question_id"].split("_")[0]] += 1

    md = ["# Teacher-marked evaluation report", "",
          f"System scoring configuration: `{chosen}`. Reference marks: {agr['raters'] if agr else 'the'} KAFA teachers "
          "marked every answer blind and independently; the final mark is the majority mark, and criteria with no "
          "majority were settled by discussion.", "",
          "> The answers are not from real pupils (teachers could not release pupil work). They are AI-written "
          "pupil-style answers, rule-built answers and researcher-written answers; only the marks are human.", "",
          "## 1. Test set", "",
          f"- Answers: {len(teacher)} ({', '.join(f'{SUBJECT_NAMES.get(k, k)} {v}' for k, v in sorted(by_subject.items()))})",
          f"- Answer types: {', '.join(f'{k} {v}' for k, v in sorted(by_kind.items()))}", ""]
    md += ["## 2. Agreement between the teachers", ""]
    if agr:
        pair = " (mean of all teacher pairs)" if agr.get("raters", 2) > 2 else ""
        md += [f"- Teachers: {agr.get('raters', 2)}",
               f"- Criteria marked by every teacher: {agr['criteria_both']} of {agr['criteria_total']}",
               f"- Exact agreement (all teachers the same): {agr['exact']:.1%}",
               f"- Cohen's kappa{pair}: {agr['kappa']:.3f} (quadratic weighted: {agr['qwk']:.3f})",
               *([f"- Fleiss' kappa (all teachers together): {agr['fleiss']:.3f}"] if "fleiss" in agr else []),
               f"- Same total score from every teacher: {agr['same_score']} of {agr['answers']} answers",
               f"- Criteria with no majority, settled by discussion: {agr['to_discuss']}", ""]
    else:
        md += ["_Not available: run `teacher_sheet.py agree` (or `from-form`) first._", ""]
    md += ["## 3. System vs teachers", "", head]
    md += [fmt_row(name, cfg["overall"]) for name, cfg in res["configs"].items()]
    for group, title in (("by_subject", "By subject"), ("by_level", "By level"), ("by_kind", "By answer type")):
        md += ["", f"### {title}", "", head] + [fmt_row(k, m) for k, m in c[group].items()]

    traps = c["by_kind"].get("keyword_illusion")
    md += ["", "## 4. Keyword illusion check", ""]
    if traps:
        md += [f"On {traps['items']} fluent-but-wrong answers (right words, wrong ruling) the system gave more marks "
               f"than the teachers on {traps['over_marked']:.0%} of answers (exact agreement {traps['item_exact']:.0%}).", ""]
    agr_target = f"{agr['qwk']:.3f}" if agr else "n/a"
    md += ["## 5. Blueprint targets", "", "| Measure | Target | Result | Met? |", "|---|---|---|---|",
           f"| QWK with teacher marks | at least 0.70 | {o['qwk_band']:.3f} | {'yes' if o['qwk_band'] >= 0.70 else 'no'} |",
           f"| Adjacent agreement (within 1 mark, answers worth 2+ marks) | at least 85% | {o['within_1']:.1%} | {'yes' if o['within_1'] >= 0.85 else 'no'} |",
           f"| MAE | low | {o['mae_marks']:.2f} marks ({o['mae_pct']}%) | - |",
           f"| Teacher vs teacher QWK, mean of pairs (for comparison) | - | {agr_target} | - |", ""]
    md += ["## 6. Largest disagreements", "", "| ID | Type | Answer | Teachers | System | Max |", "|---|---|---|---|---|---|"]
    for w in res["worst"]:
        t = teacher.get(w["answer_id"], {})
        ans = t.get("answer", "").replace("|", "/").replace("\n", " ")
        md.append(f"| {w['answer_id']} | {key.get(w['answer_id'], {}).get('kind', '')} | {ans[:80]} | "
                  f"{w['gold']} | {w['pred']} | {w['max']} |")
    dest = RES / "teacher_report.md"
    dest.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"report -> {dest}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "export"
    if cmd == "export":
        export()
    elif cmd == "agree" and len(sys.argv) >= 4:
        agree([Path(a) for a in sys.argv[2:]], OUT_DIR / "marking_final.csv")
    elif cmd == "import" and len(sys.argv) >= 3:
        import_(Path(sys.argv[2]))
    elif cmd == "form":
        form()
    elif cmd == "from-form" and len(sys.argv) >= 3:
        from_form(Path(sys.argv[2]))
    elif cmd == "report":
        report()
    elif cmd == "labels":
        labels()
    elif cmd == "adjudication-form":
        adjudication_form()
    elif cmd == "from-adjudication" and len(sys.argv) >= 3:
        from_adjudication(Path(sys.argv[2]))
    else:
        sys.exit(__doc__)
