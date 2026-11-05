"""Jawi reading test for the LLMs (Experiment plan v3, Phase 3.2): can a model read and write Jawi at all?

30 single words from the Jawi textbook's own tables (data/knowledge/jawi/*.md, columns "Rumi ... | Jawi ..."),
drawn once with a fixed seed: 15 spelling items (Rumi -> Jawi) and 15 reading items (Jawi -> Rumi). The answer
is scored against the textbook spelling: exact match (after removing harakat and unifying letter variants
such as ڬ/ݢ and ک/ك) and character error rate. Every model gets the same items and prompt.

Usage: .venv\\Scripts\\python eval\\jawi_reading.py fanar [haiku luna llama qwen sealion]
  -> eval/results/jawi_reading.json (results per model are kept, a model's run replaces its old one) and .md
Open-weight models need their Colab server running (notebooks/open_models_colab_server.ipynb).
"""
from __future__ import annotations

import json
import random
import re
import sys
import unicodedata
from pathlib import Path

import numpy as np
from rapidfuzz.distance import Levenshtein

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.app.config import get_settings  # noqa: E402
from backend.app.llm_api import MODELS, LLMError, complete, spent_usd  # noqa: E402

RES = ROOT / "eval" / "results"
OUT = RES / "jawi_reading.json"
N, SEED = 15, 7
MAX_TOKENS = 1000     # room for models that reason before answering (GPT-6 Luna); the answer is one word
SYSTEM = "Anda guru Jawi sekolah KAFA. Jawab dengan SATU perkataan sahaja, tanpa penerangan."
ASK = {"spell": "Tulis perkataan ini dalam tulisan Jawi: {w}", "read": "Tulis perkataan Jawi ini dalam tulisan Rumi: {w}"}
_ARABIC = re.compile(r"[؀-ۿݐ-ݿࢠ-ࣿ]")
_MARKS = re.compile(r"[ً-ٰٟـ]")
VARIANTS = str.maketrans({"ڬ": "ݢ", "ک": "ك", "ی": "ي", "ى": "ي", "ھ": "ه", "ۀ": "ه", "ٴ": "ء"})


def pairs() -> list[tuple[str, str]]:
    """(Rumi word, Jawi word) from every table column pair "Rumi ... | Jawi ..." in the Jawi notes."""
    out = []
    for f in sorted((Path(get_settings().knowledge_dir) / "jawi").glob("*.md")):
        head = None
        for line in f.read_text(encoding="utf-8").splitlines():
            if not line.startswith("|"):
                head = None
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if head is None:
                head = [i for i in range(len(cells) - 1)
                        if cells[i].startswith("Rumi") and cells[i + 1].lower().startswith("jawi")]
                continue
            for i in head:
                if i + 1 < len(cells):
                    r, j = cells[i], cells[i + 1]
                    if re.fullmatch(r"[a-z]+(-[a-z]+)?", r) and len(r) >= 4 and re.fullmatch(r"\S+", j) and _ARABIC.search(j):
                        out.append((r, j))
    return sorted(set(out))


def items() -> list[dict]:
    rng = random.Random(SEED)
    chosen = rng.sample(pairs(), 2 * N)
    return ([{"id": f"spell{i + 1:02d}", "task": "spell", "ask": r, "answer": j} for i, (r, j) in enumerate(chosen[:N])]
            + [{"id": f"read{i + 1:02d}", "task": "read", "ask": j, "answer": r} for i, (r, j) in enumerate(chosen[N:])])


def norm(s: str, task: str) -> str:
    """The answer word: for spelling the last Jawi word in the reply (so "Jawi for 'belai': بلاي" counts),
    for reading the first line after any "label:"."""
    s = unicodedata.normalize("NFKC", s).strip()
    if task == "spell":
        words = [w for w in re.findall(r"[^\s.,:;'\"`*()\[\]،]+", _MARKS.sub("", s)) if _ARABIC.search(w)]
        return words[-1].translate(VARIANTS) if words else ""
    line = s.splitlines()[0] if s else ""
    return line.rsplit(":", 1)[-1].strip(" .,'\"`*()[]").lower()


