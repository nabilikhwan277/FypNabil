import json

from backend.app.assess.decision import PHASE4, Rule, ScoringConfig, credit, decide, load_config
from backend.app.assess.judge import expected_credit, format_examples, judge_prob
from backend.app.assess.matching import content_overlap, keyword_overlap
from backend.app.assess.rubric import score_answer

from .fakes import fake_embed

BASE = {"a_layer": None, "a_met": None, "crit_sim": 0.5, "ans_sim": 0.5, "kw_overlap": 0.0,
        "crit_overlap": 0.0, "num_conflict": False, "n_criteria": 2}


def test_layer_a_always_wins():
    f = {**BASE, "a_layer": "A-keyword", "a_met": "ya", "crit_sim": 0.0}
    assert decide(f, Rule("sim", hi=0.99)) == "ya"


def test_threshold_rule_with_separa_band():
    r = Rule("overlap", hi=0.8, lo=0.4)
    assert decide({**BASE, "kw_overlap": 0.9}, r) == "ya"
    assert decide({**BASE, "kw_overlap": 0.5}, r) == "separa"
    assert decide({**BASE, "kw_overlap": 0.1}, r) == "tidak"
    assert decide({**BASE, "kw_overlap": 0.9, "num_conflict": True}, r) == "tidak"


def test_prob_and_hybrid_credit():
    f = {**BASE, "p_fs": {"ya": 0.6, "separa": 0.2, "tidak": 0.2}, "kw_overlap": 1.0, "crit_sim": 0.8}
    assert abs(credit(f, "prob_fs") - 0.7) < 1e-9
    assert abs(credit(f, "hybrid_fs", w=0.5) - (0.5 * 0.7 + 0.5 * 1.0)) < 1e-9
    assert credit(BASE, "prob_zs") is None      # no LLM output -> no credit
    assert decide(BASE, Rule("prob_zs", hi=0.1)) == "tidak"


def test_phase4_rules_reproduced():
    assert decide({**BASE, "n_criteria": 1, "ans_sim": 0.9}, PHASE4.l1) == "ya"
    assert decide({**BASE, "n_criteria": 1, "ans_sim": 0.8}, PHASE4.l1) == "tidak"
    assert decide({**BASE, "llm_gen": "ya", "crit_sim": 0.7}, PHASE4.l23) == "ya"
    assert decide({**BASE, "llm_gen": "ya", "crit_sim": 0.5}, PHASE4.l23) == "tidak"   # guard


def test_config_roundtrip(tmp_path):
    cfg = ScoringConfig("x", Rule("mix", hi=0.5, w=0.3), Rule("prob_fs", hi=0.6, lo=0.4))
    p = tmp_path / "c.json"
    p.write_text(json.dumps(cfg.to_dict()), encoding="utf-8")
    assert load_config(p) == cfg
    assert load_config(tmp_path / "missing.json") == PHASE4


def test_overlap_tolerates_affixes():
    assert content_overlap("Diampunkan dosa", "dosa-dosanya diampun Allah") == 1.0
    assert content_overlap("Diampunkan dosa", "rezeki murah") == 0.0
    assert keyword_overlap(["ampun dosa", "rezeki"], "dia dapat rezeki") == 1.0


def test_judge_prob_prompt_and_credit():
    seen = {}

    def fake_probs(messages, labels):
        seen["prompt"] = messages[-1]["content"]
        assert set(labels) == {"ya", "separa", "tidak"}
        return {"ya": 0.5, "separa": 0.4, "tidak": 0.1}

    ex = [{"criterion": "C1", "answer": "A1", "met": "ya"}]
    p = judge_prob(fake_probs, criterion="C", question="Q", reference="R", answer="A", context="NOTA", examples=ex)
    assert "NOTA" in seen["prompt"] and "Contoh penilaian" in seen["prompt"] and "-> YA" in seen["prompt"]
    assert abs(expected_credit(p) - 0.7) < 1e-9
    assert format_examples(None) == ""


def test_score_answer_uses_probability_judge_on_l2():
    q = {"id": "q", "subject": "fiqh", "topic_id": "t", "level": 2, "type": "structured",
         "question_rumi": "Q", "reference_answer_rumi": "R", "max_marks": 2,
         "rubric": [{"criterion": "Diampunkan dosa", "marks": 2, "keywords": ["diampunkan dosa"]}]}
    cfg = ScoringConfig("t", Rule("mix", hi=0.6), Rule("prob_zs", hi=0.6, lo=0.4))
    hi = score_answer(q, "Allah ampun salah kita", embed=fake_embed, generate=None, config=cfg,
                      label_probs=lambda m, lab: {"ya": 0.9, "separa": 0.05, "tidak": 0.05})
    assert hi.score == 2 and hi.criteria[0].layer == "B-prob" and hi.llm_calls == 1
    mid = score_answer(q, "Allah ampun salah kita", embed=fake_embed, generate=None, config=cfg,
                       label_probs=lambda m, lab: {"ya": 0.3, "separa": 0.4, "tidak": 0.3})
    assert mid.score == 1 and mid.criteria[0].met == "separa"
    # no LLM available -> safe non-LLM fallback, never an exception
    none = score_answer(q, "Allah ampun salah kita", embed=fake_embed, generate=None, config=cfg)
    assert none.llm_calls == 0 and none.criteria[0].layer in ("A-none", "A-similarity")
