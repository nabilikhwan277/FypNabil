"""API request/response models."""
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

AVATARS = ("🐱", "🐰", "🦊", "🐼", "🐯", "🐨", "🦁", "🐧", "🦉", "🐢")


class LoginIn(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    kelas: str = Field(default="", max_length=30)
    avatar: str = Field(default="🐱", max_length=8)

    @field_validator("name", "kelas")
    @classmethod
    def strip(cls, v: str) -> str:
        return " ".join(v.split())

    @field_validator("name")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v:
            raise ValueError("Nama diperlukan")
        return v

    @field_validator("avatar")
    @classmethod
    def known_avatar(cls, v: str) -> str:
        return v if v in AVATARS else AVATARS[0]


class Student(BaseModel):
    id: int
    name: str
    kelas: str
    avatar: str


class AnswerIn(BaseModel):
    student_id: int
    question_id: str = Field(min_length=1, max_length=80)
    answer: str = Field(min_length=1, max_length=2000)


class ChatTurn(BaseModel):
    role: str = Field(pattern=r"^(user|assistant)$")
    content: str = Field(min_length=1, max_length=2000)


class ChatIn(BaseModel):
    student_id: int
    message: str = Field(min_length=1, max_length=500)
    subject: str | None = Field(default=None, max_length=30)
    history: list[ChatTurn] = Field(default_factory=list, max_length=6)

    @field_validator("history", mode="before")
    @classmethod
    def limit_history(cls, v: list) -> list:
        return v[-6:] if isinstance(v, list) else v


class QwenEndpointIn(BaseModel):
    """Link + key of the Qwen server on Google Colab (shown by the notebook)."""
    url: str = Field(min_length=8, max_length=300, pattern=r"^https?://\S+$")
    key: str = Field(default="", max_length=200)
