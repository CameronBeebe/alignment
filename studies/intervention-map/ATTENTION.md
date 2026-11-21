# Where does AI research put its effort?

**How often do explicitly alignment-worded language-model papers study model weights versus external supervision or runtime harnesses?** Across the same 60 full papers, the sampling-weighted ratio is **1.56 with Jev** (95% interval 1.09–2.22) and **2.84 with Qwen** (1.99–4.07). Jev’s ratio ranges from **1.02 to 2.64** as its decision cutoff moves from 0.30 to 0.70. The evidence supports a weight tilt at the default settings. Its size is sensitive to how a paper qualifies.

The abstract rubric estimates **3.39** in this group and **0.64** among other language-model alignment papers. Full-paper results cover the explicitly worded group. Publication counts describe research attention over November 2021–October 2026.

## Hypotheses and results

| Hypothesis | Observation |
|---|---|
| Broader alignment produces at least two alignment-directed weight papers per external-supervision paper. | **Below the twofold threshold.** An estimated **1.36** alignment-directed weight papers per supervision paper (95% interval **0.98–1.90**). |
| Weight papers outnumber control or harness papers in general AI. | **Both reviewers find a weight tilt.** Rubric **3.29** (2.21–4.91). Jev **4.60** (3.08–6.88). |
| Explicitly alignment-framed papers favor weights more strongly than general AI. | **Reviewer-dependent.** The ratio in explicit alignment divided by the general-AI ratio is **1.11** (0.53–2.37) with the rubric and **0.38** (0.21–0.68) with Jev. A value above 1 supports the hypothesis. |
| Feedback and dynamics form recognizable topics outside the alignment shortlist. | **Partial support.** The shortlist contains **0 of 235** papers in one optimization/control cluster. **10 of 15** audited there use feedback or dynamics. Many study physical systems. |
| Reallocating funding or labor toward harnesses would improve safety. | **Open.** Testing this requires a comparison of safety gains at equal cost and comparable task performance. |

The study protocol specifies the twofold threshold and the comparison with parity. Topic, framing and reviewer comparisons are exploratory. These hypothesis tests use abstract-level evidence. The paired full-paper audit checks the explicit language-model subset. Intervals measure sampling uncertainty. [Study protocol](protocol.md) · [Direct comparison data](results/frame_contrast.json)

## What measures research attention?

| Measure | Observation | Coverage |
|---|---|---|
| Publication mix | Weights only / external only / both / neither: **30.4 / 28.3 / 2.5 / 38.8%** in broader alignment; **51.8 / 13.8 / 2.8 / 31.6%** in general AI. | Sampling-weighted rubric estimates. “Neither” includes evaluations, theory and governance, along with papers whose abstracts lack a qualifying intervention. |
| Financial commitments | **$581.69B** in global corporate AI investment in 2025. | Includes transactions such as acquisitions. No division by alignment topic or intervention. |
| Production practice | **68%** of surveyed deployed-agent practitioners reported at most ten steps before human intervention. | A study of 86 practitioners. Measures deployed design choices. |
| Research time | Engineer-hours by topic are unknown. | Job listings, paper counts and grants cannot recover time allocation on their own. |

[Publication estimates](results/attention.json) · [Indicator populations, units and sources](data/attention_indicators.csv)

## What changes when reviewers read the whole paper?

| Same 60 papers | Abstracts, W / external | Full papers, W / external | Weighted ratio, abstract → full paper |
|---|---:|---:|---:|
| Jev 1.14.0, 67 questions | 33 / 16 | 39 / 27 | 2.21 → **1.56** |
| Qwen3-30B-A3B-Instruct-2507, three headline questions | 53 / 24 | 57 / 21 | 2.23 → **2.84** |

All 60 inputs include text from every PDF page, spanning 1,431 pages. Twelve Jev requests used extended context. One paper was withdrawn in October 2026 and its original posted version is included to preserve the frozen sample. Omitting it gives full-paper ratios of 1.56 (Jev) and 2.79 (Qwen). Each model received the same text and headline definitions, with previous labels hidden. Different prompting and scoring rules make the older abstract rubric and Jev checks separate measurements.

