# ReAct types: process and outcome (GPT-6 Luna, R3, memory off (Step 3))

## A1 Vanilla ReAct

| | All (n=50) | Ibadah (n=18) | Jawi (n=14) | Tajwid (n=18) |
|---|---|---|---|---|
| Completed (valid marks) | 100% | 100% | 100% | 100% |
| Criterion verdicts = final teacher mark | 71% | 71% | 60% | 79% |
| Model calls per answer | 3.0 | 3.0 | 2.9 | 3.1 |
| Tokens per answer | 4201 | 4127 | 3959 | 4464 |
| Model time per answer | 13.9 s | 13.9 s | 11.7 s | 15.6 s |
| Cost per 100 answers | $0.081 | $0.079 | $0.069 | $0.091 |

## A2 Constrained ReAct

| | All (n=50) | Ibadah (n=18) | Jawi (n=14) | Tajwid (n=18) |
|---|---|---|---|---|
| Completed (valid marks) | 100% | 100% | 100% | 100% |
| Criterion verdicts = final teacher mark | 71% | 69% | 60% | 82% |
| Model calls per answer | 1.0 | 1.0 | 1.0 | 1.0 |
| Tokens per answer | 1801 | 1702 | 2048 | 1708 |
| Model time per answer | 4.0 s | 4.0 s | 4.2 s | 3.9 s |
| Cost per 100 answers | $0.028 | $0.027 | $0.030 | $0.027 |

## A3 Reflexion

| | All (n=50) | Ibadah (n=18) | Jawi (n=14) | Tajwid (n=18) |
|---|---|---|---|---|
| Completed (valid marks) | 100% | 100% | 100% | 100% |
| Criterion verdicts = final teacher mark | 71% | 71% | 60% | 79% |
| Model calls per answer | 2.0 | 2.0 | 2.0 | 2.0 |
| Tokens per answer | 3746 | 3576 | 4200 | 3562 |
| Model time per answer | 8.5 s | 8.6 s | 8.5 s | 8.5 s |
| Cost per 100 answers | $0.061 | $0.060 | $0.064 | $0.059 |

## A1: what the free tool loop did

| | All (n=50) | Ibadah (n=18) | Jawi (n=14) | Tajwid (n=18) |
|---|---|---|---|---|
| Steps (mean) | 3.0 | 3.0 | 2.9 | 3.1 |
| Read the rubric before marking | 100% | 100% | 100% | 100% |
| Searched the textbook before marking | 84% | 83% | 79% | 89% |
| Did both | 84% | 83% | 79% | 89% |
| Repeated an action | 4 | 1 | 2 | 1 |
| Unknown action | 1 | 1 | 0 | 0 |
| Same textbook sections as A2 | 66% | 76% | 57% | 63% |

Most common A1 step orders (all subjects):

- get_rubric → search_notes → submit_marks (34)
- get_rubric → submit_marks (8)
- get_rubric → search_notes → get_history → submit_marks (3)
- get_rubric → get_rubric → search_notes → submit_marks (2)
- get_rubric → search_notes → search_notes → submit_marks (1)

## A1 vs A2: criteria where they disagree, who matches the final teacher mark

| | All (n=50) | Ibadah (n=18) | Jawi (n=14) | Tajwid (n=18) |
|---|---|---|---|---|
| A2 right | 1 | 0 | 0 | 1 |
| A1 right | 1 | 1 | 0 | 0 |
| both wrong | 1 | 1 | 0 | 0 |

## A3: what the critic changed (LLM-marked criteria; draft → final)

| | All (n=50) | Ibadah (n=18) | Jawi (n=14) | Tajwid (n=18) |
|---|---|---|---|---|
| unchanged | 92 | 41 | 13 | 38 |
| helped | 1 | 1 | 0 | 0 |
| hurt | 1 | 0 | 0 | 1 |
| changed, both wrong | 1 | 1 | 0 | 0 |
| more lenient | 0 | 0 | 0 | 0 |
| stricter | 3 | 2 | 0 | 1 |
