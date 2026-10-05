"""Score SUS questionnaires (docs/SUS_soal_selidik.md).

CSV columns: respondent, role, q1..q10 (1-5), a, b (optional 1-5), comment
Usage: .venv\\Scripts\\python scripts\\sus_score.py docs\\sus_responses.csv
Writes eval/results/sus.md
"""
import csv
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def sus(row: dict) -> float:
    q = [int(row[f"q{i}"]) for i in range(1, 11)]
    if any(not 1 <= v <= 5 for v in q):
        raise ValueError(f"answers must be 1-5: {row.get('respondent')}")
    return 2.5 * (sum(q[i] - 1 for i in range(0, 10, 2)) + sum(5 - q[i] for i in range(1, 10, 2)))


def grade(s: float) -> str:
    return "Baik (≥80)" if s >= 80 else "Di atas purata (≥68)" if s >= 68 else "Di bawah purata (<68)"


def main(path: Path) -> None:
    with path.open(encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    scores = [(r.get("role", ""), sus(r), r) for r in rows]
    lines = ["# SUS results", "", f"Respondents: {len(scores)}", "", "| Group | n | Mean SUS | SD | Min | Max | Grade |",
             "|---|---|---|---|---|---|---|"]
    groups = {"Semua": scores, **{g: [s for s in scores if s[0] == g] for g in sorted({s[0] for s in scores})}}
    for g, ss in groups.items():
        v = [s for _, s, _ in ss]
        if v:
            sd = statistics.stdev(v) if len(v) > 1 else 0.0
            lines.append(f"| {g} | {len(v)} | {statistics.mean(v):.1f} | {sd:.1f} | {min(v):.1f} | {max(v):.1f} | "
                         f"{grade(statistics.mean(v))} |")
    for extra, label in (("a", "Maklum balas membantu"), ("b", "Papan kekunci Jawi mudah")):
        v = [int(r[extra]) for _, _, r in scores if r.get(extra, "").strip()]
        if v:
            lines.append(f"\n{label}: mean {statistics.mean(v):.2f} / 5 (n={len(v)})")
    comments = [r["comment"] for _, _, r in scores if r.get("comment", "").strip()]
    if comments:
        lines += ["", "## Comments", ""] + [f"- {c}" for c in comments]
    out = ROOT / "eval" / "results" / "sus.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
