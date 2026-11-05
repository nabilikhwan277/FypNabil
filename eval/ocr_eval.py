"""Ways of reading a scanned textbook page (Experiment plan v3, Phase 2.3 and 2.4).

10 pages of the three textbook PDFs, chosen so that each test unit is a WHOLE knowledge note (1-3 pages), whose
text in data/knowledge/ is the reference. Every method reads the same pages:
  pymupdf      the PDF's own text layer (no OCR)
  tesseract    Tesseract 5 OCR, Arabic model (ara) and Arabic-script model (Arabic: also Persian/Urdu letters)
  haiku, luna  vision LLM with the Library's page prompt (library.PAGE_RULES), the image the Library sends
Only Arabic-script text is scored (the books are printed in Jawi; the Rumi in the notes and in the LLM output is
a transliteration). Each line is Jawi, or Arabic (Quran, hadith, doa) when it carries harakat on at least 30% of
its letters, scored separately:
  CER   character error rate (edit distance / reference length), Jawi without harakat; Arabic with and without
  WER   word error rate (word-level edit distance)
  F1    word overlap regardless of order (a page read in a different order is not punished)
  plus [TIDAK JELAS] marks, seconds and API cost per page; per kind of page (2.4).
The reference notes were themselves transcribed with a vision LLM (Claude) and checked against the page, but
are not yet verified by a teacher (verified: false), so they may favour the Claude reader.

Usage: .venv\\Scripts\\python eval\\ocr_eval.py   -> eval/results/ocr_eval.json/.md, docs/figures/results/fig_4_15_ocr.png
(LLM pages cost about $0.002 each; outputs are cached in eval/cache/ocr/)
"""
from __future__ import annotations

import base64
import json
import re
import shutil
import subprocess
import sys
import time
import unicodedata
from collections import Counter
from pathlib import Path

import numpy as np
from rapidfuzz.distance import Levenshtein

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "eval"))

from backend.app.kb.chunking import load_note  # noqa: E402
from backend.app.library import IMAGE_EDGE, PAGE_RULES, PAGE_SCHEMA, SUBJECT_TEXT  # noqa: E402
from backend.app.llm_api import MODELS, complete, spent_usd  # noqa: E402

RES = ROOT / "eval" / "results"
CACHE = ROOT / "eval" / "cache" / "ocr"
TESSDATA = ROOT / "eval" / "cache" / "tessdata"
BOOKS = {"fiqh": "BUKU TEKS IBADAH KAFA JAKIM TAHUN 5.pdf", "jawi": "e-BOOK Buku Teks JAIS JAWI TAHUN 5.pdf",
         "tajwid": "e-BOOK Buku Teks JAIS TAJWID TAHUN 5.pdf"}
# the test notes and the kind of their pages (2.4), labelled by looking at each page
UNITS = [
    ("fiqh_b2_fadhilat_puasa", "text"),            # numbered list + a short hadith
    ("fiqh_b2_batal_puasa", "text"),               # numbered list in boxes
    ("fiqh_b2_puasa_wajib_sunat", "text"),         # two boxed lists
    ("fiqh_b2_hikmah_puasa", "picture"),           # half the page is pictures
    ("tajwid_b3_mad_iwadh", "quran"),              # rule box + Quran words and verses
    ("tajwid_b3_mad_silah_qasirah", "quran"),      # rule box + Quran verses
    ("jawi_b4_akronim_dilafaz", "table"),          # acronym tables, English and Rumi printed too
]
METHODS = {"pymupdf": "PyMuPDF text layer", "tess_ara": "Tesseract (ara)", "tess_arabic": "Tesseract (Arabic script)",
           "haiku": "Claude Haiku 5.5 vision", "luna": "GPT-6 Luna vision"}
UNCLEAR = "[TIDAK JELAS]"
A4_300DPI = 3508                     # long edge in pixels of an A4 page scanned at 300 dpi

# "- **Rumi:** ... | **Jawi:** ..." and "**Peraturan (Rumi):** ...": only the Jawi field is printed text
_RUMI_FIELD = re.compile(r"\*\*[^*]*Rumi[^*]*:\*\*.*?(?=\|\s*\*\*[^*]*Jawi|$)")

