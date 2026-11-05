# Open-weight vs API models (Phase 3)

Same setup for every model: proposed system, R3 Parent-Document RAG, A2 Constrained ReAct, memory off; 50 teacher answers. QWK [95% bootstrap CI]; change = paired difference from the best run of all experiments (**bold** = significant).

## Marking

| Model | Where it ran | QWK [95% CI] | Change from best | Exact | Within 1 mark (2+ marks) | QWK Ibadah | QWK Jawi | QWK Tajwid |
|---|---|---|---|---|---|---|---|---|
| GPT-6 Luna | OpenRouter API | 0.755 [0.58, 0.90] | best | 62% | 85% | 0.742 | 0.527 | 0.947 |
| Claude Haiku 5.5 | OpenRouter API | 0.729 [0.53, 0.89] | -0.026 [-0.12, +0.04] | 66% | 82% | 0.666 | 0.527 | 0.946 |
| Llama 3.1 8B | OpenRouter API | 0.546 [0.33, 0.73] | **-0.209 [-0.40, -0.04]** | 50% | 71% | 0.564 | 0.389 | 0.652 |
| Qwen3-4B (open-weight) | Colab NVIDIA L4, 4-bit NF4 | 0.694 [0.50, 0.84] | -0.061 [-0.22, +0.08] | 60% | 79% | 0.553 | 0.519 | 0.937 |
| Fanar 9B (open-weight) | Colab NVIDIA L4, bfloat16 | 0.624 [0.42, 0.79] | **-0.131 [-0.27, -0.01]** | 50% | 74% | 0.659 | 0.389 | 0.785 |
| SEA-LION v3 9B (open-weight) | Colab NVIDIA L4, bfloat16 | 0.685 [0.50, 0.83] | -0.070 [-0.18, +0.03] | 60% | 76% | 0.648 | 0.560 | 0.812 |

## Reliability, speed and cost

| Model | Valid marks (format followed) | Failed answers | Seconds / answer | $ / 100 answers |
|---|---|---|---|---|
| GPT-6 Luna | 100% | 0 | 3.5 | $0.030 |
| Claude Haiku 5.5 | 98% | 1 | 8.1 | $0.046 |
| Llama 3.1 8B | 98% | 1 | 5.0 | $0.041 |
| Qwen3-4B (open-weight) | 94% | 3 | 18.4 | free (Colab) |
| Fanar 9B (open-weight) | 96% | 2 | 24.2 | free (Colab) |
| SEA-LION v3 9B (open-weight) | 100% | 0 | 24.8 | free (Colab) |

## Jawi reading test (30 textbook words)

| Model | Spelling (Rumi → Jawi) | Reading (Jawi → Rumi) | All |
|---|---|---|---|
| GPT-6 Luna | 53% | 87% | 70% |
| Claude Haiku 5.5 | 40% | 73% | 57% |
| Llama 3.1 8B | 13% | 20% | 17% |
| Qwen3-4B (open-weight) | 7% | 7% | 7% |
| Fanar 9B (open-weight) | 13% | 20% | 17% |
| SEA-LION v3 9B (open-weight) | 0% | 20% | 10% |
