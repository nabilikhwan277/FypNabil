"""The marking-agreement metrics used in the thesis tables."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "eval"))

import scoring_lib  # noqa: E402


def item(max_marks, gold, pred):
    return {"max_marks": float(max_marks), "gold": float(gold), "pred": float(pred), "pred_mets": ["ya"],
            "criteria": [{"label": "ya", "marks": float(max_marks), "a_layer": None}]}


def test_within_1_ignores_one_mark_answers_which_cannot_miss_by_more_than_one():
    scored = [item(1, 0, 1), item(1, 1, 1),        # 1-mark answers: always "within 1 mark"
              item(3, 3, 0), item(3, 2, 1)]        # 3-mark answers: 3 marks out, then 1 mark out
    m = scoring_lib.metrics(scored)
    assert m["within_1_all"] == 0.75               # the old rate counted the two 1-mark answers
    assert m["within_1"] == 0.5 and m["n_within_1"] == 2


def test_within_1_is_none_when_every_answer_is_worth_one_mark():
    m = scoring_lib.metrics([item(1, 1, 1), item(1, 0, 1)])
    assert m["within_1"] is None and m["n_within_1"] == 0 and m["within_1_all"] == 1.0
