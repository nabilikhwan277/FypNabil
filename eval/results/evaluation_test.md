# Phase 7 evaluation (test split)

> Labels are **silver**: AI-written answers marked by an AI 'strict teacher', plus rule-built answers whose mark is known by construction. They are NOT teacher marks. Treat these as a development estimate; the thesis figures must come from teacher-marked answers.

Chosen configuration: `no_llm_sim` (Tahap 1 `sim`, Tahap 2/3 `sim`), tuned on train only.

## Overall

| Group | n | Exact | Within 1 mark | MAE (marks) | MAE % | QWK | Criterion acc | Over-marked | Under-marked |
|---|---|---|---|---|---|---|---|---|---|
| phase4_baseline | 485 | 0.849 | 0.953 | 0.19 | 6.0 | 0.921 | 0.910 | 0.074 | 0.076 |
| no_llm_sim | 485 | 0.841 | 0.953 | 0.19 | 6.2 | 0.920 | 0.911 | 0.068 | 0.091 |

## By Level (no_llm_sim)

| Group | n | Exact | Within 1 mark | MAE (marks) | MAE % | QWK | Criterion acc | Over-marked | Under-marked |
|---|---|---|---|---|---|---|---|---|---|
| Tahap 1 | 241 | 0.938 | 0.996 | 0.05 | 3.5 | 0.953 | 0.946 | 0.025 | 0.037 |
| Tahap 2 | 181 | 0.785 | 0.917 | 0.30 | 9.2 | 0.866 | 0.887 | 0.094 | 0.122 |
| Tahap 3 | 63 | 0.635 | 0.889 | 0.46 | 7.7 | 0.931 | 0.918 | 0.159 | 0.206 |

## By Subject (no_llm_sim)

| Group | n | Exact | Within 1 mark | MAE (marks) | MAE % | QWK | Criterion acc | Over-marked | Under-marked |
|---|---|---|---|---|---|---|---|---|---|
| fiqh | 147 | 0.837 | 0.946 | 0.20 | 7.1 | 0.911 | 0.904 | 0.068 | 0.095 |
| jawi | 141 | 0.887 | 0.972 | 0.14 | 4.3 | 0.933 | 0.929 | 0.035 | 0.078 |
| tajwid | 197 | 0.812 | 0.944 | 0.22 | 6.9 | 0.916 | 0.903 | 0.091 | 0.096 |

## By Family (no_llm_sim)

| Group | n | Exact | Within 1 mark | MAE (marks) | MAE % | QWK | Criterion acc | Over-marked | Under-marked |
|---|---|---|---|---|---|---|---|---|---|
| paraphrase | 163 | 0.577 | 0.865 | 0.51 | 16.3 | 0.735 | 0.792 | 0.178 | 0.245 |
| programmatic | 322 | 0.975 | 0.997 | 0.03 | 1.1 | 0.983 | 0.986 | 0.012 | 0.012 |

## By Script (no_llm_sim)

| Group | n | Exact | Within 1 mark | MAE (marks) | MAE % | QWK | Criterion acc | Over-marked | Under-marked |
|---|---|---|---|---|---|---|---|---|---|
| jawi | 146 | 0.897 | 0.959 | 0.14 | 3.4 | 0.959 | 0.934 | 0.055 | 0.048 |
| rumi | 339 | 0.817 | 0.950 | 0.22 | 7.4 | 0.892 | 0.902 | 0.074 | 0.109 |

## By Kind (no_llm_sim)

