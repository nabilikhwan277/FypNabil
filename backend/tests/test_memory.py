from datetime import date

import pytest

from backend.app.memory.db import MemoryStore, TopicHistory, compute_update, stars_for

Q = {"id": "t_q1", "topic_id": "t", "subject": "tajwid", "level": 1}


def rubric(percent, missed=()):
    crit = [{"criterion": "A", "marks": 1, "awarded": 0 if "A" in missed else 1},
            {"criterion": "B", "marks": 1, "awarded": 0 if "B" in missed else 1}]
    score = sum(c["awarded"] for c in crit)
    return {"score": score, "max_marks": 2, "percent": percent, "criteria": crit}


def save(mem, sid, percent, missed=(), level=1, day=date(2026, 9, 1)):
    return mem.record_attempt(student_id=sid, question={**Q, "level": level}, answer="x",
                              rubric=rubric(percent, missed), feedback={}, trace=[], latency_ms=5, today=day)


@pytest.fixture
def mem():
    return MemoryStore(":memory:")


def test_stars():
    assert [stars_for(p) for p in (0, 49, 50, 99, 100)] == [1, 1, 2, 2, 3]


def test_compute_update_ema_and_unlock():
    u = compute_update(TopicHistory("t"), 1, 80)
    assert u.mastery_after == 0.8 and u.level_after == 1       # first attempt: mastery = score
    h = TopicHistory("t", mastery=0.8, attempts=2, level_unlocked=1, recent_at_level=[0.8, 0.6])
    u = compute_update(h, 1, 100)
    assert u.mastery_after == round(0.7 * 0.8 + 0.3 * 1.0, 4)
    assert u.level_after == 2 and u.unlocked                  # avg(0.8,0.6,1.0)=0.8 >= 0.7
    low = TopicHistory("t", mastery=0.5, attempts=2, level_unlocked=1, recent_at_level=[0.5, 0.5])
    assert compute_update(low, 1, 100).level_after == 1       # avg 0.67 < 0.7
    assert compute_update(h, 2, 100).level_after == 1          # answering a lower/other level never unlocks


def test_student_is_unique_per_name_and_class(mem):
    a = mem.get_or_create_student("Aisyah", "5 Bestari")
    b = mem.get_or_create_student(" Aisyah ", "5 Bestari")
    c = mem.get_or_create_student("Aisyah", "5 Cemerlang")
    assert a["id"] == b["id"] != c["id"]
    with pytest.raises(ValueError):
        mem.get_or_create_student("  ")


def test_record_attempts_unlock_mistakes_and_progress(mem):
    sid = mem.get_or_create_student("Ali", "5A")["id"]
    save(mem, sid, 50, missed=("B",))
    save(mem, sid, 100, day=date(2026, 9, 2))
    r = save(mem, sid, 100, missed=(), day=date(2026, 9, 3))
    assert r["update"]["unlocked"] and r["update"]["level_after"] == 2
    h = mem.history(sid, "t")
    assert h.level_unlocked == 2 and h.attempts == 3 and h.recent_at_level == []  # nothing at level 2 yet
    p = mem.progress(sid)
    assert p["streak_days"] == 3
    assert p["xp"] == (10 * 2 + 2) + (10 * 3 + 2) * 2
    assert {"langkah_pertama", "tiga_bintang", "tahap_2", "rajin_3_hari"} <= set(p["badges"])


def test_repeated_mistakes_need_two_misses(mem):
    sid = mem.get_or_create_student("Siti", "5A")["id"]
    save(mem, sid, 50, missed=("B",))
    assert mem.history(sid, "t").repeated_mistakes == []
    save(mem, sid, 50, missed=("B",))
    assert mem.history(sid, "t").repeated_mistakes == ["B"]


def test_streak_resets_after_gap(mem):
    sid = mem.get_or_create_student("Abu", "5A")["id"]
    save(mem, sid, 100, day=date(2026, 9, 1))
    save(mem, sid, 100, day=date(2026, 9, 1))
    assert mem.progress(sid)["streak_days"] == 1
    save(mem, sid, 100, day=date(2026, 9, 5))
    assert mem.progress(sid)["streak_days"] == 1
