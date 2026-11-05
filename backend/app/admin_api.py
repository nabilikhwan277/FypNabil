"""Admin endpoints: sign-in, the live marking system, evaluations and Books & syllabus.

Everything under /api/admin (except /login) needs the admin token (admin_auth.require_admin).
"""
from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from . import admin_auth, admin_eval, jobs, library, live_config, runtime

public = APIRouter(prefix="/api/admin")
router = APIRouter(prefix="/api/admin", dependencies=[Depends(admin_auth.require_admin)])


class LoginIn(BaseModel):
    password: str = Field(min_length=1, max_length=200)


class ConfigIn(BaseModel):
    config: str = Field(min_length=2, max_length=60)


class EvaluateIn(ConfigIn):
    data: str = Field(pattern=r"^(teacher|silver)$")
    labels: str = Field(default="final", pattern=r"^[a-z0-9_]{1,30}$")


class DraftIn(BaseModel):
    path: str = Field(min_length=5, max_length=200)
    content: str = Field(max_length=2_000_000)


def _bad(e: Exception) -> HTTPException:
    return HTTPException(400, str(e))


# ------------------------------------------------------------------ sign-in
@public.post("/login")
def login(body: LoginIn) -> dict:
    if not admin_auth.enabled():
        raise HTTPException(503, "Admin sign-in is off: set KAFA_ADMIN_PASSWORD in .env and restart the server.")
    if not admin_auth.check_password(body.password):
        time.sleep(1)          # slows down guessing
        raise HTTPException(401, "Wrong password")
    return admin_auth.issue()


@router.get("/me")
def me() -> dict:
    return {"admin": True}


# ------------------------------------------------------------------ live marking system + evaluation
@router.get("/config")
def config() -> dict:
    rt = runtime.load()
    return {"live": live_config.describe(live_config.current()), "set_at": rt.get("scorer_set_at"),
            "options": live_config.options(), "datasets": admin_eval.datasets(),
            "syllabus_changed_at": rt.get("syllabus_changed_at")}


@router.post("/config")
def set_config(body: ConfigIn) -> dict:
    try:
        return live_config.set_current(body.config)
    except ValueError as e:
        raise _bad(e) from e


@router.get("/evaluate/estimate")
def evaluate_estimate(config: str, data: str, labels: str = "final") -> dict:
    try:
        return admin_eval.estimate(config, data, labels)
    except ValueError as e:
        raise _bad(e) from e


@router.post("/evaluate")
def evaluate(body: EvaluateIn) -> dict:
    try:
        return admin_eval.start(body.config, body.data, body.labels).to_dict()
    except (ValueError, jobs.JobBusy) as e:
        raise _bad(e) from e


@router.get("/jobs/latest")
def job_latest(kind: str) -> dict | None:
    job = jobs.latest(kind)
    return job.to_dict() if job else None


@router.get("/jobs/{job_id}")
def job(job_id: int) -> dict:
    j = jobs.get(job_id)
    if j is None:
        raise HTTPException(404, "No such job (the server may have restarted)")
    return j.to_dict()


# ------------------------------------------------------------------ books & syllabus
def _lib(fn, *args, **kw):
    try:
        return fn(*args, **kw)
    except library.LibraryError as e:
        raise _bad(e) from e


@router.get("/books")
def books() -> list[dict]:
    return library.list_books()


@router.post("/books")
async def add_book(request: Request, title: str, subject: str, kind: str, filename: str = "book.pdf", year: int = 5) -> dict:
    """The PDF is the request body (Content-Type: application/pdf)."""
    size = int(request.headers.get("content-length") or 0)
    if size > library.MAX_BYTES:
        raise HTTPException(413, "The PDF is too large")
    data = await request.body()
    return _lib(library.add_book, data, filename=filename, title=title, subject=subject, kind=kind, year=year)


@router.get("/books/{book_id}")
def book(book_id: str) -> dict:
    return _lib(library.get_book, book_id)


@router.post("/books/{book_id}/process")
def process(book_id: str) -> dict:
    rec = _lib(library.get_book, book_id)
    try:
        return jobs.start("book", f"Read {rec['title']}", lambda job: library.process(book_id, job)).to_dict()
    except jobs.JobBusy as e:
        raise _bad(e) from e


@router.get("/books/{book_id}/drafts")
def drafts(book_id: str) -> list[dict]:
    return _lib(library.drafts, book_id)


@router.post("/books/{book_id}/drafts")
def save_draft(book_id: str, body: DraftIn) -> dict:
    return _lib(library.save_draft, book_id, body.path, body.content)


@router.delete("/books/{book_id}/drafts")
def delete_draft(book_id: str, path: str) -> dict:
    _lib(library.delete_draft, book_id, path)
    return {"deleted": path}


@router.post("/books/{book_id}/publish")
def publish(book_id: str) -> dict:
    return _lib(library.publish, book_id)


@router.post("/books/{book_id}/remove")
def remove(book_id: str) -> dict:
    return _lib(library.remove, book_id)


@router.post("/books/{book_id}/restore")
def restore(book_id: str) -> dict:
    return _lib(library.restore, book_id)


@router.delete("/books/{book_id}")
def delete_book(book_id: str) -> dict:
    _lib(library.delete, book_id)
    return {"deleted": book_id}


@router.get("/books/{book_id}/pages/{page}")
def page(book_id: str, page: int) -> FileResponse:
    return FileResponse(_lib(library.page_image, book_id, page), media_type="image/jpeg")
