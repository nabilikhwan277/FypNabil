"""Phase 4 (eval/phase4.py): which replies become training targets, and which answers a hybrid router sends on."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "eval"))

import phase4 as P  # noqa: E402

Q = {"rubric": [{"criterion": "a", "marks": 1}, {"criterion": "b", "marks": 1}], "level": 1}


def reply(*verdicts, feedback="Bagus."):
    return {"criteria": [{"no": n, "verdict": v, "reason": f"r{n}"} for n, v in enumerate(verdicts, 1)], "feedback": feedback}


def test_target_only_when_every_verdict_matches_the_silver_label():
    assert P.target(Q, reply("ya", "separa"), {}, ["ya", "separa"]) == reply("ya", "separa") | {}
    assert P.target(Q, reply("ya", "tidak"), {}, ["ya", "separa"]) is None
    assert P.target(Q, reply("ya"), {}, ["ya", "separa"]) is None                 # a criterion is missing
    assert P.target(Q, reply("ya", "ya", feedback=" "), {}, ["ya", "ya"]) is None  # no feedback
    assert P.target(Q, None, {}, ["ya", "ya"]) is None


def test_target_never_contradicts_an_exact_rule():
    assert P.target(Q, reply("tidak", "ya"), {1: ("tidak", "ejaan")}, ["tidak", "ya"]) is not None
    assert P.target(Q, reply("ya", "ya"), {1: ("tidak", "ejaan")}, ["ya", "ya"]) is None


def test_routers():
    ok = {"ok": True, "score": 1.0, "criteria": [{"met": "ya", "layer": "llm"}, {"met": "separa", "layer": "rule"}]}
    unsure = ok | {"criteria": [{"met": "separa", "layer": "llm"}]}
    rule = {"score": 1.0}
    assert P.escalate("level", ok, Q | {"level": 2}, rule) and not P.escalate("level", ok, Q, rule)
    assert not P.escalate("separa", ok, Q, rule)           # a 'separa' fixed by a rule is not the model's doubt
    assert P.escalate("separa", unsure, Q, rule)
    assert P.escalate("separa", ok | {"ok": False}, Q, rule)
    assert P.escalate("rules", ok, Q, {"score": 0.5}) and not P.escalate("rules", ok, Q, rule)
