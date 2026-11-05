"""Admin sign-in for the admin pages (evaluation, system setup, books & syllabus).

One password: KAFA_ADMIN_PASSWORD in .env. Signing in returns a token, valid for TOKEN_HOURS, that the
browser sends as "Authorization: Bearer <token>". The token is an expiry time signed with HMAC; the key
mixes a random secret (storage/admin_secret, git-ignored) with the password, so tokens stay valid
across a restart and all become invalid when the password changes.
Prototype security for a school laptop or LAN, like the pupil login.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import time

from fastapi import Header, HTTPException

from .config import get_settings

TOKEN_HOURS = 12


def _key() -> bytes:
    s = get_settings()
    path = s.sqlite_path.parent / "admin_secret"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(secrets.token_bytes(32))
    return path.read_bytes() + hashlib.sha256(s.admin_password.encode()).digest()


def enabled() -> bool:
    return bool(get_settings().admin_password)


def check_password(password: str) -> bool:
    return enabled() and hmac.compare_digest(password.encode(), get_settings().admin_password.encode())


def issue() -> dict:
    exp = int(time.time()) + TOKEN_HOURS * 3600
    sig = hmac.new(_key(), str(exp).encode(), hashlib.sha256).hexdigest()
    return {"token": f"{exp}.{sig}", "expires": exp}


def valid(token: str) -> bool:
    exp, _, sig = (token or "").partition(".")
    if not enabled() or not exp.isdigit() or int(exp) < time.time():
        return False
    return hmac.compare_digest(sig, hmac.new(_key(), exp.encode(), hashlib.sha256).hexdigest())


def require_admin(authorization: str | None = Header(default=None)) -> None:
    """FastAPI dependency for every admin endpoint."""
    token = (authorization or "").removeprefix("Bearer ").strip()
    if not valid(token):
        raise HTTPException(401, "Admin sign-in needed (or the session has expired).")