_ARABIC = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]+")
_MARKS = re.compile(r"[\u064B-\u065F\u0670\u06D6-\u06ED]")        # harakat and Quranic annotation signs
_DROP = re.compile(r"[\u0640\u060C\u061B\u061F\u066A-\u066D\u06D4\u0660-\u0669\u06F0-\u06F9\uFD3E\uFD3F]")


# ------------------------------------------------------------------ text -> scored lines
def arabic_lines(text: str) -> dict[str, list[str]]:
    """The Arabic-script part of each line, split into Jawi and Arabic (Quran/doa) lines."""
    out = {"jawi": [], "arabic": []}
    for line in unicodedata.normalize("NFKC", text.replace(UNCLEAR, " ")).splitlines():
        line = _RUMI_FIELD.sub(" ", line)
        words = [_DROP.sub("", w) for w in _ARABIC.findall(line)]
        words = [w for w in words if _MARKS.sub("", w)]
        if not words:
            continue
        s = " ".join(words)
        letters = len(_MARKS.sub("", s).replace(" ", ""))
        out["arabic" if len(_MARKS.findall(s)) >= 0.3 * letters else "jawi"].append(s)
    return out


def plain(s: str) -> str:
    return _MARKS.sub("", s)


def scores(ref: str, hyp: str) -> dict:
    rw, hw = ref.split(), hyp.split()
    common = sum((Counter(rw) & Counter(hw)).values())
    p, r = (common / len(hw) if hw else 0.0), (common / len(rw) if rw else 0.0)
    return {"cer": Levenshtein.distance(ref, hyp) / max(1, len(ref)), "wer": Levenshtein.distance(rw, hw) / max(1, len(rw)),
            "f1": 2 * p * r / (p + r) if p + r else 0.0, "precision": p, "recall": r,
            "ref_chars": len(ref), "hyp_chars": len(hyp)}


def compare(ref_text: str, hyp_text: str) -> dict:
    ref, hyp = arabic_lines(ref_text), arabic_lines(hyp_text)
    j = scores(plain(" ".join(ref["jawi"])), plain(" ".join(hyp["jawi"])))
    a = " ".join(ref["arabic"]), " ".join(hyp["arabic"])
    out = {"jawi": j}
    if a[0]:
        out["arabic"] = scores(*a)
        out["arabic_letters"] = scores(plain(a[0]), plain(a[1]))
    return out


# ------------------------------------------------------------------ reading a page
def page_image(subject: str, page: int, edge: int, png: bool = False) -> Path:
    """The page with its long edge `edge` pixels (the PDF pages are oversized, so dpi would mislead)."""
    import fitz
    path = CACHE / "images" / f"{subject}_{page:03d}_{edge}.{'png' if png else 'jpg'}"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        pg = fitz.open(ROOT / "text book" / BOOKS[subject])[page - 1]
        zoom = min(3.0, edge / max(pg.rect.width, pg.rect.height))
        pix = pg.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        pix.save(path) if png else pix.save(path, jpg_quality=85)
    return path


def tesseract_exe() -> str:
    for p in (shutil.which("tesseract"), r"C:\Program Files\Tesseract-OCR\tesseract.exe",
              str(Path.home() / "tesseract-env" / "Library" / "bin" / "tesseract.exe")):
        if p and Path(p).exists():
            return p
    raise SystemExit("Tesseract not found: install it (see EXPERIMENT_PLAN_V3.md 2.3)")


