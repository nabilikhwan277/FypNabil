# Retrieval evaluation (test split)

Topic-level: does a chunk from the question's own topic appear in the top-k? No topic filter is applied (the live pipeline does filter by topic).

| Query | Retriever | Subject | n | Recall@1 | Recall@4 | MRR@10 |
|---|---|---|---|---|---|---|
| rumi_subject | dense | all | 76 | 0.855 | 0.947 | 0.898 |
| rumi_subject | dense | fiqh | 23 | 0.870 | 0.870 | 0.877 |
| rumi_subject | dense | jawi | 22 | 0.864 | 0.955 | 0.902 |
| rumi_subject | dense | tajwid | 31 | 0.839 | 1.000 | 0.911 |
| rumi_subject | keyword | all | 76 | 0.921 | 0.987 | 0.957 |
| rumi_subject | keyword | fiqh | 23 | 0.913 | 1.000 | 0.957 |
| rumi_subject | keyword | jawi | 22 | 0.909 | 1.000 | 0.955 |
| rumi_subject | keyword | tajwid | 31 | 0.935 | 0.968 | 0.958 |
| rumi_subject | hybrid | all | 76 | 0.908 | 1.000 | 0.951 |
| rumi_subject | hybrid | fiqh | 23 | 0.870 | 1.000 | 0.924 |
| rumi_subject | hybrid | jawi | 22 | 0.955 | 1.000 | 0.977 |
| rumi_subject | hybrid | tajwid | 31 | 0.903 | 1.000 | 0.952 |
| jawi_subject | dense | all | 76 | 0.487 | 0.737 | 0.613 |
| jawi_subject | dense | fiqh | 23 | 0.435 | 0.565 | 0.518 |
| jawi_subject | dense | jawi | 22 | 0.409 | 0.773 | 0.583 |
| jawi_subject | dense | tajwid | 31 | 0.581 | 0.839 | 0.705 |
| jawi_subject | keyword | all | 76 | 0.908 | 0.987 | 0.947 |
| jawi_subject | keyword | fiqh | 23 | 0.870 | 0.957 | 0.911 |
| jawi_subject | keyword | jawi | 22 | 0.909 | 1.000 | 0.955 |
| jawi_subject | keyword | tajwid | 31 | 0.935 | 1.000 | 0.968 |
| jawi_subject | hybrid | all | 76 | 0.816 | 0.934 | 0.881 |
| jawi_subject | hybrid | fiqh | 23 | 0.652 | 0.826 | 0.752 |
| jawi_subject | hybrid | jawi | 22 | 0.955 | 1.000 | 0.977 |
| jawi_subject | hybrid | tajwid | 31 | 0.839 | 0.968 | 0.910 |
| rumi_all | dense | all | 76 | 0.842 | 0.921 | 0.885 |
| rumi_all | dense | fiqh | 23 | 0.870 | 0.870 | 0.877 |
| rumi_all | dense | jawi | 22 | 0.818 | 0.864 | 0.856 |
| rumi_all | dense | tajwid | 31 | 0.839 | 1.000 | 0.911 |
| rumi_all | keyword | all | 76 | 0.895 | 0.974 | 0.937 |
| rumi_all | keyword | fiqh | 23 | 0.870 | 0.957 | 0.922 |
| rumi_all | keyword | jawi | 22 | 0.864 | 1.000 | 0.924 |
| rumi_all | keyword | tajwid | 31 | 0.935 | 0.968 | 0.958 |
| rumi_all | hybrid | all | 76 | 0.842 | 0.987 | 0.909 |
| rumi_all | hybrid | fiqh | 23 | 0.826 | 0.957 | 0.900 |
| rumi_all | hybrid | jawi | 22 | 0.818 | 1.000 | 0.890 |
| rumi_all | hybrid | tajwid | 31 | 0.871 | 1.000 | 0.930 |

Misses at k=4 (rumi_subject, hybrid): 0

