# Fine-tuning data (Phase 4)

Silver answers as the proposed system's marking request (R3, A2, memory off). Reply to learn: the silver verdicts with GPT-6 Luna's reasons and feedback, kept only where Luna gives the silver verdict on every criterion. No teacher answer is used; validation answers come from other questions than the training answers.

| Split | Group | Answers | Luna criteria = silver label | Kept |
|---|---|---|---|---|
| train | all | 532 | 96% | 490 (92%) |
| train | paraphrase | 263 | 94% | 226 (86%) |
| train | programmatic | 269 | 99% | 264 (98%) |
| train | Ibadah | 159 | 96% | 143 (90%) |
| train | Jawi | 194 | 95% | 177 (91%) |
| train | Tajwid | 179 | 98% | 170 (95%) |
| val | all | 99 | 95% | 88 (89%) |
| val | paraphrase | 60 | 93% | 49 (82%) |
| val | programmatic | 39 | 100% | 39 (100%) |
| val | Ibadah | 32 | 99% | 31 (97%) |
| val | Jawi | 33 | 95% | 29 (88%) |
| val | Tajwid | 34 | 92% | 28 (82%) |

Verdicts in the kept replies: train: separa 40, tidak 584, ya 494; val: separa 8, tidak 99, ya 104

Dropped answers by kind: partial 34, misconception 10, paraphrase_full 4, number_swap 3, ref_rumi 2
