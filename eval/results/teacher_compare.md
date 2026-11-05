# E1: system vs each teacher

Answers: 50 · fully agreed answers: 16 · agreed criteria: 40

## Human baseline (teacher vs teacher)

| Pair | QWK | Exact | Within 1 mark (2+ marks) | MAE |
|---|---|---|---|---|
| guru_1 vs guru_2 | 0.497 | 48.0% | 64.7% | 0.82 |
| guru_1 vs guru_3 | 0.516 | 54.0% | 64.7% | 0.69 |
| guru_2 vs guru_3 | 0.334 | 44.0% | 67.6% | 0.83 |

## System vs teachers

| Configuration | QWK vs Guru 1 | QWK vs Guru 2 | QWK vs Guru 3 | Mean QWK | Exact (mean) | Agreed criteria correct | Human level? |
|---|---|---|---|---|---|---|---|
| proposed:luna:R3:A2:off | 0.760 | 0.464 | 0.555 | 0.593 | 55.3% | 87.5% | yes |
| hybrid:qwen+luna:R3:A2:level | 0.784 | 0.500 | 0.491 | 0.592 | 56.0% | 87.5% | yes |
| proposed:luna:R3:A2:on | 0.755 | 0.484 | 0.534 | 0.591 | 54.0% | 87.5% | yes |
| hybrid:qwen+luna:R3:A2:separa | 0.784 | 0.454 | 0.512 | 0.583 | 58.0% | 87.5% | yes |
| hybrid:qwen+luna:R3:A2:rules | 0.743 | 0.455 | 0.546 | 0.581 | 54.7% | 82.5% | yes |
| proposed:luna:R3:A3:off | 0.755 | 0.423 | 0.524 | 0.567 | 56.7% | 87.5% | yes |
| proposed:luna:R3:A1:off | 0.733 | 0.464 | 0.499 | 0.565 | 54.7% | 87.5% | yes |
| proposed:luna:R1:A2:off | 0.733 | 0.464 | 0.499 | 0.565 | 54.0% | 87.5% | yes |
| proposed:luna:R2:A2:off | 0.733 | 0.464 | 0.499 | 0.565 | 53.3% | 87.5% | yes |
| hybrid:qwen_ft_r8e2+luna:R3:A2:level | 0.766 | 0.448 | 0.480 | 0.565 | 56.0% | 87.5% | yes |
| proposed:qwen_ft_r16e2:R3:A2:off | 0.794 | 0.405 | 0.497 | 0.565 | 58.7% | 87.5% | yes |
| proposed:qwen_ft_r8e1:R3:A2:off | 0.774 | 0.428 | 0.485 | 0.562 | 58.0% | 87.5% | yes |
| proposed:haiku:R1:A2:off | 0.769 | 0.381 | 0.528 | 0.559 | 53.3% | 87.5% | yes |
| proposed:haiku:R3:A2:off | 0.776 | 0.388 | 0.505 | 0.556 | 56.7% | 87.5% | yes |
| b3:luna:R1 | 0.715 | 0.441 | 0.504 | 0.553 | 53.3% | 87.5% | yes |
| b4:luna:R1 | 0.715 | 0.441 | 0.504 | 0.553 | 53.3% | 87.5% | yes |
| hybrid:qwen_ft_r8e2+luna:R3:A2:rules | 0.750 | 0.373 | 0.531 | 0.551 | 54.7% | 90.0% | yes |
| proposed:qwen_ft_r16e1:R3:A2:off | 0.749 | 0.383 | 0.519 | 0.550 | 56.7% | 87.5% | yes |
| b1:luna | 0.744 | 0.392 | 0.510 | 0.549 | 54.7% | 87.5% | yes |
| proposed:qwen:R3:A2:off | 0.665 | 0.471 | 0.502 | 0.546 | 54.0% | 82.5% | yes |
| hybrid:qwen_ft_r8e2+luna:R3:A2:separa | 0.782 | 0.359 | 0.484 | 0.542 | 58.7% | 90.0% | yes |
| proposed:sealion:R3:A2:off | 0.726 | 0.455 | 0.437 | 0.539 | 51.3% | 82.5% | yes |
| proposed:qwen_ft_r8e2:R3:A2:off | 0.767 | 0.355 | 0.478 | 0.533 | 58.7% | 87.5% | yes |
| proposed:fanar:R3:A2:off | 0.599 | 0.417 | 0.379 | 0.465 | 48.7% | 77.5% | yes |
| proposed:llama:R3:A2:off | 0.484 | 0.345 | 0.482 | 0.437 | 51.3% | 80.0% | no |
| proposed:llama:R1:A2:off | 0.432 | 0.372 | 0.439 | 0.414 | 51.3% | 80.0% | no |
| b2 | 0.521 | 0.188 | 0.415 | 0.375 | 48.0% | 65.0% | no |

Human level = the system's mean QWK with the teachers is at least the teachers' QWK with each other.
