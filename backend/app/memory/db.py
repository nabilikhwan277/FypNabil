"""Student learning memory in SQLite (stdlib sqlite3).

Tables: students, attempts, mistakes, topic_mastery, progress.
Rules
- Mastery per topic, exponential moving average of the percent score (0-1):
  first attempt: mastery = p; later: mastery = 0.7*old + 0.3*p.
- Level unlock: the next level opens when the student has >= 3 attempts at
  their current highest level in that topic and the average of the last 3 is
  >= 70%. Max level 3.
- XP = 10 per star + 2 for trying. Streak counts consecutive active days.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

EMA_OLD = 0.7
UNLOCK_WINDOW = 3
UNLOCK_THRESHOLD = 0.70
MAX_LEVEL = 3
REPEAT_MIN = 2  # a criterion missed this many times is a "repeated mistake"

SCHEMA = """
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    kelas TEXT NOT NULL DEFAULT '',
    avatar TEXT NOT NULL DEFAULT '',
    script_pref TEXT NOT NULL DEFAULT 'rumi',
    created_at TEXT NOT NULL,
    UNIQUE(name, kelas)
);
CREATE TABLE IF NOT EXISTS attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(id),
    question_id TEXT NOT NULL,
    topic_id TEXT NOT NULL,
    subject TEXT NOT NULL,
    level INTEGER NOT NULL,
    answer TEXT NOT NULL,
    score REAL NOT NULL,
    max_marks REAL NOT NULL,
    percent REAL NOT NULL,
    criteria_json TEXT NOT NULL,
    feedback_json TEXT NOT NULL,
    react_trace_json TEXT NOT NULL,
    latency_ms INTEGER NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_attempts_student_topic ON attempts(student_id, topic_id, level);