def read(method: str, subject: str, page: int) -> dict:
    """{text, seconds, cost} for one page, cached."""
    path = CACHE / method / f"{subject}_{page:03d}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    t0, cost = time.perf_counter(), 0.0
    if method == "pymupdf":
        import fitz
        text = fitz.open(ROOT / "text book" / BOOKS[subject])[page - 1].get_text()
    elif method.startswith("tess_"):
        lang = {"tess_ara": "ara", "tess_arabic": "Arabic"}[method]
        img = page_image(subject, page, edge=A4_300DPI, png=True)  # Tesseract's recommended resolution
        text = subprocess.run([tesseract_exe(), str(img), "stdout", "-l", lang, "--psm", "3",
                               "--tessdata-dir", str(TESSDATA)], capture_output=True, check=True).stdout.decode("utf-8")
    else:
        img = page_image(subject, page, edge=IMAGE_EDGE)  # exactly what the Library sends
        b64 = base64.b64encode(img.read_bytes()).decode()
        c = complete(method, [{"role": "system", "content": PAGE_RULES.format(kind_text="textbook", subject=SUBJECT_TEXT[subject])},
                              {"role": "user", "content": [{"type": "text", "text": f"Page {page} of the {subject} textbook."},
                                                           {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}]}],
                     schema=PAGE_SCHEMA, max_tokens=6000, tag=f"ocr_eval:{method}")
        text, cost = ((c.data or {}).get("markdown") or c.text or ""), c.cost
    out = {"text": text, "seconds": round(time.perf_counter() - t0, 2), "cost": cost}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


# ------------------------------------------------------------------ run
def mean(xs) -> float | None:
    xs = [x for x in xs if x is not None]
    return round(float(np.mean(xs)), 4) if xs else None


def pooled(rows: list[dict], part: str) -> dict | None:
    """Character-weighted CER/WER over units (errors / reference length), mean F1."""
    rs = [r["scores"][part] for r in rows if part in r["scores"]]
    if not rs:
        return None
    return {"cer": round(sum(x["cer"] * x["ref_chars"] for x in rs) / sum(x["ref_chars"] for x in rs), 4),
            "wer": mean(x["wer"] for x in rs), "f1": mean(x["f1"] for x in rs), "units": len(rs)}