def run_model(model: str, its: list[dict]) -> dict:
    rows = []
    for it in its:
        try:
            c = complete(model, [{"role": "system", "content": SYSTEM}, {"role": "user", "content": ASK[it["task"]].format(w=it["ask"])}],
                         max_tokens=MAX_TOKENS, tag="jawi_reading")
            raw, err = c.text, ""
        except LLMError as e:
            raw, err = "", str(e)[:200]
        got, want = norm(raw, it["task"]), norm(it["answer"], it["task"])
        rows.append({**it, "reply": raw.strip()[:120], "exact": got == want, "cer": Levenshtein.distance(got, want) / len(want),
                     "error": err})
        if err and "not" in err and "Colab" in err:
            raise SystemExit(err)
    summ = {t: {"exact": float(np.mean([r["exact"] for r in rows if r["task"] == t])),
                "cer": float(np.mean([min(1.0, r["cer"]) for r in rows if r["task"] == t]))} for t in ASK}
    return {"label": MODELS[model].label, "summary": summ, "exact_all": float(np.mean([r["exact"] for r in rows])),
            "failed_calls": sum(bool(r["error"]) for r in rows), "rows": rows}


def markdown(res: dict) -> str:
    md = ["# Jawi reading test (Phase 3.2)", "",
          f"{2 * N} words from the Jawi textbook tables: {N} spelling (Rumi → Jawi) and {N} reading (Jawi → Rumi). "
          "Exact = same as the textbook (harakat removed, letter variants unified); CER = character error rate (lower is better).", "",
          "| Model | Spelling exact | Spelling CER | Reading exact | Reading CER | All exact | Failed calls |", "|---|---|---|---|---|---|---|"]
    for m in sorted(res["models"].values(), key=lambda x: -x["exact_all"]):
        s = m["summary"]
        md.append(f"| {m['label']} | {s['spell']['exact']:.0%} | {s['spell']['cer']:.0%} | {s['read']['exact']:.0%} | "
                  f"{s['read']['cer']:.0%} | {m['exact_all']:.0%} | {m['failed_calls']} |")
    md += ["", "## Items and replies", "", "| Item | Asked | Textbook | " + " | ".join(m["label"] for m in res["models"].values()) + " |",
           "|---|---|---|" + "---|" * len(res["models"])]
    for i, it in enumerate(res["items"]):
        md.append(f"| {it['id']} | {it['ask']} | {it['answer']} | " + " | ".join(
            ("✓ " if m["rows"][i]["exact"] else "✗ ") + m["rows"][i]["reply"].replace("|", "/").replace("\n", " ")[:40]
            for m in res["models"].values()) + " |")
    return "\n".join(md) + "\n"


def main(models: list[str]) -> None:
    spent0 = spent_usd()
    its = items()
    res = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {"models": {}}
    if res.get("items") and [i["id"] + i["ask"] for i in res["items"]] != [i["id"] + i["ask"] for i in its]:
        res = {"models": {}}            # the notes changed: the old results are for other items
    res["items"] = its
    for m in models:
        print(f"   {MODELS[m].label} ...", flush=True)
        res["models"][m] = run_model(m, its)
    res["spent"] = round(res.get("spent", 0) + spent_usd() - spent0, 4)
    OUT.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    OUT.with_suffix(".md").write_text(markdown(res), encoding="utf-8")
    print(markdown(res).split("\n## Items")[0])


if __name__ == "__main__":
    if len(sys.argv) < 2 or any(m not in MODELS for m in sys.argv[1:]):
        sys.exit(f"usage: jawi_reading.py MODEL [MODEL ...]   (models: {', '.join(MODELS)})")
    main(sys.argv[1:])