CREATE TABLE IF NOT EXISTS mistakes (
    student_id INTEGER NOT NULL REFERENCES students(id),
    topic_id TEXT NOT NULL,
    criterion TEXT NOT NULL,
    count INTEGER NOT NULL DEFAULT 0,
    last_seen TEXT NOT NULL,
    PRIMARY KEY (student_id, topic_id, criterion)
);
CREATE TABLE IF NOT EXISTS topic_mastery (
    student_id INTEGER NOT NULL REFERENCES students(id),
    topic_id TEXT NOT NULL,
    subject TEXT NOT NULL,
    mastery REAL NOT NULL,
    attempts INTEGER NOT NULL,
    level_unlocked INTEGER NOT NULL DEFAULT 1,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (student_id, topic_id)
);
CREATE TABLE IF NOT EXISTS progress (
    student_id INTEGER PRIMARY KEY REFERENCES students(id),
    xp INTEGER NOT NULL DEFAULT 0,
    streak_days INTEGER NOT NULL DEFAULT 0,
    last_active_date TEXT,
    badges_json TEXT NOT NULL DEFAULT '[]'
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class TopicHistory:
    topic_id: str
    mastery: float = 0.0
    attempts: int = 0
    level_unlocked: int = 1
    recent_at_level: list[float] = field(default_factory=list)  # last scores at level_unlocked (0-1)
    repeated_mistakes: list[str] = field(default_factory=list)
    recent_question_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Update:
    mastery_before: float
    mastery_after: float
    level_before: int
    level_after: int
    xp_gained: int
    stars: int

    @property
    def unlocked(self) -> bool:
        return self.level_after > self.level_before

    def to_dict(self) -> dict:
        d = asdict(self)
        d["unlocked"] = self.unlocked
        return d


def stars_for(percent: float) -> int:
    if percent >= 100:
        return 3
    if percent >= 50:
        return 2
    return 1  # always at least one star for trying


def compute_update(h: TopicHistory, level: int, percent: float) -> Update:
    """Pure function: what this attempt changes (used for feedback and saving)."""
    p = max(0.0, min(1.0, percent / 100))
    after = p if h.attempts == 0 else round(EMA_OLD * h.mastery + (1 - EMA_OLD) * p, 4)
    level_after = h.level_unlocked
    if level == h.level_unlocked and h.level_unlocked < MAX_LEVEL:
        window = ([*h.recent_at_level, p])[-UNLOCK_WINDOW:]
        if len(window) >= UNLOCK_WINDOW and sum(window) / len(window) >= UNLOCK_THRESHOLD:
            level_after = h.level_unlocked + 1
    stars = stars_for(percent)
    return Update(h.mastery, after, h.level_unlocked, level_after, 10 * stars + 2, stars)


class MemoryStore:
    def __init__(self, path: Path | str) -> None:
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.executescript(SCHEMA)
        # One connection is shared by FastAPI's worker threads, so every read and
        # write is serialised (concurrent use raises sqlite3.InterfaceError).
        self._lock = threading.RLock()

    # ---- students ----
    def get_or_create_student(self, name: str, kelas: str = "", avatar: str = "") -> dict:
        name, kelas = name.strip(), kelas.strip()
        if not name:
            raise ValueError("name is required")
        with self._lock, self._conn:
            row = self._conn.execute("SELECT * FROM students WHERE name=? AND kelas=?", (name, kelas)).fetchone()
            if row is None:
                cur = self._conn.execute(
                    "INSERT INTO students(name, kelas, avatar, created_at) VALUES (?,?,?,?)",
                    (name, kelas, avatar, _now()))
                self._conn.execute("INSERT INTO progress(student_id) VALUES (?)", (cur.lastrowid,))
                row = self._conn.execute("SELECT * FROM students WHERE id=?", (cur.lastrowid,)).fetchone()
            elif avatar and avatar != row["avatar"]:
                self._conn.execute("UPDATE students SET avatar=? WHERE id=?", (avatar, row["id"]))
                row = self._conn.execute("SELECT * FROM students WHERE id=?", (row["id"],)).fetchone()
        return dict(row)

    def get_student(self, student_id: int) -> dict | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM students WHERE id=?", (student_id,)).fetchone()
        return dict(row) if row else None

    # ---- history ----
    def history(self, student_id: int, topic_id: str) -> TopicHistory:
        h = TopicHistory(topic_id=topic_id)
        with self._lock:
            tm = self._conn.execute("SELECT * FROM topic_mastery WHERE student_id=? AND topic_id=?",
                                    (student_id, topic_id)).fetchone()
            if tm:
                h.mastery, h.attempts, h.level_unlocked = tm["mastery"], tm["attempts"], tm["level_unlocked"]
            rows = self._conn.execute(
                "SELECT percent FROM attempts WHERE student_id=? AND topic_id=? AND level=? ORDER BY id DESC LIMIT ?",
                (student_id, topic_id, h.level_unlocked, UNLOCK_WINDOW - 1)).fetchall()
            h.recent_at_level = [r["percent"] / 100 for r in reversed(rows)]
            h.repeated_mistakes = [r["criterion"] for r in self._conn.execute(
                "SELECT criterion FROM mistakes WHERE student_id=? AND topic_id=? AND count>=? ORDER BY count DESC LIMIT 3",
                (student_id, topic_id, REPEAT_MIN))]
            h.recent_question_ids = [r["question_id"] for r in self._conn.execute(
                "SELECT question_id FROM attempts WHERE student_id=? AND topic_id=? ORDER BY id DESC LIMIT 5",
                (student_id, topic_id))]
        return h

    def all_mastery(self, student_id: int) -> dict[str, dict]:
        with self._lock:
            return {r["topic_id"]: dict(r) for r in self._conn.execute(
                "SELECT * FROM topic_mastery WHERE student_id=?", (student_id,))}

    def progress(self, student_id: int) -> dict:
        with self._lock:
            row = self._conn.execute("SELECT * FROM progress WHERE student_id=?", (student_id,)).fetchone()
        if not row:
            return {"xp": 0, "streak_days": 0, "last_active_date": None, "badges": []}
        d = dict(row)
        d["badges"] = json.loads(d.pop("badges_json"))
        return d

    def recent_attempts(self, student_id: int, limit: int = 10) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, question_id, topic_id, subject, level, score, max_marks, percent, created_at "
                "FROM attempts WHERE student_id=? ORDER BY id DESC LIMIT ?", (student_id, limit)).fetchall()
        return [dict(r) for r in rows]

    # ---- write ----
    def record_attempt(self, *, student_id: int, question: dict, answer: str, rubric: dict,
                       feedback: dict, trace: list[dict], latency_ms: int, today: date | None = None) -> dict:
        """Persist one attempt and apply mastery / unlock / mistakes / XP updates.
        Returns {"attempt_id", "update", "new_badges"}."""
        topic_id = question["topic_id"]
        level = int(question["level"])
        percent = float(rubric["percent"])
        today = today or date.today()
        now = _now()
        with self._lock, self._conn:
            # Read and update under the same (re-entrant) lock so two answers cannot interleave.
            h = self.history(student_id, topic_id)
            upd = compute_update(h, level, percent)
            cur = self._conn.execute(
                "INSERT INTO attempts(student_id, question_id, topic_id, subject, level, answer, score, max_marks,"
                " percent, criteria_json, feedback_json, react_trace_json, latency_ms, created_at)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (student_id, question["id"], topic_id, question["subject"], level, answer, rubric["score"],
                 rubric["max_marks"], percent, json.dumps(rubric["criteria"], ensure_ascii=False),
                 json.dumps(feedback, ensure_ascii=False), json.dumps(trace, ensure_ascii=False), latency_ms, now))
            self._conn.execute(
                "INSERT INTO topic_mastery(student_id, topic_id, subject, mastery, attempts, level_unlocked, updated_at)"
                " VALUES (?,?,?,?,?,?,?) ON CONFLICT(student_id, topic_id) DO UPDATE SET"
                " mastery=excluded.mastery, attempts=topic_mastery.attempts+1,"
                " level_unlocked=excluded.level_unlocked, updated_at=excluded.updated_at",
                (student_id, topic_id, question["subject"], upd.mastery_after, 1, upd.level_after, now))
            for c in rubric["criteria"]:
                if c["awarded"] < c["marks"]:
                    self._conn.execute(
                        "INSERT INTO mistakes(student_id, topic_id, criterion, count, last_seen) VALUES (?,?,?,1,?)"
                        " ON CONFLICT(student_id, topic_id, criterion) DO UPDATE SET count=count+1, last_seen=excluded.last_seen",
                        (student_id, topic_id, c["criterion"], now))
            new_badges = self._update_progress(student_id, upd, today)
        return {"attempt_id": cur.lastrowid, "update": upd.to_dict(), "new_badges": new_badges}

    def _update_progress(self, student_id: int, upd: Update, today: date) -> list[str]:
        row = self._conn.execute("SELECT * FROM progress WHERE student_id=?", (student_id,)).fetchone()
        badges = json.loads(row["badges_json"]) if row else []
        last = date.fromisoformat(row["last_active_date"]) if row and row["last_active_date"] else None
        streak = row["streak_days"] if row else 0
        if last == today:
            pass
        elif last == today - timedelta(days=1):
            streak += 1
        else:
            streak = 1
        new = []
        for badge, earned in (("langkah_pertama", True), ("tiga_bintang", upd.stars == 3),
                              ("tahap_2", upd.level_after >= 2), ("tahap_3", upd.level_after >= 3),
                              ("rajin_3_hari", streak >= 3)):
            if earned and badge not in badges:
                badges.append(badge)
                new.append(badge)
        self._conn.execute(
            "INSERT INTO progress(student_id, xp, streak_days, last_active_date, badges_json) VALUES (?,?,?,?,?)"
            " ON CONFLICT(student_id) DO UPDATE SET xp=progress.xp+excluded.xp, streak_days=excluded.streak_days,"
            " last_active_date=excluded.last_active_date, badges_json=excluded.badges_json",
            (student_id, upd.xp_gained, streak, today.isoformat(), json.dumps(badges)))
        return new
