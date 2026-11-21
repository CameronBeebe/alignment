# Alignment research, 2021–26

**November 2026 update.** [Open the AI research attention overview](attention-overview.html) or [read the report on GitHub](ATTENTION.md). It adds a general-AI baseline, coauthor and semantic clusters, Jev validation, and evidence from deployed systems, surveys, hiring and funding.

[Open the offline HTML report and searchable paper explorer](alignment-overview.html), [read the one-page report](REPORT.md) or [browse the alignment dataset](results/alignment_papers.csv). The study compares changes to the acting model’s parameters with external supervision and enforcement. Soft inference steering, task-specific safety engineering, and studies without a proposed intervention are identifiable separately.

[Open the language-model subset](attention-overview.html#language-models). The first comparison covers LLMs, GPT-family research and language Transformers. Model-scope controls in the topic explorer and paper map switch between language models and all model families. [Subset definitions and checks](MASTER.md#select-language-model-publications)

[Compare publication mix, topic trends, overlapping labels, reviewers, coauthors and surveys in the visual report](attention-overview.html#data-views). The paper-profile explorer supports three Jev cutoffs and shows counts and percentages within each selected sample.

[Download the master dataset](results/paper_master.csv.gz) · [Column definitions, validation and reproduction](MASTER.md). The table joins ten Jev contribution and relevance ratings, a separate language-model focus score, semantic distances, topic assignments, and available review and coauthor data on each paper ID.

## Use the frozen study

Run these commands from this directory with Python 3.12. The CSV tables open directly. The candidate archive ships in two binary parts. Analysis restores it automatically and verifies its SHA-256 against the original review design. To restore it separately with the Python standard library, run `python snapshot.py`. Installing dependencies once requires internet access. Subsequent analyses work offline.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python analyze.py stats    # recompute audited estimates from the shipped tables
python build_overview.py   # render the HTML from existing results
python analyze.py          # rebuild paper tags, topics, shortlist and statistics
```

| File | What it contains |
|---|---|
| [alignment_papers.csv](results/alignment_papers.csv) | Practical discovery set. Each row has an ID, title, authors, URL, inclusion status, relevance score, provisional mechanism, topic, search channels, facets and mentioned metrics. Reviewed records also have substantive mechanism codes. |
| [reviewed_alignment.csv](results/reviewed_alignment.csv) | The 215 individually reviewed core papers. |
| [reviewed_papers.csv](results/reviewed_papers.csv) | The entire 360-paper probability sample, including exclusions and adjacent work. |
| [papers.csv](results/papers.csv) | All 25,329 candidates, with lexical evidence and topic membership. These rows include background mentions and false positives. |
| Candidate archive [part 1](data/candidates.jsonl.gz.part1) and [part 2](data/candidates.jsonl.gz.part2) | Frozen titles, abstracts, authors, dates, identifiers, original source variants, venues/categories and retrieval paths. Join tables on `paper_id`. |
| [search_manifest.json](data/search_manifest.json) | Input fingerprints, dates, flow counts, held-out sentinel checks, and the adaptive search log. |
| [topics.json](results/topics.json) | Cluster sizes, terms, representative paper IDs and silhouette scores. |
| [inference.json](results/inference.json) | Design-weighted totals, intervals, threshold tests and sensitivity analyses. |
| [Reading guide](data/reading_guide.csv) | Examples of weights, soft inference steering, external control, harness adaptation and specification. |
| [L4DC venue check](results/venue_index_check.csv) | Independent venue register with exact-title matches in the source index and retrieved papers. |

## Search or extend the dataset

Only run acquisition to refresh raw metadata or to build the full local search index for the first time. The official sources are the [Cornell arXiv metadata mirror](https://www.kaggle.com/datasets/Cornell-University/arxiv) and the [ACL Anthology abstract-inclusive bulk export](https://aclanthology.org/faq/bib/). The released study used the versions retrieved on 20 November 2026 in Denver. Source digests in the manifest refer to the **uncompressed** files supplied for this run. Latest-source refreshes can incorporate new records and revisions.

```bash
python catalog.py arxiv --refresh
python catalog.py acl --refresh
python search.py --out data/new_search
python analyze.py --data data/new_search --out results/new_search
```

Already have the archives or the unpacked files? Use `python catalog.py arxiv --input PATH` and `python catalog.py acl --input PATH`. The catalog supports ZIP, gzip and plain text. Indexing an unchanged input is a no-op. The full SQLite index stays in `cache/catalog.sqlite`. Change retrieval rules in `rules.py` and rerun only `search.py` against that index. For classification changes on the same 25,329 papers, rerun only `analyze.py`. Use a new output directory for an expanded search. The audited snapshot is protected against replacement by a changed search.

The search takes a mechanism-neutral path through human goals, safety, oversight and misalignment, plus targeted paths for preference training, formal control, runtime enforcement, schemas, tool permissions and inference-time steering. It searches titles and abstracts across all arXiv categories and eligible ACL entries. A pilot on ACL informed expansion into neighboring terminology. A bounded search agent then uses seed papers to mine repeated two- and three-word phrases, queries the local full-text index, inspects ranked neighbors, and feeds fresh records into a second round. Counts and next seeds are logged. The 24 accepted probes added 248 source records. Some second-round terms drifted off topic. Dropping feedback-only candidates leaves the audited primary ratio unchanged. The six held-out sentinel papers were recovered. Sentinel recovery is a spot check.

For a fresh audit, run `python analyze.py draw --data data/new_search --budget 360`. Review the drawn papers under [the protocol](protocol.md) and save the review using the schema of [review.csv](data/review.csv). The seed, sampling probabilities and snapshot fingerprint are preserved. Old labels refer to the frozen draw. For an optional venue refresh use `python venue_refresh.py --out data/new_search/l4dc_catalog.json`. On a machine with the full catalog, `python coverage.py` recomputes the independent index-coverage check.

## Analysis and interpretation

**Mechanism.** W means the acting policy’s parameters change. E means a substantive surrounding control, such as authorization, filtering, supervision or monitoring. I means soft inference steering, such as activation editing or preference-guided decoding. Multiple labels are allowed. `none` covers core work such as measurement, governance or specification without a qualifying intervention. A trained detector supervising a frozen actor can qualify as E. Generic task accuracy and unrelated representation alignment are outside scope.

**Sampling.** The 360-paper draw uses 20 strata defined by provisional method, generative-model vocabulary, and period (before 2025 or later). Within each stratum, papers are randomly selected without replacement. Each reviewed paper represents its stratum size divided by its sample size. Totals use these weights. Ratios divide the two totals, with both sides credited for a hybrid. Log-ratio uncertainty and paired linear contrasts use within-stratum variances, finite-population corrections and Satterthwaite degrees of freedom. The primary two-sided tests use equality and a prespecified twofold imbalance. Subsets and time comparisons are exploratory. The single AI reviewer saw paper titles and abstract evidence, with ambiguous cases reopened, and did not see provisional groups on the review sheet. The reviewer helped design the study. There was no independent second review. [Protocol](protocol.md) · [Audit design](data/audit_design.json)

**Retrieval versus relevance.** The initial screen yielded 205,581 full-text-index matches and 27,781 lexical candidates. Feedback brought this to 28,029 source records. Normalized-title and DOI deduplication yielded 25,329 works. Substantially retitled papers with no common DOI can remain. The high-score discovery set contains all reviewed core papers plus unreviewed papers with a logistic-regression relevance score of at least .80. In five-fold held-out review data, 96 of 104 flagged papers were core. Design-weighted precision was 92% and recall was 46% **within the candidate frame**. These are internal estimates against the same reviewer’s labels. The high-score set favors precision. The statistical comparison instead uses the probability sample of the whole frame. [Validation](results/relevance_validation.json)

**Topics and metrics.** TF–IDF words and bigrams, 48-dimensional latent semantic analysis, and k-means organize the full candidate set. Of 8, 12 and 16 clusters, 16 had the best sampled cosine silhouette (.178). Topics overlap. Examples include preference optimization, reward learning, prompt injection, agent systems, barrier functions, robotics, interpretability, and governance. Metric tags identify phrases such as win rate, constraint violation, refusal rate and latency. They record mentions and do not pool scores across incompatible tasks. [Topic descriptions](results/topics.json) · [Lexical rule validation](results/rule_validation.json)

**Coverage.** arXiv includes preprints and revised abstracts. ACL adds published NLP material. The L4DC check covers all five conference volumes in 2022–26 and screens their titles independently for safety terms. Exact-title matches miss renamed preprints. Conference-specific probes and the shortlist model cannot measure field-wide recall. Corporate deployment work, practitioner material, work published only in other indexes, and scholarship outside the search vocabulary can be absent. A separate review of three frontier labs also identified sparse publication on safety by design, using a different scope and taxonomy. [L4DC proceedings](https://proceedings.mlr.press/) · [Delaney, Guest and Williams](https://arxiv.org/abs/2409.07878)

## Attribution

Titles, authors, abstracts and identifiers come from the source records linked per paper. The Cornell metadata mirror describes its metadata as CC0. In-window ACL material is attributed to the original authors and ACL Anthology under its published CC BY 4.0 terms. The L4DC table attributes papers to their authors and PMLR volumes. Derived labels and estimates were produced for this study. [Cornell metadata terms](https://www.kaggle.com/datasets/Cornell-University/arxiv) · [ACL terms](https://aclanthology.org/faq/bib/)

## Does a recurring team drive the explicit-vocabulary result?

Among the 38 reviewed papers behind the 7.20 ratio, one pair of papers shared a normalized author name, and zero pairs shared two. UltraFeedback and LLaDA 1.5 both list Yankai Lin. The reviewed papers may still connect through other publications. To check, we linked papers across the entire 7,735-paper shortlist whenever they shared at least two author names, weighted each link by the number of shared names, and grouped papers using Louvain community detection. Isolated papers each form their own group.

The 38 reviewed papers fell in 35 groups. Dropping each represented group in turn and recomputing the original sampling-weighted ratio gave 6.73–9.52. This range describes sensitivity to removing a group. Sampling uncertainty is reported separately in the [study report](REPORT.md). Using a different clustering seed also gave 35 groups. Requiring three shared names gave 37 groups. With at most two papers contributing to the named comparison per group in the primary analysis, the audit gives little information on any individual group's intervention mix.

This exploratory analysis uses title-and-abstract review decisions for intervention counts. Unreviewed papers contribute only byline connections. Name matching uses normalized full-name strings from ACL and arXiv metadata. Homonyms, initials, spelling variants, missed publications and collaborations outside the shortlist affect coverage. Groups can span institutions or split a single lab. The output measures concentration in published papers. Estimating spending, staffing, unpublished deployment work and the return on additional investment requires other data.

Run `python -m pip install networkx==3.4.2` and then `python author_network.py` from this directory. [Paper assignments and bylines](results/author_clusters.csv) · [Results and sensitivity checks](results/author_balance.json)

## General AI publication baseline

A separate 180-paper probability sample from seven arXiv categories estimates how often papers study model weights, external controls and execution frameworks across general AI research. [Baseline report, definitions and review decisions](BASELINE.md)

## Reproduce the attention study

Install the pinned packages in `requirements-semantic.txt` in the study environment. Recompute the estimates from the shipped data with the commands below. The pinned E5 model downloads on its first run. To use a cached model offline, set `HF_HUB_OFFLINE=1`. Use a fresh vector-cache filename when changing the input texts or model.

```bash
python -m pip install -r requirements-semantic.txt
python baseline.py
python author_network.py
python semantic_map.py --vectors /tmp/attention-e5.npz
python cybernetics_map.py
python attention.py
python semantic_checks.py /tmp/attention-e5.npz
python jev_results.py
python compare_frames.py
python cluster_audit.py
python cluster_geometry.py --vectors /tmp/attention-e5.npz
python general_topics.py
python build_attention.py
```

The Jev measurements are frozen. Reading or recomputing their statistics requires no API access. To request additional scores from TypeSafe deliberately, set `TYPESAFE_API_KEY` locally and run `python jev_check.py --sample control --limit 90` or `python jev_check.py --sample mechanisms --limit 395`. Requests send public titles and abstracts only and may incur charges. A result hash identifies the submitted prompt and text. Specify a new `--output` to collect a fresh replicate separately. Model aliases may change. The raw records include the returned version.

To regenerate the draws from the original full SQLite metadata catalog, run `baseline.py --draw-from PATH`, `control_sample.py PATH`, `match_papers.py PATH` and `vocabulary.py PATH` with Python. The frozen samples preserve public metadata, matched IDs and review decisions. Recollecting the source catalog at a different date can change records.

The exploratory explicit-alignment versus general-AI contrast divides their weights-to-external ratios. It uses independent draw variances for the difference of the two log ratios, stratum weights and a Satterthwaite interval. This unadjusted comparison describes different publication mixes. [Contrast code](compare_frames.py) · [Estimates](results/frame_contrast.json)

The HTML embeds all three maps for offline use with a modern browser. A point can be selected by mouse or from the searchable paper list. The 800 independent general-AI papers are also part of the 1,200-paper systems comparison. The 7,735-paper discovery shortlist includes model-selected records. To reproduce the 256-paper stratified Jev collection, use `python jev_check.py --sample clusters --limit 256 --workers 4`. Rebuilding the page from shipped tables requires no paid calls.
