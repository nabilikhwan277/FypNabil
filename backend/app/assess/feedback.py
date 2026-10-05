"""Adaptive feedback.

Template-first: every fact shown to the student (what was missed, the correct
answer, the textbook page) comes from the rubric, the reference answer and the
note metadata, never from free LLM text. The LLM may add ONE short encouraging
sentence (Rumi), which passes a guard; otherwise a template is used.
"""
from __future__ import annotations

import re
from typing import Callable

from .. import prompts
from ..memory.db import TopicHistory, Update
from .jawi_text import is_arabic_script
from .rubric import RubricResult

Generate = Callable[[list[dict], int], str]

VERDICT = {
    3: {"rumi": "Syabas! Jawapan kamu tepat.", "jawi": "شاباس! جواڤن کامو تڤت."},
    2: {"rumi": "Bagus! Hampir betul, sedikit lagi.", "jawi": "باݢوس! همڤير بتول، سديکيت لاݢي."},
    1: {"rumi": "Cuba lagi, kamu boleh!", "jawi": "چوبا لاݢي، کامو بوليه!"},
}
ENCOURAGE = {
    3: {"rumi": "Teruskan usaha, kamu memang hebat!", "jawi": "تروسکن اوسها، کامو میمڠ هيبت!"},
    2: {"rumi": "Usaha yang baik, teruskan belajar!", "jawi": "اوسها يڠ باءيق، تروسکن بلاجر!"},
    1: {"rumi": "Jangan putus asa, setiap cubaan membuat kamu lebih pandai.",
        "jawi": "جاڠن ڤوتوس اس، ستياڤ چوباءن ممبوات کامو لبيه ڤنداي."},
}
BAND = {3: "markah penuh", 2: "separuh markah atau lebih", 1: "markah rendah"}


def _mistake_line(c: dict) -> dict:
    crit = c["criterion"]
    if c["met"] == "separa":
        return {"criterion": crit, "status": "separa",
                "rumi": f"Hampir betul: {crit}", "jawi": f"همڤير بتول: {crit}"}
    return {"criterion": crit, "status": "tidak",
            "rumi": f"Belum disebut atau belum tepat: {crit}", "jawi": f"بلوم دسبوت اتاو بلوم تڤت: {crit}"}


def _suggestion(mastery: float, percent: float, upd: Update, level: int) -> dict:
    if upd.unlocked:
        return {"rumi": f"Tahniah! Tahap {upd.level_after} sudah dibuka. Jom cuba soalan yang lebih mencabar.",
                "jawi": f"تهنية! تاهڤ {upd.level_after} سوده دبوک. جوم چوبا سوءالن يڠ لبيه منچابر.",
                "action": "next_level", "level": upd.level_after}
    if mastery < 0.4:
        return {"rumi": "Baca semula nota topik ini, kemudian cuba soalan Tahap 1 yang mudah.",
                "jawi": "باچ سمولا نوتا توڤيق اين، کمودين چوبا سوءالن تاهڤ 1 يڠ موده.",
                "action": "read_note", "level": 1}
    if mastery < 0.7 or percent < 100:
        return {"rumi": "Lihat jawapan betul di atas, kemudian cuba soalan yang serupa.",
                "jawi": "ليهت جواڤن بتول دأتس، کمودين چوبا سوءالن يڠ سروڤا.",
                "action": "similar", "level": level}
    return {"rumi": "Hebat! Teruskan dengan soalan seterusnya.",
            "jawi": "هيبت! تروسکن دڠن سوءالن ستروسڽ.",
            "action": "continue", "level": upd.level_after}


_SENTENCE_END = re.compile(r"(?<=[.!?])\s")
_BANNED = re.compile(r"\d|harakat|hukum|wajib|sunat|haram|rakaat|ejaan|huruf", re.I)


def guard_encouragement(text: str) -> str | None:
    """Accept a short, fact-free, Rumi sentence; otherwise None."""
    t = (text or "").strip().strip('"').strip()
    t = _SENTENCE_END.split(t)[0].strip() if t else ""
    if not t or len(t) > 160 or len(t.split()) > 24:
        return None
    if is_arabic_script(t) or _BANNED.search(t) or "\n" in t:
        return None
    # Reject looping output ("janganlah kamu ..., janganlah kamu ..., ...").
    words = t.lower().split()
    trigrams = [tuple(words[i:i + 3]) for i in range(len(words) - 2)]
    if len(trigrams) != len(set(trigrams)):
        return None
    return t


def build_feedback(
    *,
    question: dict,
    rubric: RubricResult,
    history: TopicHistory,
    update: Update,
    source: dict,
    generate: Generate | None = None,
) -> dict:
    percent = rubric.percent
    stars = update.stars
    criteria = [c.__dict__ for c in rubric.criteria]
    mistakes = [_mistake_line(c) for c in criteria if c["awarded"] < c["marks"]]

    encouragement = dict(ENCOURAGE[stars])
    encouragement["source"] = "template"
    if generate is not None:
        raw = generate([{"role": "user", "content": prompts.render(
            "encourage", topic=source.get("topic_rumi", ""), band=BAND[stars])}], 40)
        ok = guard_encouragement(raw)
        if ok:
            encouragement = {"rumi": ok, "jawi": ENCOURAGE[stars]["jawi"], "source": "llm"}

    repeated = [m for m in history.repeated_mistakes if any(m == x["criterion"] for x in mistakes)]
    repeated_text = None
    if repeated:
        joined = "; ".join(repeated)
        repeated_text = {"rumi": f"Kamu pernah tertinggal perkara ini sebelum ini: {joined}. Cuba ingat baik-baik!",
                         "jawi": f"کامو ڤرنه ترتيڠݢل ڤرکارا اين سبلوم اين: {joined}. چوبا ايڠت باءيق٢!"}

    return {
        "score": rubric.score,
        "max_marks": rubric.max_marks,
        "percent": percent,
        "stars": stars,
        "xp_gained": update.xp_gained,
        "verdict": VERDICT[stars],
        "mistakes": mistakes,
        "correct_answer": {"rumi": question.get("reference_answer_rumi", ""),
                           "jawi": question.get("reference_answer_jawi", "")},
        "source": source,
        "repeated": repeated_text,
        "suggestion": _suggestion(update.mastery_after, percent, update, int(question["level"])),
        "encouragement": encouragement,
        "mastery": {"before": update.mastery_before, "after": update.mastery_after},
        "level": {"before": update.level_before, "after": update.level_after, "unlocked": update.unlocked},
    }
