# Phase 4: fine-tuning and a hybrid model

All on the 50 teacher answers with the proposed system (R3, A2, memory off). QWK [95% bootstrap CI]; a change is a paired difference on the same answers (**bold** = significant, its interval leaves out 0).

Training data: 490 answers for training and 88 for validation (silver answers; reply to learn = silver verdicts with GPT-6 Luna's reasons and feedback; see finetune_data.md).

## Training: validation loss (lower is better)

QLoRA on unsloth/Qwen3-4B-Instruct-2507-bnb-4bit, learning rate 0.0002 (constant, 5 warm-up steps), 8 answers per update, alpha = 2 x rank, dropout 0.05, all attention and MLP projections. The adapter used for the hybrid is chosen by this loss, before the teacher test: **r8e2**.

| LoRA rank | After 1 epoch | After 2 epochs | Training time |
|---|---|---|---|
| 8 | 0.3117 | 0.2904 | 47.0 min |
| 16 | 0.3006 | 0.2920 | 47.2 min |

## Marking: fine-tuned vs base Qwen3-4B

| Model | QWK [95% CI] | Change from base | Exact | Within 1 | QWK Ibadah | QWK Jawi | QWK Tajwid | 'separa' given (teachers) | Valid marks | s / answer | Jawi test |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3-4B (open-weight) | 0.694 [0.50, 0.84] | – | 60% | 79% | 0.553 | 0.519 | 0.937 | 13% (17%) | 94% | 18.4 | 7% |
| Qwen3-4B fine-tuned (LoRA r8, 1 epoch) | 0.741 [0.55, 0.88] | +0.047 [-0.10, +0.20] | 68% | 79% | 0.683 | 0.572 | 0.914 | 1% (17%) | 100% | 25.6 | 13% |
| Qwen3-4B fine-tuned (LoRA r8, 2 epochs) | 0.701 [0.50, 0.86] | +0.007 [-0.15, +0.18] | 64% | 82% | 0.687 | 0.439 | 0.914 | 1% (17%) | 100% | 27.4 | 13% |
| Qwen3-4B fine-tuned (LoRA r16, 1 epoch) | 0.701 [0.51, 0.85] | +0.007 [-0.15, +0.17] | 62% | 79% | 0.615 | 0.503 | 0.914 | 0% (17%) | 100% | 25.5 | 13% |
| Qwen3-4B fine-tuned (LoRA r16, 2 epochs) | 0.743 [0.55, 0.90] | +0.049 [-0.11, +0.21] | 66% | 85% | 0.703 | 0.533 | 0.938 | 4% (17%) | 100% | 25.1 | 13% |
| GPT-6 Luna | 0.755 [0.58, 0.90] | +0.062 [-0.08, +0.22] | 62% | 85% | 0.742 | 0.527 | 0.947 | 3% (17%) | 100% | 3.5 | 70% |

## Hybrid: open model + GPT-6 Luna

- Router A: Tahap 1 to the open model, Tahap 2-3 to GPT-6 Luna
- Router B: open model first; GPT-6 Luna when its reply is invalid or has a 'separa' verdict
- Router C: open model first; GPT-6 Luna when its reply is invalid or its score differs from the rule-based scorer (B2)

| System | QWK [95% CI] | Change from GPT-6 Luna alone | Answers sent to Luna | $ / 100 answers | s / answer |
|---|---|---|---|---|---|
| GPT-6 Luna | 0.755 [0.58, 0.90] | – | 100% | $0.030 | 3.5 |
| Qwen3-4B (open-weight) | 0.694 [0.50, 0.84] | -0.062 [-0.22, +0.08] | 0% | $0.000 | 18.4 |
| Qwen3-4B fine-tuned (LoRA r8, 2 epochs) | 0.701 [0.50, 0.86] | -0.054 [-0.15, +0.03] | 0% | $0.000 | 27.4 |
| Qwen3-4B (open-weight) + GPT-6 Luna (Router A) | 0.785 [0.60, 0.92] | +0.030 [+0.00, +0.07] | 48% | $0.017 | 8.2 |
| Qwen3-4B (open-weight) + GPT-6 Luna (Router B) | 0.764 [0.58, 0.90] | +0.009 [-0.03, +0.06] | 32% | $0.011 | 19.5 |
| Qwen3-4B (open-weight) + GPT-6 Luna (Router C) | 0.737 [0.55, 0.88] | -0.018 [-0.06, +0.00] | 54% | $0.017 | 20.2 |
| Qwen3-4B fine-tuned (LoRA r8, 2 epochs) + GPT-6 Luna (Router A) | 0.733 [0.54, 0.89] | -0.022 [-0.11, +0.05] | 48% | $0.017 | 10.4 |
| Qwen3-4B fine-tuned (LoRA r8, 2 epochs) + GPT-6 Luna (Router B) | 0.709 [0.51, 0.87] | -0.047 [-0.14, +0.03] | 2% | $0.001 | 27.5 |
| Qwen3-4B fine-tuned (LoRA r8, 2 epochs) + GPT-6 Luna (Router C) | 0.703 [0.50, 0.86] | -0.052 [-0.14, +0.01] | 34% | $0.011 | 28.6 |

Open-model times are on a Colab L4 GPU; a hybrid's time is the open model's plus Luna's for the answers it sends on.
