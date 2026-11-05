"""Background jobs started from the admin pages: an evaluation run, processing an uploaded book.

One job of each kind runs at a time (they share the API budget and the GPU). Status is kept in memory
and polled by the page; a restart forgets running jobs (a book's own status is saved on disk).
"""
from __future__ import annotations

import itertools
import logging
import threading
import time
import traceback
from dataclasses import asdict, dataclass, field
from typing import Callable

log = logging.getLogger("kafa.jobs")
_ids = itertools.count(1)
_lock = threading.Lock()
_jobs: dict[int, "Job"] = {}


class JobBusy(RuntimeError):
    pass


@dataclass
class Job:
    id: int
    kind: str                  # evaluation | book
    title: str
    status: str = "running"    # running | done | failed
    done: int = 0
    total: int = 0
    message: str = ""
    result: dict = field(default_factory=dict)
    error: str = ""
    started: float = field(default_factory=time.time)
    finished: float | None = None

    def progress(self, done: int, total: int, message: str = "") -> None:
        self.done, self.total = done, total
        if message:
            self.message = message

    def to_dict(self) -> dict:
        return asdict(self)


def start(kind: str, title: str, fn: Callable[[Job], dict | None]) -> Job:
    with _lock:
        if any(j.kind == kind and j.status == "running" for j in _jobs.values()):
            raise JobBusy(f"Another {kind} job is still running")
        job = Job(next(_ids), kind, title)
        _jobs[job.id] = job

    def runner() -> None:
        try:
            job.result = fn(job) or {}
            job.status = "done"
        except Exception as e:  # noqa: BLE001 - the page shows the error
            log.exception("job %s failed", job.title)
            job.status, job.error = "failed", f"{type(e).__name__}: {e}"[:500]
            job.result = {"trace": traceback.format_exc()[-1500:]}
        finally:
            job.finished = time.time()

    threading.Thread(target=runner, daemon=True, name=f"job-{job.id}").start()
    return job


def get(job_id: int) -> Job | None:
    return _jobs.get(job_id)


def latest(kind: str) -> Job | None:
    found = [j for j in _jobs.values() if j.kind == kind]
    return max(found, key=lambda j: j.id) if found else None
