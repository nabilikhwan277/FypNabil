"""Tanya Bulan as pupils get it: does the live chat decline off-syllabus questions and answer the textbook ones?

Phase 6 lowered the chat's gate from 0.55 to 0.35 and added the RAG study's decline rule to its prompt. The study
measured declining with GPT-6 Luna; this checks the live chat (backend/app/chat.py) with the model it really uses:
Qwen on Google Colab (link pasted on the website), Qwen on the laptop (KAFA_LOCAL_LLM=true), or no model at all
(--no-model: the textbook-only fallback). Same questions as the RAG evaluation (eval/rag_eval.py): 45 answerable
textbook questions and 24 out-of-syllabus questions (12 general, 12 near the syllabus).
For each: the best bge-m3 match (strong >= 0.55, weak 0.35-0.55, below 0.35), whether the reply declines
("Data ini tiada dalam pangkalan data saya."), whether it shows textbook sources, and the time. Free (no API model).

Usage: .venv\\Scripts\\python eval\\chat_gate_eval.py [--no-model]
       -> eval/results/chat_gate_eval.json and .md (chat_gate_eval_no_model.* with --no-model)
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "eval"))

import rag_eval as RE  # noqa: E402

from backend.app import chat, remote_llm  # noqa: E402
from backend.app.config import get_settings  # noqa: E402
from backend.app.kb.retriever import dense_search  # noqa: E402

RES = ROOT / "eval" / "results"
SID = -1   # a test pupil id for the chat's turn counter (nothing is saved)
NOTICES = ("tiada dalam pangkalan data saya.", "not in my database.")
LONG_EXTRA = 160   # more text than this after the notice is a real answer, not a one-sentence pointer to the teacher


def after_notice(reply: str) -> str:
    """What follows the decline notice. The chat puts the notice in front of whatever the model said, so a reply with
    the notice can still contain a full answer: this text tells the two apart."""
    low = reply.lower()
    for n in NOTICES:
        if n in low:
            return reply[low.index(n) + len(n):].strip()
    return ""


def model_in_use(no_model: bool) -> str:
    if no_model:
        remote_llm.endpoint = lambda: None                      # this run only: the saved link is left as it is
        get_settings().local_llm = False
        return "no model (textbook-only fallback)"
    if remote_llm.endpoint() is not None:
        st = remote_llm.check()
        if not st.get("ok"):
            sys.exit(f"The saved Colab link does not answer ({st.get('error')}). Start the Qwen notebook and paste its "
                     "new link on the website, remove the old link, or run with --no-model.")
        if "marker" in str(st.get("model", "")):
            sys.exit(f"The saved Colab link serves {st['model']} (the fine-tuned marker), not the chat model: start "
                     "notebooks/open_models_colab_server.ipynb with MODEL = Qwen and paste its link.")
        return f"Google Colab: {st.get('model')} ({st.get('gpu', '?')}, {st.get('precision', '?')})"
    if get_settings().local_llm:
        return f"Qwen on this laptop: {get_settings().llm_model_id}"
    sys.exit("No chat model: start Qwen on Colab and paste the link on the website (or set KAFA_LOCAL_LLM=true), "
             "or run with --no-model.")


def band(score: float) -> str:
    return "strong" if score >= chat.GATE_TEXTBOOK_ONLY else "weak" if score >= chat.GATE else "below"


def ask(text: str, subject: str | None) -> dict:
    chat.reset_turns(SID)
    top = dense_search(text, k=1, subject=subject)
    score = top[0].score if top else 0.0
    t0 = time.perf_counter()
    r = chat.ask(student_id=SID, message=text, subject=subject)
    declined = "tiada dalam pangkalan data" in r.reply.lower() or "not in my database" in r.reply.lower()
    return {"question": text, "subject": subject or "", "score": round(score, 3), "band": band(score),
            "declined": declined, "answered_anyway": declined and len(after_notice(r.reply)) > LONG_EXTRA,
            "sources": len(r.sources), "reply": r.reply, "seconds": round(time.perf_counter() - t0, 1)}


def main(no_model: bool) -> None:
    mode = model_in_use(no_model)
    print("model:", mode, flush=True)
    rows = []
    for q in RE.pick_questions(45):
        rows.append({"kind": "answerable", "id": q["id"], **ask(q["question_rumi"], q["subject"])})
        print(f"  {rows[-1]['band']:6} {'DECLINED' if rows[-1]['declined'] else 'answered'}  {q['id']}", flush=True)
    for text, kind in RE.OUT_OF_SYLLABUS:
        rows.append({"kind": kind, "id": "", **ask(text, None)})
        print(f"  {rows[-1]['band']:6} {'declined' if rows[-1]['declined'] else 'ANSWERED'}  {text[:50]}", flush=True)
    ans = [r for r in rows if r["kind"] == "answerable"]
    oos = [r for r in rows if r["kind"] != "answerable"]
    summary = {
        "answerable_answered": sum(not r["declined"] for r in ans), "answerable": len(ans),
        "oos_declined": sum(r["declined"] for r in oos), "oos": len(oos),
        "oos_declined_but_answered": sum(r["answered_anyway"] for r in oos),
        "oos_declined_by_kind": {k: f"{sum(r['declined'] for r in oos if r['kind'] == k)}/{sum(r['kind'] == k for r in oos)}"
                                 for k in ("general", "near")},
        "oos_answered_with_sources": sum(not r["declined"] and r["sources"] > 0 for r in oos),
        "by_band": {b: {"answerable": sum(r["band"] == b for r in ans),
                        "answerable_declined": sum(r["band"] == b and r["declined"] for r in ans),
                        "oos": sum(r["band"] == b for r in oos), "oos_declined": sum(r["band"] == b and r["declined"] for r in oos)}
                    for b in ("strong", "weak", "below")},
        "seconds_mean": round(sum(r["seconds"] for r in rows) / len(rows), 1),
    }
    res = {"date": datetime.now(timezone.utc).isoformat(timespec="seconds"), "model": mode,
           "gates": {"gate": chat.GATE, "textbook_only": chat.GATE_TEXTBOOK_ONLY}, "summary": summary, "rows": rows}
    out = RES / ("chat_gate_eval_no_model.json" if no_model else "chat_gate_eval.json")
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    out.with_suffix(".md").write_text(markdown(res), encoding="utf-8")
    print(markdown(res).split("## Every")[0])


def markdown(res: dict) -> str:
    s = res["summary"]
    md = [f"# Tanya Bulan: declining off-syllabus questions ({res['model']})", "",
          f"Gate {res['gates']['gate']} (a model answers with the decline rule); textbook-only fallback "
          f"{res['gates']['textbook_only']}. Questions of the RAG evaluation. Run {res['date']}.", "",
          "| | Result |", "|---|---|",
          f"| Textbook questions answered | {s['answerable_answered']} of {s['answerable']} |",
          f"| Off-syllabus questions declined | {s['oos_declined']} of {s['oos']} (general {s['oos_declined_by_kind']['general']}, "
          f"near the syllabus {s['oos_declined_by_kind']['near']}) |",
          f"| ...of those, the reply also answered from general knowledge (more than {LONG_EXTRA} characters after the notice) | "
          f"{s['oos_declined_but_answered']} |",
          f"| Off-syllabus answered with textbook sources (the risky case) | {s['oos_answered_with_sources']} |",
          f"| Mean time per question | {s['seconds_mean']} s |", "",
          "| Best match | Textbook questions | of them declined | Off-syllabus | of them declined |", "|---|---|---|---|---|"]
    names = {"strong": "strong (≥ 0.55)", "weak": "weak (0.35–0.55)", "below": "below 0.35"}
    md += [f"| {names[b]} | {v['answerable']} | {v['answerable_declined']} | {v['oos']} | {v['oos_declined']} |"
           for b, v in s["by_band"].items()]
    md += ["", "## Every question", "", "| Kind | Question | Match | Declined | Sources | Reply |", "|---|---|---|---|---|---|"]
    for r in res["rows"]:
        reply = r["reply"].replace("|", "/").replace("\n", " ")
        md.append(f"| {r['kind']} | {r['question'][:70]} | {r['score']:.2f} ({r['band']}) | {'yes' if r['declined'] else 'no'} "
                  f"| {r['sources']} | {reply[:160]}{'…' if len(reply) > 160 else ''} |")
    return "\n".join(md) + "\n"


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-model", action="store_true", help="test the textbook-only fallback (no Qwen)")
    main(ap.parse_args().no_model)
