# Weight updates and external systems in general AI research

The baseline samples arXiv submissions whose primary category is cs.AI, cs.LG, stat.ML, cs.CL, cs.CV, cs.RO or cs.NE, from November 2021 through October 2026. Each arXiv ID counts once. Every eligible submission can enter the draw, including work unrelated to alignment and work that falls in none of the mechanism categories. This measures publication mix in those categories. The original alignment estimates use a separate arXiv-plus-ACL search and audit.

## Review criteria

Use title and abstract. Mark W for a substantive contribution that trains or updates the principal predictor, generator or acting policy, including new learned architectures, training objectives, or analysis of a specific weight-changing method. Merely running a pretrained model or training standard models to evaluate a benchmark is insufficient.

Mark E for an external supervisor, filter, monitor, enforced constraint or control rule that governs the outputs, decisions or actions of an AI or autonomous system. Include controllers that supervise execution or enforce operational limits. An ordinary controller that supplies the acting policy by itself, an auxiliary training loss, a classifier predicting a property in isolation, and offline verification alone are insufficient.

Mark H for a substantive external execution framework that organizes how a model or agent performs a task, including orchestration of model calls, tool or retrieval pipelines, multi-agent workflows, or an execution layer mediating actions. Architecture inside the predictor and training-only pipelines are insufficient. This broader engineering definition includes capability-oriented scaffolds. A hard action gate can qualify for E and H. A retrieval pipeline can qualify for H alone. An output monitor can qualify for E alone.

Score mechanisms independently. Allow hybrids. Count reviews, evaluation and theory without a qualifying intervention in the full denominator. Decisions are exploratory judgments from one AI reviewer. Unspecified mechanisms receive no credit.

## Sampling and replication

To improve coverage of relatively uncommon controls, baseline.py predefines a stratum of titles or abstracts matching a list of control, supervision or workflow cues, including weak cues such as supervised learning. Draw 80 cue-matched and 100 other records using the lowest SHA-256 ranks of a fixed salt and arXiv ID within each stratum. The cues determine sampling probabilities only. Estimate population totals by multiplying each stratum mean by its population size. Ratio intervals use the paired linearized log ratio, finite-population variance and a t critical value. Intervals cover sampling variability conditional on the labels.

Run `python baseline.py` from this directory to recompute results. The optional `--draw-from /path/to/catalog.sqlite` regenerates the frozen draw using the original metadata catalog. The sample and review tables join on review_id.

## What the baseline shows

The frame contains 375,724 arXiv submissions in the seven primary categories. Across 180 reviewed papers, 100 received W, 12 received E, and 31 received H. The 80 cue-matched papers represent 102,623 submissions and the 100 other papers represent 273,101. A paper can receive multiple codes.

| Mechanism counted | Estimated share of all submissions | Weight-update papers per comparator paper (95% interval) |
|---|---:|---:|
| Weight updates | 54.6% | — |
| External control | 4.9% | 11.2 (6.0–21.0) |
| External execution framework | 14.8% | 3.7 (2.4–5.6) |
| Either external category, counting overlaps once | 16.6% | 3.3 (2.2–4.9) |

The closest general-AI comparison to the earlier 7.2 estimate is 11.2, because both use external control as the comparator. The two studies have different sampling frames and subject mixes. This comparison leaves open whether explicitly alignment-framed papers differ from otherwise comparable AI papers after matching year, application and venue. A research paper on medical image segmentation fits the baseline and may have little reason to include an execution harness.

[All 180 decisions, with titles, links and reasons](data/baseline_review.csv) · [Frozen sample and abstracts](data/baseline_draw.csv) · [Statistical estimates](results/general_ai_baseline.json)
