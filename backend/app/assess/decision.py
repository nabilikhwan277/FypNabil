"""Decision rules for rubric criteria that Layer A could not settle.

Shared by the live scorer (rubric.py) and the offline tuner/evaluator (eval/),
so the numbers reported in the thesis come from exactly the production logic.

A criterion's features:
  a_layer, a_met   deterministic Layer A result (None if unresolved)
  crit_sim         cosine(answer, criterion + keywords)
  ans_sim          cosine(answer, reference answer)
  kw_overlap       content-word overlap with best keyword (0..1)
  crit_overlap     content-word overlap with the criterion text (0..1)
  num_conflict     answer contradicts reference numbers
  n_criteria       number of criteria in the question
  llm_gen          generative judge verdict, if computed
  p_zs / p_fs      probability judge (zero-/few-shot) {'ya','separa','tidak'}
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent / "scoring_config.json"
LLM_METHODS = {"gen", "prob_zs", "prob_fs", "hybrid_zs", "hybrid_fs"}


def award(marks: float, met: str) -> float:
    """ya = full, separa = half rounded to the nearest 0.5 (min 0.5), tidak = 0."""
    if met == "ya":
        return marks
    if met == "separa":
        return max(0.5, round(marks / 2 * 2) / 2)
    return 0.0


def norm_sim(s: float, lo: float = 0.35, hi: float = 0.80) -> float:
    """Map a bge-m3 cosine onto 0..1 (0.35 ~ unrelated, 0.80 ~ paraphrase)."""
    return max(0.0, min(1.0, (s - lo) / (hi - lo)))


@dataclass(frozen=True)
class Rule:
    method: str            # phase4_l1 | gen | sim | ans_sim | overlap | mix | prob_zs | prob_fs | hybrid_zs | hybrid_fs
    hi: float = 0.6        # credit >= hi -> ya
    lo: float = 1.1        # credit >= lo -> separa (lo > 1 disables separa)
    w: float = 0.5         # overlap weight in mix / hybrid
    guard: float = 0.60    # gen only: LLM yes needs crit_sim >= guard

    @property
    def needs_llm(self) -> bool:
        return self.method in LLM_METHODS

    def label(self) -> str:
        if self.method == "gen":
            return f"gen(guard={self.guard:.2f})"
        if self.method == "phase4_l1":
            return "phase4_l1(sim>=0.85)"
        s = f"{self.method}(hi={self.hi:.2f}"
        if self.lo <= 1:
            s += f",lo={self.lo:.2f}"
        if self.method in ("mix", "sims", "hybrid_zs", "hybrid_fs"):
            s += f",w={self.w:.1f}"
        return s + ")"


def credit(f: dict, method: str, w: float = 0.5) -> float | None:
    """0..1 evidence that the criterion is met."""
    ovl = max(f["kw_overlap"], f["crit_overlap"])
    mix = w * ovl + (1 - w) * norm_sim(f["crit_sim"])
    if method == "sim":
        return norm_sim(f["crit_sim"])
    if method == "ans_sim":
        return norm_sim(f["ans_sim"])
    if method == "overlap":
        return ovl
    if method == "mix":
        return mix
    if method == "sims":      # criterion similarity and whole-answer similarity, weighted by w
        return w * norm_sim(f["crit_sim"]) + (1 - w) * norm_sim(f["ans_sim"])
    p = f.get("p_fs" if method.endswith("_fs") else "p_zs")
    if p is None:
        return None
    pc = p["ya"] + 0.5 * p["separa"]
    if method.startswith("prob_"):
        return pc
    if method.startswith("hybrid_"):
        return 0.5 * pc + 0.5 * mix
    raise ValueError(f"unknown method {method}")


def decide(f: dict, rule: Rule) -> str:
    """Final ya / separa / tidak for one criterion."""
    if f.get("a_layer") is not None:
        return f["a_met"]
    if rule.method == "phase4_l1":   # the Phase 4 behaviour, kept as a baseline
        s = f["ans_sim"] if f.get("n_criteria", 1) == 1 else f["crit_sim"]
        return "ya" if s >= 0.85 and not f["num_conflict"] else "tidak"
    if rule.method == "gen":
        v = f.get("llm_gen")
        if v is None:
            return "tidak"
        if v in ("ya", "separa") and (f["crit_sim"] < rule.guard or f["num_conflict"]):
            return "tidak"
        return v
    c = credit(f, rule.method, rule.w)
    if c is None or f["num_conflict"]:
        return "tidak"
    if c >= rule.hi:
        return "ya"
    if c >= rule.lo:
        return "separa"
    return "tidak"


@dataclass(frozen=True)
class ScoringConfig:
    name: str
    l1: Rule    # Tahap 1 (never uses the LLM)
    l23: Rule   # Tahap 2/3

    def rule_for(self, level: int) -> Rule:
        return self.l1 if level == 1 else self.l23

    def to_dict(self) -> dict:
        return {"name": self.name, "l1": asdict(self.l1), "l23": asdict(self.l23)}

    @classmethod
    def from_dict(cls, d: dict) -> "ScoringConfig":
        return cls(d["name"], Rule(**d["l1"]), Rule(**d["l23"]))


PHASE4 = ScoringConfig("phase4_baseline", Rule("phase4_l1"), Rule("gen", guard=0.60))


def load_config(path: Path = CONFIG_PATH) -> ScoringConfig:
    """Tuned configuration if present, else the Phase 4 behaviour."""
    if path.exists():
        return ScoringConfig.from_dict(json.loads(path.read_text(encoding="utf-8")))
    return PHASE4
