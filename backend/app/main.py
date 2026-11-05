"""FastAPI entry point.

Run (from the FypNabil folder):
    .venv\\Scripts\\uvicorn backend.app.main:app --port 8000

SECURITY NOTE: prototype only. A student is identified by name + class and the
client sends student_id. The admin pages need the admin password (admin_auth.py).
Run on localhost or a trusted school LAN only; add real auth before any public deployment.
"""
from __future__ import annotations

import logging
import threading
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from . import __doc__ as pkg_doc
from . import admin_api, live_config
from .admin_auth import require_admin
from . import catalog as cat
from . import chat as chat_module
from .assess import pipeline
from .assess.decision import load_config
from .config import get_settings
from .embeddings import embedder_loaded, get_embedder
from .llm import get_llm, llm_loaded
from .notes import note_body, source_label
from . import remote_llm
from .schemas import AVATARS, AnswerIn, ChatIn, LoginIn, QwenEndpointIn, Student

log = logging.getLogger("kafa")
settings = get_settings()
_warm = {"state": "idle", "error": None}


def _warm_up() -> None:
    """Load both models in the background so the first answer is not slow."""
    _warm["state"] = "loading"
    try:
        get_embedder()
        if remote_llm.endpoint() is None and settings.local_llm:   # Qwen on Colab: nothing to load here
            get_llm()
        _warm["state"] = "ready"
    except Exception as e:  # noqa: BLE001 - report, keep API alive (rule-only scoring still works)
        log.exception("model warm-up failed")
        _warm["state"], _warm["error"] = "error", str(e)


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.preload_models:
        threading.Thread(target=_warm_up, daemon=True).start()
    yield


app = FastAPI(title="Intelligent KAFA UPKK Learning Assistant API", version="0.2.0", description=pkg_doc, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
                   allow_methods=["GET", "POST", "DELETE"], allow_headers=["Content-Type", "Authorization"])
app.include_router(admin_api.public)
app.include_router(admin_api.router)


def _student_or_404(student_id: int) -> dict:
    s = pipeline.get_memory().get_student(student_id)
    if s is None:
        raise HTTPException(404, "Murid tidak dijumpai")
    return s


@app.get("/api/health")
def health() -> dict:
    remote = remote_llm.endpoint()
    return {"status": "ok", "llm_model": settings.llm_model_id, "llm_loaded": llm_loaded() or bool(remote and remote_llm.served()),
            "llm_location": "colab" if remote else ("local" if settings.local_llm else "none"),
            "embed_model": settings.embed_model_id, "embedder_loaded": embedder_loaded(),
            "warm_up": _warm["state"], "scoring_config": load_config().name,
            "live_scorer": live_config.current(), "researcher_mode": settings.researcher_mode}


@app.get("/api/eval/summary", dependencies=[Depends(require_admin)])
def eval_summary_route() -> dict:
    """Results for the evaluation page (admin only)."""
    from .eval_summary import summary

    return summary()


@app.get("/api/settings/qwen", dependencies=[Depends(require_admin)])
def qwen_endpoint_get() -> dict:
    """Where Qwen runs: the saved Google Colab link (key hidden) and whether it answers."""
    ep = remote_llm.endpoint()
    return {"url": ep[0] if ep else "", "has_key": bool(ep and ep[1]), "local_llm": settings.local_llm,
            "status": remote_llm.check() if ep else None}


@app.post("/api/settings/qwen", dependencies=[Depends(require_admin)])
def qwen_endpoint_set(body: QwenEndpointIn) -> dict:
    """Test the Colab link, and save it only if the server answers."""
    status = remote_llm.check(remote_llm.normalize(body.url), body.key)
    if not status["ok"]:
        raise HTTPException(400, f"Colab server did not answer: {status['error']}")
    remote_llm.set_endpoint(body.url, body.key)
    return {"saved": True, "status": status}


@app.delete("/api/settings/qwen", dependencies=[Depends(require_admin)])
def qwen_endpoint_clear() -> dict:
    remote_llm.clear_endpoint()
    return {"saved": False}


@app.get("/api/avatars")
def avatars() -> list[str]:
    return list(AVATARS)


@app.post("/api/auth/login", response_model=Student)
def login(body: LoginIn) -> dict:
    """Prototype login: find-or-create by name + class. NOT secure authentication."""
    s = pipeline.get_memory().get_or_create_student(body.name, body.kelas, body.avatar)
    chat_module.reset_turns(s["id"])   # fresh chat quota every login
    return {k: s[k] for k in ("id", "name", "kelas", "avatar")}


@app.get("/api/subjects")
def subjects(student_id: int | None = None) -> list[dict]:
    mastery = {}
    if student_id is not None:
        _student_or_404(student_id)
        mastery = pipeline.get_memory().all_mastery(student_id)
    return cat.catalog(mastery)


@app.get("/api/topics/{topic_id}/note")
def topic_note(topic_id: str) -> dict:
    t = cat.topic(topic_id)
    body = note_body(topic_id)
    if t is None or body is None:
        raise HTTPException(404, "Topik tidak dijumpai")
    return {"topic": t, "markdown": body, "source": source_label(topic_id)}


@app.get("/api/questions/next")
def question_next(student_id: int, subject: str | None = None, topic_id: str | None = None,
                  level: int | None = Query(default=None, ge=1, le=3)) -> dict:
    _student_or_404(student_id)
    try:
        q = pipeline.next_question(student_id, subject=subject, topic_id=topic_id, level=level)
    except pipeline.AssessmentError as e:
        raise HTTPException(400, str(e)) from e
    return {**pipeline.public_question(q), "topic": cat.topic(q["topic_id"])}


@app.post("/api/answers")
def answer(body: AnswerIn) -> dict:
    _student_or_404(body.student_id)
    try:
        res = pipeline.assess(body.student_id, body.question_id, body.answer)
    except pipeline.AssessmentError as e:
        raise HTTPException(400, str(e)) from e
    return res.to_dict()


@app.get("/api/progress/{student_id}")
def progress(student_id: int) -> dict:
    s = _student_or_404(student_id)
    mem = pipeline.get_memory()
    subs = cat.catalog(mem.all_mastery(student_id))
    return {
        "student": {k: s[k] for k in ("id", "name", "kelas", "avatar")},
        **mem.progress(student_id),
        "subjects": [{"id": x["id"], "name_rumi": x["name_rumi"], "name_jawi": x["name_jawi"],
                      "mastery": x["mastery"], "topic_count": x["topic_count"],
                      "topics": [{k: t[k] for k in ("id", "title_rumi", "title_jawi", "mastery",
                                                   "attempts", "level_unlocked")}
                                 for b in x["babs"] for t in b["topics"] if t["has_questions"]]}
                     for x in subs],
        "recent": mem.recent_attempts(student_id, 30),   # enough for the weekly trend and the history list
    }


@app.post("/api/chat")
def chat(body: ChatIn) -> dict:
    """AI Chat Assistant: pupil asks free-form questions, answered from the KB."""
    _student_or_404(body.student_id)
    try:
        result = chat_module.ask(
            student_id=body.student_id,
            message=body.message,
            subject=body.subject or None,
            history=[{"role": t.role, "content": t.content} for t in body.history],
        )
    except chat_module.ChatLimitError:
        raise HTTPException(429, "Had bual bicara untuk sesi ini sudah habis. Log masuk semula untuk teruskan.")
    return {
        "reply": result.reply,
        "sources": [
            {"topic_rumi": s.topic_rumi, "topic_jawi": s.topic_jawi, "pages": s.pages}
            for s in result.sources
        ],
        "turns_left": result.turns_left,
    }
