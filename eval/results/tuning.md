# Phase 5 tuning (train split, silver labels)

Items: 446 (paraphrase 263, programmatic 183). Labels are silver (AI-written, not teacher-marked).

Tahap 1 rule chosen: `sim(hi=0.95)`

| config | l23 | unresolved_criteria | crit_acc | unres_acc | mark_err_rate | item_exact | mae_pct | qwk_band | over_marked | under_marked |
|---|---|---|---|---|---|---|---|---|---|---|
| phase4_baseline | gen(guard=0.60) | 467 | 0.837 | 0.769 | 0.14 | 0.747 | 11.1 | 0.822 | 0.13 | 0.123 |
| gen_guard_0.50 | gen(guard=0.50) | 467 | 0.797 | 0.677 | 0.181 | 0.709 | 14.3 | 0.775 | 0.222 | 0.07 |
| gen_guard_0.55 | gen(guard=0.55) | 467 | 0.827 | 0.745 | 0.15 | 0.735 | 12.1 | 0.805 | 0.164 | 0.101 |
| gen_guard_0.60 | gen(guard=0.60) | 467 | 0.837 | 0.769 | 0.14 | 0.747 | 11.1 | 0.822 | 0.13 | 0.123 |
| gen_guard_0.65 | gen(guard=0.65) | 467 | 0.851 | 0.801 | 0.125 | 0.76 | 10.1 | 0.844 | 0.103 | 0.137 |
| gen_guard_0.70 | gen(guard=0.70) | 467 | 0.846 | 0.79 | 0.129 | 0.756 | 10.5 | 0.833 | 0.096 | 0.148 |
| gen_guard_0.75 | gen(guard=0.75) | 467 | 0.848 | 0.794 | 0.127 | 0.76 | 10.3 | 0.835 | 0.092 | 0.148 |
| l1_tuned+baseline_l23 | gen(guard=0.60) | 467 | 0.838 | 0.771 | 0.138 | 0.749 | 10.9 | 0.827 | 0.128 | 0.123 |
| no_llm_sim | sim(hi=0.65) | 467 | 0.853 | 0.805 | 0.122 | 0.762 | 9.9 | 0.851 | 0.103 | 0.135 |
| no_llm_sims | sims(hi=0.75,w=0.7) | 467 | 0.852 | 0.803 | 0.123 | 0.765 | 9.9 | 0.85 | 0.099 | 0.137 |
| no_llm_overlap | overlap(hi=0.80) | 467 | 0.838 | 0.771 | 0.137 | 0.756 | 10.8 | 0.831 | 0.121 | 0.123 |
| no_llm_mix | mix(hi=0.85,lo=0.75,w=0.3) | 467 | 0.848 | 0.794 | 0.124 | 0.76 | 10.0 | 0.845 | 0.094 | 0.146 |
| llm_prob_zeroshot | prob_zs(hi=0.95) | 467 | 0.846 | 0.79 | 0.128 | 0.758 | 10.3 | 0.838 | 0.09 | 0.152 |
| llm_prob_fewshot | prob_fs(hi=0.95) | 467 | 0.83 | 0.754 | 0.145 | 0.751 | 11.3 | 0.816 | 0.105 | 0.143 |
| hybrid_zeroshot | hybrid_zs(hi=0.85,lo=0.80,w=0.3) | 467 | 0.849 | 0.797 | 0.124 | 0.765 | 10.0 | 0.843 | 0.092 | 0.143 |
| hybrid_fewshot | hybrid_fs(hi=0.85,w=0.5) | 467 | 0.85 | 0.799 | 0.124 | 0.767 | 10.0 | 0.843 | 0.099 | 0.135 |
| llm_generative | gen(guard=0.65) | 467 | 0.852 | 0.803 | 0.123 | 0.762 | 9.9 | 0.849 | 0.101 | 0.137 |

**Lowest error:** `no_llm_sim`. **Deployed:** `no_llm_sim` - Tahap 1 `sim(hi=0.95)`, Tahap 2/3 `sim(hi=0.65)`

## Signal quality (AUC, ya vs tidak, unresolved Tahap 2/3 criteria)

| signal | value |
|---|---|
| sim | 0.762 |
| ans_sim | 0.805 |
| sims | 0.821 |
| overlap | 0.684 |
| mix | 0.748 |
| prob_zs | 0.56 |
| prob_fs | 0.552 |
| gen_says_ya_when_gold_ya | 1.0 |
| gen_says_ya_when_gold_tidak | 1.0 |
| n_unresolved_l23 | 380 |

## Chosen vs baseline by answer kind

| kind | baseline mae_pct | chosen mae_pct | baseline exact | chosen exact |
|---|---|---|---|---|
| dont_know | 0.0 | 0.0 | 1.0 | 1.0 |
| jawi_typo | 0.0 | 0.0 | 1.0 | 1.0 |
| misconception | 17.8 | 10.9 | 0.656 | 0.756 |
| number_swap | 12.0 | 8.0 | 0.88 | 0.92 |
| other_topic | 0.0 | 0.0 | 1.0 | 1.0 |
| paraphrase_full | 12.8 | 15.0 | 0.689 | 0.678 |
| partial | 22.4 | 22.1 | 0.398 | 0.373 |
| ref_jawi | 0.0 | 0.0 | 1.0 | 1.0 |
| ref_rumi | 1.3 | 1.3 | 0.96 | 0.96 |
| rumi_for_jawi | 0.0 | 0.0 | 1.0 | 1.0 |
| tf_flip | 0.0 | 0.0 | 1.0 | 1.0 |
