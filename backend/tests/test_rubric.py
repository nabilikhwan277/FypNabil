from backend.app.assess.judge import judge_criterion, parse_verdict
from backend.app.assess.matching import number_conflict, phrase_in, true_false_answer
from backend.app.assess.decision import PHASE4
from backend.app.assess.rubric import Thresholds, award, score_answer

from .fakes import ScriptedLLM, fake_embed

Q_L1 = {
    "id": "t_q1", "subject": "tajwid", "topic_id": "t", "level": 1, "type": "short",
    "question_rumi": "Berapakah kadar harakat Mad Badal?",
    "reference_answer_rumi": "Dua harakat", "reference_answer_jawi": "دوا حركة",
    "rubric": [{"criterion": "Menyatakan dua harakat", "marks": 1, "keywords": ["dua harakat", "2 harakat"]}],
    "max_marks": 1,
}
Q_SPELL = {
    "id": "j_q1", "subject": "jawi", "topic_id": "j", "level": 1, "type": "short",
    "question_rumi": "Tulis perkataan 'teks' dalam tulisan Jawi.",
    "reference_answer_rumi": "teks", "reference_answer_jawi": "تيك س",
    "rubric": [{"criterion": "Ejaan teks", "marks": 1, "keywords": ["تيك س", "تيكس"]}],
    "max_marks": 1,
}
Q_TF = {
    "id": "f_q1", "subject": "fiqh", "topic_id": "f", "level": 1, "type": "short",
    "question_rumi": "Betul atau Salah: Solat witir boleh enam rakaat.",
    "reference_answer_rumi": "Salah", "reference_answer_jawi": "ساله",
    "rubric": [{"criterion": "Menjawab Salah", "marks": 1, "keywords": ["salah", "ساله"]}],
    "max_marks": 1,
}
Q_L2 = {
    "id": "f_q2", "subject": "fiqh", "topic_id": "f", "level": 2, "type": "structured",
    "question_rumi": "Nyatakan dua fadhilat solat dhuha.",
    "reference_answer_rumi": "Dimurahkan rezeki; diampunkan dosa",
    "rubric": [
        {"criterion": "Dimurahkan rezeki", "marks": 1, "keywords": ["rezeki"]},
        {"criterion": "Diampunkan dosa", "marks": 2, "keywords": ["ampun dosa", "diampunkan dosa"]},
    ],
    "max_marks": 3,
}


# ---------- matching ----------
def test_phrase_in_numbers_spacing_and_script():
    assert phrase_in("dua harakat", "Kadarnya 2 harakat sahaja")
    assert phrase_in("تيك س", "تيكس")            # textbook spaced form == joined form
    assert phrase_in("تيكس", "jawapan: تيك س")
    assert not phrase_in("dua harakat", "dua belas harakat")
    assert phrase_in("سبلوم", "سَبْلُوم")          # harakat ignored


def test_number_conflict_and_true_false():
    assert number_conflict("dua harakat", "enam harakat")
    assert not number_conflict("dua harakat", "2 harakat")
    assert not number_conflict("dua harakat", "harakat")   # no number stated: not a conflict
    assert true_false_answer("Salah") == "salah"
    assert true_false_answer("tidak betul") == "salah"
    assert true_false_answer("Betul!") == "betul"
    assert true_false_answer("betul atau salah") is None


def test_award_rounding():
    assert award(1, "ya") == 1 and award(1, "tidak") == 0
    assert award(1, "separa") == 0.5 and award(2, "separa") == 1 and award(3, "separa") == 1.5


# ---------- layer A ----------
def test_l1_keyword_and_number_word():
    r = score_answer(Q_L1, "2 harakat", embed=fake_embed, generate=None)
    assert r.score == 1 and r.criteria[0].layer == "A-keyword"


def test_l1_wrong_number_scores_zero_even_if_similar():
    r = score_answer(Q_L1, "enam harakat", embed=fake_embed, generate=None)
    assert r.score == 0


def test_jawi_spelling_is_strict():
    assert score_answer(Q_SPELL, "تيكس", embed=fake_embed, generate=None).score == 1
    wrong = score_answer(Q_SPELL, "تيكص", embed=fake_embed, generate=None)
    assert wrong.score == 0 and wrong.criteria[0].layer == "A-spelling"


def test_true_false_requires_the_right_choice():
    assert score_answer(Q_TF, "salah", embed=fake_embed, generate=None).score == 1
    assert score_answer(Q_TF, "betul", embed=fake_embed, generate=None).score == 0
    assert score_answer(Q_TF, "betul atau salah", embed=fake_embed, generate=None).score == 0


def test_l1_never_calls_llm():
    llm = ScriptedLLM('{"met": "ya"}')
    score_answer(Q_L1, "saya tidak tahu", embed=fake_embed, generate=llm, config=PHASE4)
    assert llm.prompts == []


# ---------- layer B ----------
def test_l2_keyword_criteria_skip_llm_and_missing_ones_go_to_llm():
    llm = ScriptedLLM('{"met": "separa", "reason": "hampir"}')
    # bag-of-words fake embedder cannot see "diampun" ~ "diampunkan"; relax the guard here
    r = score_answer(Q_L2, "Dimurahkan rezeki dan dosa diampun oleh Allah", embed=fake_embed, generate=llm, config=PHASE4,
                     thresholds=Thresholds(guard_similarity=0.2))
    assert [c.layer for c in r.criteria] == ["A-keyword", "B-llm"]
    assert len(llm.prompts) == 1 and "Diampunkan dosa" in llm.prompts[0]
    assert r.score == 1 + 1  # 1 + half of 2
    assert r.max_marks == 3 and r.percent == 66.7


def test_llm_yes_is_blocked_when_answer_is_unrelated():
    llm = ScriptedLLM('{"met": "ya", "reason": "betul"}', '{"met": "ya", "reason": "betul"}')
    r = score_answer(Q_L2, "Saya suka bermain bola", embed=fake_embed, generate=llm, config=PHASE4)
    assert r.score == 0
    assert all(c.layer == "B-guard" for c in r.criteria)


def test_unparseable_llm_output_retries_then_falls_back():
    llm = ScriptedLLM("hmm entahlah", "mungkin", default="mungkin")
    r = score_answer({**Q_L2, "rubric": Q_L2["rubric"][1:], "max_marks": 2}, "dosa", embed=fake_embed, generate=llm, config=PHASE4)
    assert r.criteria[0].layer == "B-fallback" and r.score == 0
    assert r.llm_calls == 2 and len(llm.prompts) == 2


def test_parse_verdict_variants():
    assert parse_verdict('{"met": "ya", "reason": "ok"}') == ("ya", "ok")
    assert parse_verdict('Jawapan: {"met":"SEPARA"}')[0] == "separa"
    assert parse_verdict('"met": "tidak", reason ...')[0] == "tidak"
    assert parse_verdict("Ya, jawapan murid memenuhi kriteria.")[0] == "ya"
    assert parse_verdict("Kadar dua hari...")[0] is None


def test_judge_prompt_contains_grounding():
    llm = ScriptedLLM('{"met":"ya"}')
    j = judge_criterion(llm, criterion="C", question="Q", reference="R", answer="A", context="NOTA BUKU")
    assert j.met == "ya" and "NOTA BUKU" in llm.prompts[0] and "Jawapan rujukan: R" in llm.prompts[0]
