# Paper-level measurements

[Download the master CSV](results/paper_master.csv.gz) · [Explore the paper map](attention-overview.html#paper-map) · [Questions, counts and file checksum](results/master_manifest.json)

**26,697 paper IDs · 91 columns · 266,970 contribution and relevance ratings plus 26,697 language-model focus ratings.** Six IDs have title-only evidence. The 26,697 rows comprise all 25,329 search candidates and 1,368 additional comparison IDs. The alignment shortlist is a subset of the candidates. Publication volume measures one form of attention. Estimating hours, spending or safety gains requires other evidence.

## Select language-model publications

[Download the language-model catalog](results/language_model_papers.csv.gz) for a compact table of selected titles, IDs, cohort membership and intervention ratings. Join it to the master on `paper_id` for every column.

Use `jev_language_model_focus >= 0.50` for the report’s default language-model subset. Jev 1.14.0 assessed whether a language model plays a substantive role from the public title and abstract, without access to the mechanism votes or alignment-framing tags. The definition includes GPT-style systems, encoder models such as BERT, and multimodal systems with a material language-model component. It does not establish proprietary architecture or a parameter count. The ten original ratings retain their own request hash and token counts. The language-model scope request, usage, model and score are archived separately for every paper ID. [Exact question and term patterns](language_scope.py) · [Scope scores and provenance](results/language_model_scores.csv.gz)

`literal_llm` flags the acronym LLM or the phrase “large language model,” including plurals. `family_mention` flags one of a fixed set of model names, including GPT, ChatGPT, Llama, Claude, Gemini, DeepSeek, Qwen, BERT, RoBERTa, DeBERTa or T5. A family mention can be incidental. The default semantic subset, alternative cutoffs and both wording rules can be compared on the same frozen audit. The mechanism ratio divides the sampling-weighted total of weight papers by the weighted total of papers on supervision or harnesses. The explicit/other contrast uses disjoint parts of the same audit and estimates their covariance within strata. Intervals condition on the classifications. [Comparisons](results/language_comparison.json)

Forty abstracts received a separate AI scope review with Jev scores hidden. A fixed hash draw selected ten papers in each of four cells crossing the 800-paper general-AI draw or the alignment shortlist with presence or absence of literal LLM wording or a recognized family name. This deliberately balances easy-to-find and potentially missed cases. Unclear cases are reported separately. The check describes those selected papers. [Review decisions](data/language_scope_review.csv)

## Choose a population

| Exact entry in `cohorts` | Selection | Use |
|---|---|---|
| `candidate` | All retained alignment-search candidates | Describe the search results, including irrelevant matches. |
| `alignment_shortlist` | 7,735 reviewed core or high-scoring candidates | Explore likely relevant papers and topical neighborhoods. |
| `general_ai` | 800 papers from seven AI-related arXiv categories, drawn without a wording filter | Explore a general-AI comparison. |
| `control_and_optimization` | 400 papers from systems, control and optimization | Examine research in these categories. The 1,200-paper control map combines these papers with the 800 general-AI papers. |
| `general_ai_audit` | 180 papers from the separate stratified general-AI draw | Estimate frequencies using the frame's sampling weights. |
| `matched_comparison` | 49 comparisons matched to alignment papers | Check sensitivity within the matched design. |

Memberships overlap. Pooling all rows would give most of the weight to the alignment search. For estimates of the publication mix, use the sampling designs and reviewed denominators in the [report](ATTENTION.md). The master includes authors for attribution. A shared name can reflect a namesake. Records with the same normalized title have a count in `same_title_records`. Retitled versions can remain.

## Read the columns

| Fields | Meaning |
|---|---|
| `paper_id`, `title`, `authors`, `year`, `month`, `url`, `doi`, `sources`, `category`, `venue` | Bibliographic fields. Category is the primary arXiv category when available. Empty cells indicate missing information or a field outside the paper's frame. |
| `text_source`, `evidence_basis` | Frozen input source and whether an abstract was available. The text resolver gives precedence to candidates, then the general-AI audit, control sample and matched comparisons. |
| `lanes`, `auto_group`, `named`, `generative`, `*_hit`, `facets`, `metrics`, `cluster` | Original candidate retrieval channels, lexical flags, metric mentions and TF–IDF/LSA topic. `shortlist_selection` and `shortlist_core_score` describe separate relevance screening. |
| `jev_weights`, `jev_supervision`, `jev_scaffolding` | Evidence that the contribution changes the principal model, separately supervises or constrains outputs/actions, or coordinates a runtime system. Functional questions allow older terminology. |
| `jev_feedback`, `jev_dynamics` | Evidence for a feedback mechanism or a substantive analysis of state evolution. A high rating may describe a physical plant, optimization, or a deployed AI system. |
| `jev_alignment_relevance`, `jev_evaluation`, `jev_theory`, `jev_data_resources`, `jev_governance` | Independent questions about the paper's scope and contributions. A paper can qualify on several dimensions. |
| `jev_external_max`, `jev_feedback_dynamics_max` | Maximum of supervision/scaffolding and feedback/dynamics respectively. Thresholding a maximum counts the union of the two separate calls. |
| `jev_labels_at_050`, `jev_near_threshold_labels` | Pipe-separated dimensions scoring at least 0.50, or within 0.40–0.60 inclusive, respectively. `none` means no dimension meets that rule. |
| `jev_model`, `jev_request_sha256`, `jev_input_tokens`, `jev_output_tokens` | Returned model version, SHA-256 of the exact serialized request, and provider-reported usage for the single ten-question request. |
| `candidate_topic`, `topic_distance_l2`, `runner_up_topic`, `runner_up_distance_l2`, `topic_distance_margin` | Two closest candidate-fit centroids, Euclidean distances, and second distance minus first. A small margin places a paper near a topic boundary. |
| `nearest_paper_id`, `nearest_cosine`, `nearest_cosine_distance` | Exact nearest other ID across all 26,697 vectors, cosine similarity and one minus cosine. Ties use the first sorted ID. |
| `e5_cosine_feedback`, `e5_cosine_dynamics`, `e5_cosine_scaffold`, `e5_cosine_weight` | Cosine similarities to four functional descriptions. These serve as retrieval scores. |
| `shortlist_map_*`, `general_map_*`, `control_map_*` | Topic, distance to its centroid and two display coordinates within each existing map. Each map has its own fit and coordinate system. |
| `coauthor_group`, `coauthor_group_size` | Group and paper count in the shortlist coauthorship graph. Groups are linked through shared author names. |
| `alignment_review_*`, `alignment_harmonized_codes`, `baseline_review_codes`, `matched_review_codes`, `matched_core_id` | Published scope, mechanism decisions and matched partner where applicable. W = weight change, E = supervision/enforcement and H = harness in the harmonized coding. |
| `alignment_stratum`, `baseline_stratum` and their `N_h`, `n_h` columns | Sampling stratum, population size and draw size. Within the corresponding audit, the design weight is N_h / n_h. |
| `control_review_feedback`, `control_review_dynamics`, `role_review_*` | Separate AI rubric decisions on reviewed papers. Blank = unreviewed, zero = reviewed negative. |

## How the measurements were made

Jev 1.14.0 received only the title and available abstract with ten typed questions in one request. Higher scores indicate a stronger model judgment. A score of 0.80 has no established interpretation as an 80% empirical frequency here. Thresholds can be changed directly on the scores. The audit-based estimates in the overview use the separately frozen five-question instrument. The shortlist heatmap uses all ten-question records at the 0.50 cutoff. [Exact questions](results/master_manifest.json) · [Collector](master_jev.py)

The E5-small-v2 encoder uses normalized vectors from the first 160 tokens of the prefixed title and abstract. The candidate clustering fits only the 25,329 search candidates. It compares k = 6, 10, 16 and 24 by cosine silhouette on a fixed 2,000-paper subset. Each fit uses five initializations. A second seed checks assignment stability. Comparison papers receive their nearest candidate topic after fitting. The four functional prompts and all Jev ratings are excluded from the clustering inputs. Representative titles, cluster sizes, model revision and seed agreement are available in the [topic diagnostics](results/master_topics.json).

## Check the scores

At the 0.50 cutoff, Jev recovered 96% of rubric-coded weight papers and 52% of rubric-coded harness papers in broader alignment. In the general-AI audit, the corresponding recalls were 91% and 28%. These estimates use sampling weights. Supervision showed a different error pattern, with 48% precision in broader alignment. Both assessments used AI reviewers. Differences in label frequency can therefore reflect measurement as well as research attention.

Across the 733 IDs scored with both instruments, the expanded question set changed 5 harness calls, 6 weight calls and 11 supervision calls at the 0.50 threshold. Across all 25,329 candidates, six clusters had the highest sampled silhouette (0.044). Agreement between fits at two seeds was high (adjusted Rand index 0.999). The small silhouette indicates overlapping topics even though the partition was repeatable.

The [validation results](results/master_validation.json) report the reference-positive count, raw confusion matrix, precision, recall, specificity and average precision for each applicable sample. The alignment and general-AI audits use design weights. The feedback/dynamics audit accounts for its 15 papers per topic. The four other contribution roles use a 32-paper descriptive audit, split equally between general AI and candidates outside that sample. Its reviewer was an AI and saw the titles and abstracts with Jev scores hidden. Its small positive counts limit precision. [Review decisions and evidence notes](data/master_role_review.csv)

## Work with the table

Run from this directory. Read the exact memberships before constructing a subset.

```python
import pandas as pd
from master_records import master_records

papers = pd.read_csv("results/paper_master.csv.gz", keep_default_na=False)
groups = papers.cohorts.str.split("|", regex=False)
general = papers[groups.map(lambda memberships: "general_ai" in memberships)]
print(general.nlargest(10, "jev_scaffolding")[["title", "jev_scaffolding"]])

texts, _ = master_records()
paper_id = general.iloc[0].paper_id
title, abstract = texts[paper_id]
```

To rebuild from released scores, install the [dependencies](requirements-semantic.txt) and run the commands below. The E5 model requires an initial download or an existing local model cache. The Jev restore checks the released request hashes and requires no API calls. To collect scores on changed or new inputs, set `TYPESAFE_API_KEY` and supply a positive request budget through `--limit`.

```bash
python master_jev.py --cache /tmp/paper-jev.sqlite --limit 0
python master_semantics.py --vectors /tmp/paper-e5.npz --output /tmp/paper-features.csv
python language_scope.py --cache /tmp/language-jev.sqlite --limit 0 --freeze
python master_export.py --cache /tmp/paper-jev.sqlite --semantics /tmp/paper-features.csv
python language_comparison.py
python master_validation.py
python build_attention.py
```

## Join the full-paper audit

[Paper measurements](results/fulltext_measures.csv) join to the master on `paper_id`. This extension follows all 60 papers that are core in the stratified audit, contain an explicit alignment phrase and meet the default language-model cutoff. Membership stays fixed across reviewers and evidence sources. Every Jev measure has an abstract column and a full-paper column. Qwen supplies independent binary decisions on the three headline mechanisms. Full-paper scores apply only to the audited IDs.

Jev 1.14.0 answers 67 independent Noul questions per request, sharing the paper across questions. Qwen3-30B-A3B-Instruct-2507 receives the same three mechanism definitions with no previous labels. The full-paper input is the ordered PDF text of every page, including references and appendices. Figures contribute extractable text only. Published PDFs can include revisions after the metadata snapshot. PDF and extracted-text hashes identify the material used. The CSV includes versioned arXiv URLs when the version appears in the extracted text. The frozen sample includes arXiv:2608.01629, withdrawn on October 25, 2026. We retrieved v1 and report a leave-out sensitivity. Reading a paper in full can reveal mechanisms omitted from its abstract. It also gives a classifier more opportunities to mistake cited work or an experimental baseline for the paper’s own contribution.

The weighted ratios use the original stratified design. A paper qualifies as external if either the supervision or harness decision is positive. Hybrids count on both sides. Jev uses a 0.50 cutoff. The 67 exploratory questions yield descriptive counts for the paired papers. Changes and reviewer agreement do not measure accuracy. [Exact questions](fulltext_questions.py) · [Results and paired changes](results/fulltext_summary.json) · [Request, model and usage ledger](results/fulltext_requests.csv)

Rebuild the summary and HTML offline from the released measurements with `python fulltext_analysis.py` and `python build_attention.py`. To repeat collection with the dependencies in `requirements-semantic.txt` and the two provider keys set in the environment, run the following from this study directory.

```sh
python fulltext_sources.py /tmp/alignment-pdfs
python fulltext_rate.py /tmp/alignment-pdfs /tmp/alignment-ratings
python fulltext_analysis.py --export /tmp/alignment-pdfs /tmp/alignment-ratings
python build_attention.py
```

TypeSafe bills the shared paper input once per request, plus the question text. Outputs are free. The collector first uses the standard context and requests the extended context on a provider length rejection. The published ledger records which requests used it. [Jev model limits and pricing](https://docs.typesafe.ai/models) · [Parallel questions cookbook](https://docs.typesafe.ai/cookbooks/parallel_questions)
