# Alignment research, 2021–26

[Open the offline HTML report and searchable paper explorer](alignment-overview.html), [read the one-page report](REPORT.md) or [browse the alignment dataset](results/alignment_papers.csv). The study compares changes to the acting model’s parameters with external supervision and enforcement. Soft inference steering, task-specific safety engineering, and studies without a proposed intervention are identifiable separately.

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
