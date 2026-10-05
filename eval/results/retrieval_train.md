# Retrieval evaluation (train split)

Topic-level: does a chunk from the question's own topic appear in the top-k? No topic filter is applied (the live pipeline does filter by topic).

| Query | Retriever | Subject | n | Recall@1 | Recall@4 | MRR@10 |
|---|---|---|---|---|---|---|
| rumi_subject | dense | all | 306 | 0.824 | 0.964 | 0.884 |
| rumi_subject | dense | fiqh | 90 | 0.922 | 0.989 | 0.949 |
| rumi_subject | dense | jawi | 91 | 0.681 | 0.912 | 0.783 |
| rumi_subject | dense | tajwid | 125 | 0.856 | 0.984 | 0.910 |
| rumi_subject | keyword | all | 306 | 0.915 | 0.980 | 0.947 |
| rumi_subject | keyword | fiqh | 90 | 0.878 | 0.978 | 0.921 |
| rumi_subject | keyword | jawi | 91 | 0.956 | 0.989 | 0.975 |
| rumi_subject | keyword | tajwid | 125 | 0.912 | 0.976 | 0.947 |
| rumi_subject | hybrid | all | 306 | 0.899 | 0.990 | 0.942 |
| rumi_subject | hybrid | fiqh | 90 | 0.900 | 0.978 | 0.939 |
| rumi_subject | hybrid | jawi | 91 | 0.879 | 1.000 | 0.938 |
| rumi_subject | hybrid | tajwid | 125 | 0.912 | 0.992 | 0.947 |
| jawi_subject | dense | all | 306 | 0.618 | 0.807 | 0.707 |
| jawi_subject | dense | fiqh | 90 | 0.622 | 0.789 | 0.699 |
| jawi_subject | dense | jawi | 91 | 0.440 | 0.659 | 0.544 |
| jawi_subject | dense | tajwid | 125 | 0.744 | 0.928 | 0.831 |
| jawi_subject | keyword | all | 306 | 0.879 | 0.974 | 0.927 |
| jawi_subject | keyword | fiqh | 90 | 0.856 | 0.956 | 0.906 |
| jawi_subject | keyword | jawi | 91 | 0.890 | 0.989 | 0.940 |
| jawi_subject | keyword | tajwid | 125 | 0.888 | 0.976 | 0.933 |
| jawi_subject | hybrid | all | 306 | 0.869 | 0.958 | 0.915 |
| jawi_subject | hybrid | fiqh | 90 | 0.789 | 0.922 | 0.857 |
| jawi_subject | hybrid | jawi | 91 | 0.890 | 0.978 | 0.934 |
| jawi_subject | hybrid | tajwid | 125 | 0.912 | 0.968 | 0.942 |
| rumi_all | dense | all | 306 | 0.807 | 0.935 | 0.864 |
| rumi_all | dense | fiqh | 90 | 0.922 | 0.989 | 0.948 |
| rumi_all | dense | jawi | 91 | 0.648 | 0.824 | 0.734 |
| rumi_all | dense | tajwid | 125 | 0.840 | 0.976 | 0.898 |
| rumi_all | keyword | all | 306 | 0.902 | 0.974 | 0.938 |
| rumi_all | keyword | fiqh | 90 | 0.878 | 0.967 | 0.918 |
| rumi_all | keyword | jawi | 91 | 0.923 | 0.978 | 0.953 |
| rumi_all | keyword | tajwid | 125 | 0.904 | 0.976 | 0.943 |
| rumi_all | hybrid | all | 306 | 0.873 | 0.977 | 0.923 |
| rumi_all | hybrid | fiqh | 90 | 0.889 | 0.978 | 0.933 |
| rumi_all | hybrid | jawi | 91 | 0.802 | 0.956 | 0.880 |
| rumi_all | hybrid | tajwid | 125 | 0.912 | 0.992 | 0.948 |

Misses at k=4 (rumi_subject, hybrid): 3

- `fiqh_b1_solat_tahajud_q6` rank=None top1=`fiqh_b1_pengenalan`: Puan Siti sering mengeluh tentang masalah yang menimpanya kerana tiada pekerjaan tetap dan
- `fiqh_b2_latihan_q7` rank=None top1=`fiqh_b2_pengertian_puasa`: Latihan 2: Baca dan fahami situasi di bawah. Kemudian, nyatakan hukum beserta alasannya. A
- `tajwid_b4_tingkatan_mad_q1` rank=None top1=`tajwid_b3_mad_lazim_harfi_muthaqqal`: Berapakah kadar harakat bacaan Mad Lazim?
