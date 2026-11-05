# R3 settings for marking: check on the silver development answers

GPT-6 Luna, proposed system (R3, A2, memory off), 171 silver answers (paraphrase_full 56, misconception 56, partial 51, number_swap 8). QWK of the score bands against the silver labels, 95% bootstrap interval; the change is paired against the earlier setting (**bold** = significant).

| R3 setting | Chunks | Sections | Minimum similarity | QWK [95% CI] | Change from earlier | Criterion accuracy | Valid |
|---|---|---|---|---|---|---|---|
| earlier | 4 | 3 | none | 0.960 [0.94, 0.98] | – | 94% | 100% |
| study | 6 | 5 | 0.35 | 0.964 [0.94, 0.98] | +0.004 [-0.01, +0.02] | 95% | 100% |
| sections | 6 | 5 | none | 0.964 [0.94, 0.98] | +0.004 [-0.01, +0.02] | 95% | 100% |
| minimum | 4 | 3 | 0.35 | 0.960 [0.94, 0.98] | +0.000 [+0.00, +0.00] | 94% | 100% |

**Rule outcome** (fixed before the run: keep the earlier R3 for marking unless a study setting scores at least as high): **study**, but only by a difference far inside the noise: the silver answers are too easy to separate the settings, and the minimum similarity removed nothing (the same marks as without it).

## The same settings on the 50 teacher answers

Runs on the final teacher marks with the earlier R3 and with the study's R3 (archived in `eval/results/archive/r3_study_settings_2nov/`); paired bootstrap, 2,000 resamples.

| Configuration | Earlier R3 | Study's R3 | Change [95% CI] |
|---|---|---|---|
| proposed:luna:R3:A2:off | 0.755 | 0.695 | **-0.060 [-0.152, -0.002]** |
| proposed:luna:R3:A2:on | 0.736 | 0.697 | -0.039 [-0.126, +0.000] |
| proposed:luna:R3:A1:off | 0.700 | 0.714 | +0.013 [-0.008, +0.053] |
| proposed:luna:R3:A3:off | 0.722 | 0.714 | -0.009 [-0.024, +0.000] |
| proposed:haiku:R3:A2:off | 0.729 | 0.636 | **-0.094 [-0.232, -0.004]** |

**Final decision:** Because the silver answers could not separate the settings and the teacher set showed a significant drop for the final system, the researcher decided on 2 Nov 2026 that marking keeps the earlier R3. The study's choices stay where they were measured: Tanya Bulan's lower gate with the decline rule. Marking uses **earlier** (4 chunks, 3 sections, no minimum).

API cost of the silver check: $0.063 (first run; the answers are cached, so a rerun is free).
