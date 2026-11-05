"""Objective (A-D) questions: exact marking, and the answer never reaches the pupil."""
from backend.app.assess.pipeline import mcq_choice, mcq_marking, public_question

Q = {
    "id": "t_q1", "topic_id": "tajwid_b3_mad_badal", "subject": "tajwid", "level": 1, "type": "short", "max_marks": 1,
    "question_rumi": "Berapakah kadar panjang bacaan Mad Badal?", "question_jawi": "...",
    "reference_answer_rumi": "Dua harakat", "rubric": [{"criterion": "Dua harakat", "marks": 1, "keywords": ["dua harakat"]}],
    "mcq": {"stem_rumi": "Berapakah kadar panjang bacaan Mad Badal?", "stem_jawi": "...", "answer": 2, "spelling": False,
            "explanation_rumi": "Mad Badal dibaca dua harakat.",
            "options": [{"rumi": "Enam harakat", "jawi": "انم حركة"}, {"rumi": "Empat harakat", "jawi": "امڤت حركة"},
                        {"rumi": "Dua harakat", "jawi": "دوا حركة"}, {"rumi": "Lima harakat", "jawi": "ليم حركة"}]},
}


def test_choice_only_for_letters_on_objective_questions():
    assert mcq_choice(Q, "c") == 2 and mcq_choice(Q, " B. ") == 1
    assert mcq_choice(Q, "dua harakat") is None                 # an open answer is still marked the open way
    assert mcq_choice({k: v for k, v in Q.items() if k != "mcq"}, "A") is None


def test_marking_is_exact():
    q, shown, score = mcq_marking(Q, 2)
    r, extra = score()
    assert r.score == 1.0 and r.max_marks == 1.0 and r.criteria[0].met == "ya" and extra["scorer"] == "mcq"
    assert shown == "C. Dua harakat" and q["reference_answer_rumi"].startswith("C. Dua harakat")
    _, shown, score = mcq_marking(Q, 0)
    r, _ = score()
    assert r.score == 0.0 and r.criteria[0].met == "tidak" and shown == "A. Enam harakat"


def test_public_question_hides_the_answer():
    p = public_question(Q)
    assert len(p["choices"]["options"]) == 4 and p["max_marks"] == 1
    assert "answer" not in p["choices"] and "explanation_rumi" not in p["choices"]
    assert "mcq" not in p and "reference_answer_rumi" not in p and "rubric" not in p
