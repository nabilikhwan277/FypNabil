"""Tanya Bulan's gate (RAG settings study): a weak match goes to the model with the decline rule; when the model
declines, or there is nothing to show (no model reply and no textbook key fact), the reply says the topic is not in
the notes and shows no sources."""
import pytest

from backend.app import chat
from backend.app.remote_llm import RemoteUnavailable

from .fakes import FakeHit

NOTICE = "Data ini tiada dalam pangkalan data saya."
NOTE = "Solat Dhuha ialah solat sunat yang dikerjakan pada waktu dhuha. Bilangan rakaatnya sekurang-kurangnya dua rakaat."


class Gen:
    def __init__(self, text: str) -> None:
        self.text = text


@pytest.fixture
def ask(monkeypatch):
    def run(score: float, model_reply: str | None, note: str = NOTE):
        hit = FakeHit("c1", note, "fiqh_b1_solat_dhuha", score=score)
        hit.metadata.update(topic_rumi="Solat Dhuha", book_pages=[12])
        monkeypatch.setattr(chat, "dense_search", lambda q, k=1, subject=None: [hit])
        monkeypatch.setattr(chat, "search_notes", lambda q, subject=None, k=4: [hit])

        def generate(messages, **_):
            if model_reply is None:
                raise RemoteUnavailable("no model")
            if isinstance(model_reply, Exception):
                raise model_reply
            return Gen(model_reply)

        monkeypatch.setattr(chat, "generate_text", generate)
        chat.reset_turns(1)
        return chat.ask(student_id=1, message="Apakah solat dhuha?")
    return run


def test_weak_match_answered_by_the_model_keeps_its_sources(ask):
    r = ask(0.45, "Solat Dhuha ialah solat sunat pada waktu dhuha.")
    assert r.sources and NOTICE not in r.reply


def test_weak_match_declined_by_the_model_has_no_sources(ask):
    r = ask(0.45, NOTICE)
    assert r.sources == [] and r.reply.startswith(NOTICE)


def test_weak_match_without_a_model_is_outside_the_notes(ask):
    r = ask(0.45, None)
    assert r.sources == [] and r.reply == NOTICE


def test_strong_match_without_a_model_uses_the_textbook(ask):
    r = ask(0.7, None)
    assert r.sources and r.reply.startswith("Berdasarkan buku teks Solat Dhuha")


def test_strong_match_without_a_model_or_key_fact_is_outside_the_notes(ask):
    r = ask(0.7, None, note="Tanda waqaf:\n| صلى | قلى |")   # no sentence the textbook fallback can show
    assert r.sources == [] and r.reply == NOTICE


def test_below_the_gate_is_outside_the_notes(ask):
    r = ask(0.3, "apa-apa")
    assert r.sources == [] and r.reply.startswith(NOTICE)


@pytest.mark.parametrize("failure", [RuntimeError("CUDA out of memory"), OSError("model files not found"),
                                     KeyError("choices")])
def test_any_model_failure_gives_the_pupil_a_reply_not_a_server_error(ask, failure):
    """A model that cannot load, or a Colab reply with no 'choices', behaves like no model."""
    weak = ask(0.45, failure)
    assert weak.sources == [] and weak.reply == NOTICE
    strong = ask(0.7, failure)
    assert strong.sources and strong.reply.startswith("Berdasarkan buku teks Solat Dhuha")


def test_gate_eval_tells_a_pointer_to_the_teacher_from_a_real_answer():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "eval"))
    import chat_gate_eval as ev

    pointer = f"{NOTICE} Sila tanya guru anda."
    answer = f"{NOTICE} " + "Sungai terpanjang di Malaysia ialah Sungai Rajang. " * 5
    assert ev.after_notice(pointer) == "Sila tanya guru anda." and len(ev.after_notice(pointer)) <= ev.LONG_EXTRA
    assert len(ev.after_notice(answer)) > ev.LONG_EXTRA
    assert ev.after_notice("Solat Dhuha ialah solat sunat.") == ""   # no notice: nothing to measure