def main() -> None:
    spent0 = spent_usd()
    units = []
    for note_id, kind in UNITS:
        subject = note_id.split("_")[0]
        note = load_note(ROOT / "data" / "knowledge" / subject / f"{note_id}.md")
        units.append({"note": note_id, "subject": subject, "kind": kind, "pages": list(note.meta["pdf_pages"]),
                      "reference": note.body})
    print(f"{len(units)} notes, {sum(len(u['pages']) for u in units)} pages", flush=True)
    rows = []
    for m in METHODS:
        for u in units:
            got = [read(m, u["subject"], p) for p in u["pages"]]
            text = "\n".join(g["text"] for g in got)
            rows.append({"method": m, "note": u["note"], "subject": u["subject"], "kind": u["kind"], "pages": len(u["pages"]),
                         "scores": compare(u["reference"], text), "unclear": text.count(UNCLEAR),
                         "seconds": sum(g["seconds"] for g in got), "cost": sum(g["cost"] for g in got),
                         "chars": len(text)})
        print(f"   {METHODS[m]} done", flush=True)
    summary = {}
    for m in METHODS:
        mine = [r for r in rows if r["method"] == m]
        pages = sum(r["pages"] for r in mine)
        summary[m] = {"label": METHODS[m], "pages": pages,
                      **{part: pooled(mine, part) for part in ("jawi", "arabic", "arabic_letters")},
                      "unclear": sum(r["unclear"] for r in mine),
                      "seconds_per_page": round(sum(r["seconds"] for r in mine) / pages, 2),
                      "cost_per_page": round(sum(r["cost"] for r in mine) / pages, 5),
                      "by_subject": {s: pooled([r for r in mine if r["subject"] == s], "jawi") for s in BOOKS},
                      "by_kind": {k: pooled([r for r in mine if r["kind"] == k], "jawi") for k in sorted({u[1] for u in UNITS})}}
    out = {"units": [{k: v for k, v in u.items() if k != "reference"} for u in units], "summary": summary, "rows": rows,
           "models": {m: MODELS[m].label for m in ("haiku", "luna")}, "spent": round(spent_usd() - spent0, 4)}
    (RES / "ocr_eval.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    (RES / "ocr_eval.md").write_text(markdown(out), encoding="utf-8")
    figure(out)
    print(markdown(out))
    print(f"-> {RES / 'ocr_eval.md'}  (this run ${out['spent']:.4f})")


def _p(v: dict | None, k: str, pct: bool = True) -> str:
    if not v or v.get(k) is None:
        return "–"
    return f"{v[k]:.1%}" if pct else f"{v[k]:.2f}"


def markdown(o: dict) -> str:
    s = o["summary"]
    n_pages = sum(len(u["pages"]) for u in o["units"])
    md = ["# Reading scanned textbook pages (Phase 2.3 / 2.4)", "",
          f"{n_pages} pages ({len(o['units'])} whole notes: " + ", ".join(f"{u['note']} p{','.join(map(str, u['pages']))}"
                                                                        for u in o["units"]) + "). Reference: the knowledge "
          "notes (AI-transcribed, checked against the page, not yet teacher-verified). Only Arabic-script text is scored. "
          "CER / WER: lower is better (above 100% = more wrong text than the reference holds); F1: higher is better.", "",
          "## Overall", "",
          "| Method | Jawi CER | Jawi WER | Jawi word F1 | Arabic CER (with harakat) | Arabic CER (letters only) | "
          "Arabic word F1 | [TIDAK JELAS] | Seconds / page | Cost / page |", "|---|---|---|---|---|---|---|---|---|---|"]
    for m, v in s.items():
        md.append(f"| {v['label']} | {_p(v['jawi'], 'cer')} | {_p(v['jawi'], 'wer')} | {_p(v['jawi'], 'f1', False)} | "
                  f"{_p(v['arabic'], 'cer')} | {_p(v['arabic_letters'], 'cer')} | {_p(v['arabic'], 'f1', False)} | "
                  f"{v['unclear']} | {v['seconds_per_page']:.1f} | ${v['cost_per_page']:.4f} |")
    for title, key, names in (("Jawi CER per subject", "by_subject", {"fiqh": "Ibadah", "jawi": "Jawi", "tajwid": "Tajwid"}),
                              ("Jawi CER per kind of page (2.4)", "by_kind", None)):
        cols = list(next(iter(s.values()))[key])
        md += ["", f"## {title}", "", "| Method | " + " | ".join((names or {}).get(c, c) for c in cols) + " |",
               "|---|" + "---|" * len(cols)]
        md += [f"| {v['label']} | " + " | ".join(_p(v[key][c], "cer") for c in cols) + " |" for v in s.values()]
    md += ["", "## Per note", "", "| Method | Note | Kind | Jawi CER | Jawi F1 | Arabic CER | [TIDAK JELAS] |", "|---|---|---|---|---|---|---|"]
    for r in o["rows"]:
        sc = r["scores"]
        md.append(f"| {METHODS[r['method']]} | {r['note']} | {r['kind']} | {_p(sc['jawi'], 'cer')} | {_p(sc['jawi'], 'f1', False)} | "
                  f"{_p(sc.get('arabic'), 'cer')} | {r['unclear']} |")
    return "\n".join(md) + "\n"


def figure(o: dict) -> None:
    import make_figures as MF
    plt = MF.plt
    s = o["summary"]
    short = {"pymupdf": "PyMuPDF\ntext layer", "tess_ara": "Tesseract\n(ara)", "tess_arabic": "Tesseract\n(Arabic script)",
             "haiku": "Claude Haiku\n5.5 vision", "luna": "GPT-6 Luna\nvision"}
    labels = [short.get(m, v["label"]) for m, v in s.items()]
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.8), sharey=True)
    for ax, part, title in ((axes[0], "jawi", "Jawi text"), (axes[1], "arabic", "Arabic text (Quran, doa), with harakat")):
        vals = [min(1.5, (v[part] or {}).get("cer", 1.0)) for v in s.values()]
        ax.bar(labels, vals, color=[MF.C[i % len(MF.C)] for i in range(len(vals))], width=0.6, zorder=2,
               edgecolor="white", linewidth=1.5)
        for i, v in enumerate(vals):
            ax.text(i, v + 0.02, f"{v:.0%}", ha="center", va="bottom", fontsize=9, color=MF.INK)
        ax.set_title(title)
        ax.tick_params(axis="x", labelsize=8)
    axes[0].set_ylabel("Character error rate (lower is better)")
    fig.suptitle("Reading scanned KAFA textbook pages", fontweight="bold")
    MF.save(fig, "fig_4_15_ocr.png")


if __name__ == "__main__":
    main()
