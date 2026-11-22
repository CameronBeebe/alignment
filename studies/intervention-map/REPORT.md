# Where does alignment research intervene?

**Original alignment-only comparison.** The [expanded attention study](ATTENTION.md) tests the general-AI baseline and explicitly includes execution harnesses.

**The five-year evidence supports a narrower version of the hypothesis.** In papers that explicitly use alignment terminology, studies of model-weight updates outnumber studies of external controls by an estimated **7.2 to 1**. Across the broader literature on preferences, safety, oversight and enforcement, the estimate falls to **1.36 to 1**. The broader result is consistent with parity and falls below the prespecified twofold threshold.

| Comparison within retrieved research | Estimated weight-update papers per comparator paper | 95% interval |
|---|---:|---:|
| Core alignment, external controls | **1.36** | **0.98–1.90** |
| Core alignment, external controls or soft inference-time steering | 0.83 | 0.63–1.09 |
| Including adjacent safety engineering, external controls | 1.08 | 0.83–1.40 |
| Explicit alignment vocabulary only, external controls | 7.20 | 2.80–18.49 |

**The balance changed over time.** For core alignment, the weight-to-external-control ratio was **3.75** through 2024 and **0.96** from January 2025 through October 2026. The exploratory test of that change gave *p* = .0023. The early comparison draws its observed mechanism papers from 2023–24. Only five reviewed external-control papers met the explicit-vocabulary rule, which explains the wide interval in the last row.

**Where the distinction matters.** DPO changes the policy that generates an answer. CaMeL limits the data and authority available when an agent acts. SHE revises the harness, including its tool policy, after observing failures. A learned guard can therefore count as external control, and an online weight update still counts as weight-based. An estimated 38% of core papers had no intervention vote, including work on benchmarks, specification and governance. Enforcing a JSON grammar guarantees structural validity. Authorization additionally requires a rule about which action the agent may take. [DPO](https://arxiv.org/abs/2305.18290) · [CaMeL](https://arxiv.org/abs/2503.18813) · [SHE](https://arxiv.org/abs/2608.09885)

**How much confidence to place in the result.** The search covered 1,330,760 dated arXiv and ACL metadata records from November 2021 through October 2026 and retained 25,329 distinct candidates. One AI reviewer coded a stratified random sample of 360, including 215 core papers. The primary comparison had 65 reviewed weight-update papers and 46 external-control papers. After sampling weights, the equality test gave *p* = .060. The intervals cover sampling uncertainty within this corpus. They omit reviewer error and missing publications. In an independent check of 71 safety-titled Learning for Dynamics and Control papers, 56 had exact title matches in the source catalog and 42 reached the candidate set. Definitions and coverage matter enough to change the conclusion. Publication counts alone cannot establish whether researchers allocated too much effort to either approach. [arXiv metadata](https://www.kaggle.com/datasets/Cornell-University/arxiv) · [ACL Anthology](https://aclanthology.org/faq/bib/) · [Venue cross-check](results/venue_index_check.csv)

[Browse the 7,735-paper alignment shortlist](results/alignment_papers.csv) · [Inspect all 360 decisions](results/reviewed_papers.csv) · [Reproduce the study](README.md)