Jev flags 11 full papers for a direct weight-versus-external experiment, three for a resource-matched comparison of any kind, and one for both. The two flags can refer to different experiments in the same paper. These counts identify papers for evaluating returns to different approaches. [Full-paper comparison](attention-overview.html#full-paper-check) · [Paper scores and sources](results/fulltext_measures.csv) · [Questions, methods and reproduction](MASTER.md#join-the-full-paper-audit)

## Which language-model papers count?

The default view selects papers substantively about large language models or language Transformers from all 26,697 paper IDs. It includes systems built around named models such as GPT and language-based multimodal systems. A transformer for images or time series alone falls outside the definition. Each paper retains its original sample membership, model-scope score and separate intervention labels.

In the broader alignment audit, **172 of 215** papers qualify. Of those, 60 use explicit alignment wording and 112 use other wording. The rubric counts **33 weight papers and 11 external papers** in the first group, and **31 and 46** in the second. Both numerator and denominator credit hybrids. Sampling-weighted ratios are **3.39 (1.78–6.46)** and **0.64 (0.43–0.96)**. Combining the two groups gives **1.12 (0.83–1.51)**. The inclusion rule describes how authors frame a paper and makes no claim about the authors’ personal views. [Language-model comparisons](results/language_comparison.json) · [Language-model catalog](results/language_model_papers.csv.gz) · [Model-scope definitions](MASTER.md#select-language-model-publications)

## Which papers count?

| Population | How a paper enters | Audited papers | Weights vs control alone | Weights vs harness alone | Weights vs either, 95% sampling interval |
|---|---|---:|---:|---:|---:|
| General AI | Any arXiv submission with primary category AI, machine learning, computational linguistics, computer vision, robotics, neural computing or statistical ML | 180 | 11.21 | 3.68 | **3.29 (2.21–4.91)** |
| Explicit alignment | A paper in the broader alignment audit also uses a specified phrase in its title or abstract, such as “preference alignment,” “aligning language models,” or aligning with human values | 72 | 8.00 | 4.40 | **3.67 (1.93–6.96)** |
| Broader alignment | The review found a substantive alignment problem within the arXiv and ACL search, including preferences, behavior, oversight and enforcement, regardless of the author’s wording | 215 | 1.52 | 1.29 | **1.07 (0.81–1.41)** |

The 72 explicit papers are part of the 215. A DPO paper changes the generator’s weights. A monitor that blocks a proposed action supplies **external control**. A tool, memory or retrieval system that changes how an agent executes a task counts as a **harness**. A monitor can itself be trained. Its role relative to the acting model determines the code. A paper can receive both weight and external credit, and a paper about governance or evaluation can receive neither. Within the external comparator the same paper counts once. [Criteria and baseline](BASELINE.md) · [Exact wording rule](rules.py) · [Paper-level decisions](data/attention_review.csv)

The **7.20** estimate compares alignment-directed weight changes with external supervision alone, using 33 observed weight papers and five external papers. Under the general-AI weight definition the explicit ratio is 8.00 against external supervision and 3.67 against supervision or scaffolds. Across the broader audit the corresponding sequence is 1.36, 1.52 and 1.07. Eight papers gained a weight code under the common definition, including work that trains an adversarial generator. Each rubric decision is available at paper level. [Alignment-directed comparison](REPORT.md) · [Reasons for revisions](data/attention_review.csv)

The raw counts for the combined comparison were **100 weight / 35 external** in general AI, **37 / 11** in explicit alignment, and **73 / 66** in broader alignment. The reported ratios use the probabilities with which papers entered their respective audits. In general AI the estimated shares of all papers were 54.6% weights, 4.9% controls, 14.8% harnesses and 16.6% either external mechanism. The AI sample includes applications such as image segmentation where a runtime harness may have little bearing on the research question. [Estimates and intervals](results/attention.json) · [Baseline shares](results/general_ai_baseline.json)

## Does the contrast survive changes in time, subject and authors?

| Weights per paper with either external mechanism | Nov 2021–Dec 2024 | Jan 2025–Oct 2026 |
|---|---:|---:|
| General AI | 5.75 | 2.26 |
| Explicit alignment | 9.26 | 2.44 |
| Broader alignment | 2.70 | 0.75 |

The later period has more external work relative to weights in each sample. Subject mix also matters. Within primary computational linguistics in the later period, the broad-alignment estimate was **1.24** (0.38–3.98, 25 reviewed) and the general estimate **1.15** (0.33–4.05, 20 reviewed). A second check paired 49 audited arXiv computational-linguistics papers with distinct papers in the same year and primary category, selecting the closest available titles by embedding from up to 300 random candidates per year. The pairs gave 24 weight / 10 external on the alignment side and 19 / 15 on the comparison side. The estimated ratio of ratios was **1.89 (paired bootstrap interval 0.82–5.14)**. Titles do not guarantee matching tasks, and the interval admits effects in both directions. We cannot isolate an excess preference for weights attributable to alignment researchers themselves. [Inspect the matched pairs](data/matched_cscl.csv) · [Calculations](results/semantic_checks.json)

The explicit-vocabulary estimate is insensitive to removal of any one observed coauthor group. The 38 papers behind it fell into **35 groups** when papers on the 7,735-paper shortlist were connected through two or more shared author names. The recalculated ratio ranged from **6.73 to 9.52**. The largest group supplied two of the 38. This argues against one prolific team driving the finding. Small group counts, ambiguous author names and missing affiliations preclude a lab ranking or strong conclusions about intellectual networks. [Coauthor assignments](results/author_clusters.csv) · [Sensitivity to group definitions](results/author_balance.json)

## Where do feedback and dynamical systems appear?

A search-free draw from general AI and from systems/control/optimization produced two recognizable neighborhoods. One linked robotics and reinforcement learning to feedback control. Another linked optimization to dynamics, stability and control. Neither produced a single identifiable “cybernetics school” covering the whole dataset. Here, feedback means that an observation changes a subsequent action. Dynamics includes substantive reasoning about state evolution or trajectories. Static gates, generic mentions of feedback and state-space model names need separate examination.

| Semantic neighborhood | General AI draw | Systems/control/optimization draw | Reviewed examples with feedback or dynamics |
|---|---:|---:|---:|
| Language models | 192 | 2 | 3 / 15 |
| Robots, agents and reinforcement learning | 132 | 49 | **12 / 15** |
| Energy and industrial infrastructure | 6 | 110 | 6 / 15 |
| General learning, estimation and privacy | 248 | 24 | 5 / 15 |
| Mathematical optimization, dynamics and control | 21 | 214 | **10 / 15** |
| Computer vision | 201 | 1 | 1 / 15 |

The categories supplied 800 and 400 papers, respectively, chosen by a fixed hash without a keyword condition. The latter 400 were drawn from 38,353 submissions in systems and control or optimization (cs.SY, eess.SY, math.OC). The algorithm grouped all 1,200 before we interpreted or named the clusters. Only **five of 235** mathematical optimization/control papers had the same identifier in the alignment candidate set, and **zero** reached its alignment shortlist. Among the 181 robotics/RL papers, nine reached the candidates and zero reached the shortlist. Those counts demonstrate a difference in coverage. Many of the papers concern mechanical or industrial control and would reasonably fall outside a study of AI alignment. [All papers and assignments](results/control_map.csv) · [Central examples](results/control_map.json) · [Frozen audit](data/control_validation.csv)

For a concrete example, *Tuning of passivity-based controllers for mechanical systems* concerns stability under feedback. In AI, *Voyager* builds a skill library and uses environment feedback to improve an agent’s actions. Both belong in a search for systems that learn from consequences. Only the latter clearly exemplifies an AI execution scaffold. Preserving this distinction prevents a wider vocabulary from counting all control engineering as a solution to AI alignment. [Passivity-based control](https://arxiv.org/abs/2202.10161) · [Voyager](https://arxiv.org/abs/2305.16291)

## How do topics and coauthors relate?

The shortlist contains **7,735** papers. Topic assignments come from K-means on contextual embeddings (E5) of titles and abstracts. Names summarize the papers nearest each center. No Jev intervention labels, coauthor names or publication years enter the clustering. A separate **800-paper general-AI map** uses a hash draw across seven arXiv primary categories, with no topical keywords. A third map adds **400** systems/control/optimization papers to that sample. Its sample proportions reflect that design. Topic labels are descriptive; the general-AI solution has silhouette 0.049 and alternate-seed agreement 0.918. The corpus excludes non-arXiv work from these two category-based samples. The maps overlap. Their totals cannot be added.

| General-AI topic | Papers out of 800 |
|---|---:|
| Learning methods and optimization | 252 |
| Computer vision and generation | 205 |
| Robotics and reinforcement learning | 156 |
| Language models and applications | 187 |

The interactive heatmap covers all **7,735 shortlist papers**. Among 534 direct preference optimization papers, Jev flags 514 for weights and 74 for control or harnesses. Among 815 agent-security papers, it flags 159 and 477 respectively. A paper can qualify for both. Each paper has ten Jev scores, a nearest neighbor and distances in embedding space. The master also includes every candidate and comparison paper. [Paper-level data](results/paper_master.csv.gz) · [Measures and validation](MASTER.md)

For a separate audit, a hash draw selected **32 papers per topic**, independent of the mechanism scores. Jev rated each abstract on five dimensions. At cutoff 0.50, the direct preference optimization group has **31/32** weight positives and **3/32** control-or-harness positives. The agent-security group has **8/32** and **21/32** respectively. Feedback or dynamics can refer to model training, physical systems or runtime intervention. Its interpretation requires reading the paper.

Across the eight groups, random label permutations give Holm-adjusted *p* = **0.0003** for weights, **0.0003** for external mechanisms and **0.0004** for feedback/dynamics at 0.50. The test uses 9,999 permutations of the joint votes across eight equally sized groups and asks whether measured rates vary by topic. Both the topic encoder and Jev read the same abstracts. These are associations between text-based measurements. The 256 papers come from a discovery shortlist with model-selected entries, so these counts cannot estimate field-wide prevalence. Threshold sensitivity and per-paper scores are available. [Counts by topic and threshold](results/cluster_audit.json) · [256 paper-level judgments](results/jev_cluster_audit.jsonl)

Of 8,749 shortlist paper pairs sharing two or more normalized author names, **2,987 (34.1%)** share a semantic topic. Shuffling labels among papers in the same publication year gives **14.9%** on average (middle 95% of 1,999 permutations, **14.0–15.8%**). This preserves the coauthor graph and each year's topic counts. Specialization, venue, institutions and repeated research programs are all possible explanations. The test establishes no causal role for any team. [Coauthor permutation test](results/coauthor_topic_test.json)

In the interactive map, t-SNE projects the embeddings to two dimensions after reducing them to 50 principal components. The four nearest papers shown for a selection are ranked by cosine similarity in the full embedding space, before projection. Topic separation is weak, and boundaries depend on corpus selection and clustering resolution. [Alignment cluster diagnostics](results/semantic_map.json) · [General AI diagnostics](results/general_topics.json) · [Systems comparison diagnostics](results/control_map.json)

## How much do the words hide?

Of seven pre-2025 alignment papers judged to study a harness, **zero** used the literal “harness” or “harnesses” in the title or abstract. Three of 46 published from 2025 through October 2026 used either term. The literal word found zero of the 31 general-AI harness papers. Even the expanded word list, including “scaffolding,” “orchestration,” and “middleware,” found zero of seven through 2024 and eight of 46 in 2025–26. Across the entire seven-category catalog, scaffold-related wording rose from 22 of 43,680 papers in 2022 (0.05%) to 770 of 105,325 through October 2026 (0.73%). These are word counts with multiple possible meanings. They cannot tell whether a community renamed the same idea. [Annual vocabulary counts and denominators](results/vocabulary_by_year.csv)

A contextual text encoder, E5, learned to rank likely harness papers from the coded examples in one sample. Tested on the other, weighted average precision was **0.475** for general AI → alignment and **0.329** for alignment → general AI. The expanded keyword flag scored 0.307 and 0.148, respectively. Baseline positive shares were 0.255 and 0.148. A shared paper was excluded from training. Continuous scores can rank papers within the ties that a binary keyword flag creates. The comparison supports semantic retrieval as a screening aid. It leaves ample uncertainty for individual labels. [Cross-sample results](results/semantic_checks.json)

On the separate 90-paper audit, 37 abstracts showed substantive feedback or dynamics under the review criteria. A broad control-theory word list missed 25 of those 37 and flagged two negatives. E5 similarity to a functional description of feedback achieved weighted average precision 0.775, a dynamics description 0.728, and the binary keyword flag 0.584. The 90 papers were drawn equally across clusters, so the metric weights each reviewed paper by the size of its cluster. [Queries and lexical comparator](cybernetics_map.py) · [Raw audit outcomes](data/control_validation.csv)

The large exploratory map embeds 7,914 unique documents (7,735 shortlisted and 180 general-AI audit papers, with one overlap). At the selected eight-cluster resolution it separates preference optimization, reward learning, synthetic feedback, safety fine-tuning, multimodal work, jailbreaks, agent security and governance. The shortlist dominates this map by construction. The highest average silhouette was just 0.055 (alternate-seed adjusted Rand index 0.974). The independently drawn 1,200-paper map had silhouette 0.048 and seed agreement 0.646. The dense overlap makes sharp boundaries or a unique count of schools untenable. [Large map](results/semantic_map.json) · [Independent map](results/control_map.json)

## What changes when Jev reads the same abstracts?

TypeSafe’s Jev (returned version **jev-1.14.0**) scored 395 abstracts in the publication comparisons and 90 abstracts in the control audit. Each request supplied a public title and abstract with five independent questions covering weight changes, external supervision, runtime scaffolding, feedback and dynamics. It saw no prior labels, cluster assignments or sampling strata. The model’s scores and the exact questions are frozen. The table uses the same sampling design as the rubric review. Across columns only the mechanism votes change.

| Weights per paper on control or harness | Rubric-based AI review | Jev at 0.50, 95% interval | Jev at 0.30 | Jev at 0.70 |
|---|---:|---:|---:|---:|
| General AI | 3.29 | **4.60 (3.08–6.88)** | 2.85 | 7.90 |
| Explicit alignment | 3.67 | **1.74 (1.14–2.65)** | 1.18 | 2.75 |
| Broader alignment | 1.07 | **0.89 (0.72–1.10)** | 0.77 | 1.11 |

A score of at least 0.50 gives a paper a vote for that mechanism. An external vote requires either a supervision or a scaffolding score above the chosen cutoff, including equality. The 0.30 and 0.70 columns show sensitivity. At 0.30 the explicit-alignment interval includes parity (0.92–1.51). Thresholds were not calibrated against independent human labels. The two reviewers even disagree on whether general AI or explicit alignment has the higher point estimate. A claim that the “alignment crowd” is unusually weight-focused relative to general AI would go beyond these data.

The discrepancy has a paper-level explanation. Of the 72 explicitly worded papers, Jev called 18 papers supervisory that the rubric reviewer did not, and missed one of the five rubric supervision positives. On the 215 broader papers it also missed 26 of 53 reviewed harnesses at the 0.50 cutoff. For example, a study of regularized best-of-N sampling builds a runtime procedure to select outputs and separately trains on its selected data. The rubric assigned both weights and harness. Jev assigned a harness score of 0.05 and a weights score of 0.26. Conversely, it gave 0.92 on supervision to a paper that verifies candidate scene trajectories for video generation. The rubric counted the verification pipeline as a harness and reserved supervision for stronger control over the acting system. These are plausible semantic disagreements about where a component intervenes. [Best-of-N study](https://arxiv.org/abs/2404.01054) · [Sketch-guided verification](https://arxiv.org/abs/2511.17450) · [All 395 Jev score records](results/jev_mechanisms.jsonl)

For feedback or dynamics in the 90-paper sample, Jev achieved **0.894 weighted average precision**, ahead of the E5 feedback query (0.775) and keyword flag (0.584). Taking the larger of the two Jev scores at 0.50 recovered 33 of 37 rubric positives and flagged 11 of the other 53. This supports the use of functional descriptions to retrieve relevant research. Both the initial labels and Jev rely on abstract-level AI judgments, so their agreement cannot certify the true prevalence. [Frozen 90-paper Jev scores](results/jev_checks.jsonl) · [All thresholds and disagreement counts](results/jev_validation.json) · [Exact questions](jev_check.py)

## What do people expect, want and actually do?

| Whose attention? | Observation | What it measures |
|---|---|---|
| US public and AI experts | In Pew’s 2024 fieldwork, 64% of adults and 39% of AI experts expected fewer US jobs over 20 years. 55% and 57%, respectively, wanted more control over AI in their own lives. | Forecasts diverge while preferences for personal control are similar. Neither question asks respondents to choose a technical intervention. |
| International publics | Across 18 high-income and 18 middle-income countries surveyed in 2026, median shares expecting job loss were 55% and 36%. Shares unsure were 22% and 34%. | Country medians reveal geographic variation. They weight countries equally. |
| Publishing AI researchers | A 2023 survey of 2,778 authors put the aggregate 50% date for machines outperforming humans at every task at 2047, and for all occupations being fully automatable at 2116. About 70% wanted more priority for research to reduce AI risk. | Researchers distinguished technical capabilities and job automation. The forecasts are conditional on continued scientific progress and sensitive to wording. |
| People deploying agents | In a study of 86 practitioners with deployed systems across 26 domains and 20 case studies, 70% relied on off-the-shelf models with prompting, 68% allowed at most ten steps before human intervention, and 74% primarily used human evaluation. | Bounded autonomy and human review already consume operational attention. This is a selected deployment sample. A prompted model alone does not qualify as a harness in the paper audit. |
| Users of AI products | Anthropic classified 52% of Claude.ai use as augmentation and 45% as automation in November 2025. About 70% of consumer ChatGPT messages were unrelated to work in July 2025. | Consumer use, enterprise APIs and job forecasts have different populations and time horizons. |
| Employers | US postings listing the “Agentic AI” skill went from 151 in 2024 to 16,541 in 2025. | A hiring signal sensitive to changes in vocabulary. Postings omit internal transfers, effort shares and hires per advert. |
| Investors and grantmakers | Global corporate AI investment was $581.69B in 2025. In 2026 one grantmaker recommended more than $70M over two years for Redwood’s mixed agenda including control, recommended $68M over three years for Epoch AI, and approved $160M for rigorous alignment at Resolution. | Corporate transactions, grant recommendations and approved support measure different flows. The disclosures provide no comparable W/H line items. |
| Incident reporters | The AI Index reports 233 documented incidents in 2024 and 362 in 2025. | Coverage and use can grow. A rate per deployment or user-hour requires an exposure denominator. |

Sources and units for all 32 observations are in the [evidence ledger](data/attention_indicators.csv). [Pew US](https://www.pewresearch.org/internet/2025/04/03/how-the-us-public-and-ai-experts-view-artificial-intelligence/) · [Pew international](https://www.pewresearch.org/global/2026/09/17/concerns-about-ai-are-especially-widespread-in-high-income-countries/) · [AI researcher survey](https://mlanthology.org/jair/2025/grace2025jair-thousands/) · [Deployed agents study](https://proceedings.mlr.press/v306/pan26a.html) · [AI Index economy](https://hai.stanford.edu/ai-index/2026-ai-index-report/economy) · [Grant disclosure](https://coefficientgiving.org/research/were-urgently-scaling-our-work-on-ai-and-biosecurity/)

## What do we know about returns to research spending?

**There is evidence of a publication imbalance and of a discovery problem.** Weight papers are easier to find in explicitly alignment-framed literature. Work on runtime behavior turns up under different names, in adjacent disciplines, and in deployment practice. The deployment survey records operational choices about human oversight. Its denominator is deployed systems. Equally, a single base-model training project can support many downstream deployments. A target of one publication on each side has no inherent economic or safety justification.

**The missing comparison is the return on the next dollar or engineer-month.** A controlled AI study has already shown that supervision and editing can improve safety with a fixed strong model and a limited trusted oversight budget. Its result establishes a benefit in the studied setting. Estimating the best allocation requires varying investment on both sides. On the same held-out tasks, compare a baseline, a model update, an external intervention, and their combination. Measure costly failures, legitimate tasks completed, human review minutes, latency, compute and maintenance. Report uncertainty per deployment and the incremental reduction in harm per equal budget at comparable utility. Include the combination because improvements can complement one another. [AI control experiment](https://proceedings.mlr.press/v235/greenblatt24a.html)

A study of **human priorities** also needs to ask whose preferences count. The Pew item about wanting control could mean being able to refuse a deployment, correct a decision, appeal to a person, or choose when AI is used. Treating all such answers as support for harness funding would erase the distinction the survey measures. The surveys measure desired agency. Translating that preference into a research budget requires separate evidence.

## Coverage and replication

The alignment search covers 1,330,760 dated arXiv and ACL metadata records and retained 25,329 distinct candidates. One AI reviewer examined a stratified random draw of 360 and classified 215 as core. The general-AI baseline sampled 180 from 375,724 submissions, with 80 selected from a control-cue stratum and 100 from the remainder. The 1,200-paper map was drawn separately without vocabulary filters. A hash-selected 15 papers per cluster received a mechanism-level review. The 49 title-matched comparisons form a separate sensitivity exercise. These samples overlap and answer different questions. Do not sum them as independent studies.

Intervals use stratum sampling probabilities, within-paper covariance and finite-population variance, conditional on the frozen labels. Missing venues, private work, title/abstract omissions, author identification and classification disagreement can all affect the estimates beyond those intervals. The external venue check located 56 of 71 safety-titled Learning for Dynamics and Control papers in the source catalog, and only 42 reached the candidates. The publication window ends October 31, 2026. The earliest and latest calendar years are incomplete. Recruitment, time windows, and units for non-publication evidence differ across sources. The indicators are a sourced selection and furnish no search-complete inventory of global funding or public opinion.

[Reproduction commands and source catalog](README.md) · [Study protocol](protocol.md) · [Full baseline audit](data/baseline_review.csv) · [Searchable paper catalog](alignment-overview.html)