| Group | n | Exact | Within 1 mark | MAE (marks) | MAE % | QWK | Criterion acc | Over-marked | Under-marked |
|---|---|---|---|---|---|---|---|---|---|
| dont_know | 76 | 0.987 | 1.000 | 0.01 | 1.3 | 0.000 | 0.994 | 0.013 | 0.000 |
| jawi_typo | 7 | 1.000 | 1.000 | 0.00 | 0.0 | 1.000 | 1.000 | 0.000 | 0.000 |
| misconception | 56 | 0.661 | 0.821 | 0.52 | 13.7 | 0.232 | 0.836 | 0.339 | 0.000 |
| number_swap | 8 | 1.000 | 1.000 | 0.00 | 0.0 | 1.000 | 1.000 | 0.000 | 0.000 |
| other_topic | 76 | 0.961 | 1.000 | 0.04 | 0.9 | 0.000 | 0.983 | 0.039 | 0.000 |
| paraphrase_full | 56 | 0.643 | 0.875 | 0.52 | 15.9 | 0.000 | 0.816 | 0.000 | 0.357 |
| partial | 51 | 0.412 | 0.902 | 0.50 | 19.4 | 0.261 | 0.721 | 0.196 | 0.392 |
| ref_jawi | 76 | 0.987 | 1.000 | 0.01 | 0.4 | 0.000 | 0.994 | 0.000 | 0.013 |
| ref_rumi | 68 | 0.956 | 0.985 | 0.07 | 2.2 | 0.000 | 0.970 | 0.000 | 0.044 |
| rumi_for_jawi | 7 | 1.000 | 1.000 | 0.00 | 0.0 | 1.000 | 1.000 | 0.000 | 0.000 |
| tf_flip | 4 | 1.000 | 1.000 | 0.00 | 0.0 | 1.000 | 1.000 | 0.000 | 0.000 |

## Live pipeline (real models)

- Answers run: 60 x 3 = 180 assessments, errors: 0 (success rate 1.0)
- Consistency (same answer, same score in all 3 runs): **1.0**
- Live score = offline replay: 1.0
- Feedback grounded (correct answer = reference, textbook page given, 5-step trace): 1.0

| Level | runs | median ms | p95 ms | mean ms |
|---|---|---|---|---|
| Tahap 1 | 60 | 56 | 70 | 56 |
| Tahap 2 | 60 | 70 | 95 | 71 |
| Tahap 3 | 60 | 154 | 245 | 168 |

## Largest disagreements

- `fiqh_b1_solat_tahajud_q4::paraphrase_full` silver 3 / predicted 0.0 (max 3)
- `fiqh_b1_solat_witir_q4::paraphrase_full` silver 3 / predicted 0.0 (max 3)
- `jawi_b3_pinjaman_arab_q5::paraphrase_full` silver 2 / predicted 0.0 (max 2)
- `jawi_b1_imbuhan_an_alif_nun_q8::ref_rumi` silver 3 / predicted 0.0 (max 3)
- `tajwid_b2_mad_asli_kalimi_q3::dont_know` silver 0.0 / predicted 1 (max 1)
- `fiqh_b1_solat_dhuha_q5::misconception` silver 0.0 / predicted 2.0 (max 3)
- `fiqh_b2_batal_puasa_q5::paraphrase_full` silver 3 / predicted 1.0 (max 3)
- `fiqh_b2_latihan_q8::misconception` silver 0.0 / predicted 2.0 (max 3)
- `tajwid_b3_mad_farq_q5::paraphrase_full` silver 3 / predicted 1.0 (max 3)
- `tajwid_b3_mad_lin_q5::misconception` silver 1.0 / predicted 3 (max 3)
- `tajwid_b4_tingkatan_mad_q6::misconception` silver 0.0 / predicted 2.0 (max 3)
- `fiqh_b1_latihan_q6::partial` silver 0.5 / predicted 1 (max 1)
- `fiqh_b1_solat_dhuha_q5::partial` silver 1.5 / predicted 3 (max 3)
- `fiqh_b1_solat_taubat_q3::partial` silver 0.5 / predicted 1 (max 1)
- `fiqh_b1_solat_witir_q2::misconception` silver 0.0 / predicted 1.0 (max 2)
- `fiqh_b2_batal_puasa_q2::partial` silver 0.5 / predicted 0.0 (max 1)
- `fiqh_b2_fadhilat_puasa_q1::partial` silver 0.5 / predicted 0.0 (max 1)
- `fiqh_b2_latihan_q3::partial` silver 0.5 / predicted 1 (max 1)
- `jawi_b3_pinjaman_arab_q7::misconception` silver 1.0 / predicted 3.0 (max 4)
- `tajwid_b1_mad_bahagian_q3::partial` silver 0.5 / predicted 0.0 (max 1)
