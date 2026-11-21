# Which alignment-research databases already exist?

Seven public collections yielded **8,249 distinct matches** to the 26,697-ID master. They provide independent topic labels, human-curated bibliographies and additional paper text. Among the collections examined on November 21, 2026, we found no release combining the same acting-model versus runtime definitions, a general-AI probability sample and paired full-paper labels from two reviewers.

## What does the largest database label?

The Guardrail’s November 21 export contains **77,215 records**. Its GPT-5.6 Terra classifier reads titles and abstracts and assigns categories from a fixed taxonomy. All records have at least one category. **74,423** have at least one fine-grained tag from the 51 observed tags. The published method describes no unsupervised clustering. The browse export has no embedding or cluster-ID column. A paper can appear in several of the counts below. [Methodology](https://theguardrail.net/methodology/) · [Browse export](https://data.theguardrail.net/index/browse-index.json)

| Category | Papers |
|---|---:|
| Evaluations | 43,402 |
| Robustness | 30,835 |
| Agents | 27,111 |
| Alignment | 21,229 |
| Interpretability | 13,122 |
| Governance | 7,197 |

## Where do the databases intersect?

| External collection | Records used for matching | Distinct master IDs | What it contributes |
|---|---:|---:|---|
| [The Guardrail](https://theguardrail.net/methodology/) | 68,933 | 8,076 | In-window arXiv IDs. The tags include preference learning, guardrails and sandboxing. Tags describe topics, which can include evaluating a method. |
| [AI Safety Radar](https://aisafetyradar.org/about) | 234 | 156 | Haiku labels after a keyword screen. We take the union of two topics listed in October 2026, restricted to October arXiv IDs. |
| [AI Alignment Research Dataset, Stampy](https://huggingface.co/datasets/StampyAI/alignment-research-dataset) | 311 | 48 | In-window IDs from the 1,744-record arXiv component. It contains document text and source metadata. Other components include forum posts and books. |
| [Mapping Technical Safety Research at AI Companies](https://arxiv.org/abs/2409.07878) | 78 | 29 | Hand-coded safety approaches across three labs. The report gives 80. The linked workbook’s “All papers” sheet contains 78 positive records after explicitly marked duplicates are removed, matching its “Summary” sheet. |
| [AI Disclosures Project](https://github.com/AI-Disclosures-Project/Real-World-Gaps-in-AI-Governance-Research) | 5,337 | 77 | Distinct normalized titles with recognized codes in the public partial file, including negative examples. Categories distinguish pre-deployment alignment and post-deployment risks. |
| [Large Language Model Alignment survey](https://github.com/Magnetic2014/llm-alignment-survey) | 209 | 48 | Distinct titles extracted from numbered, bold-title reading-list entries across periods. Retains author-assigned section headings, including RL-based and supervised methods. |
| [ControlArena research bibliography](https://control-arena.aisi.org.uk/research.html) | 12 | 4 | Listed papers and posts using a control research framework. Inclusion indicates use of the framework. The individual paper can emphasize measurement or another contribution. |

Source denominators differ by date, venue and inclusion criteria. A missing title can be a different version or a publication outside the study frame. Matches use a canonical arXiv ID first, then an exact normalized title unique in the master. A conflicting arXiv ID blocks a title match. Source categories are preserved and a paper may have multiple labels. Across collections one paper can match repeatedly. The three-lab spreadsheet and the curated survey offer sources of human judgment. Guardrail and Radar are independent automated abstract measurements. [Matched labels](results/external_matches.csv.gz) · [Per-source counts, hashes and URLs](results/external_comparison.json) · [Diagnostic sample of unmatched records](results/external_gap_sample.csv)

## Does independent topic selection reveal a coverage gap?

All 234 Radar IDs were present in the frozen source catalog. The master contains **122 of 161 alignment-training papers (76%)** and **41 of 83 control-and-monitoring papers (49%)**. The alignment shortlist contains **67** and **9**, respectively. Ten papers carry both Radar labels. Excluding those ten leaves **115 of 151** training-only and **34 of 73** control-only papers in the master. The comparison measures retrieval on one externally selected month. Inferring a field-wide correction factor would require a broader independent sample.

For a mechanism check, both providers received the same frozen abstract with no Radar tags, previous scores or information about whether the paper entered the master. Jev received 67 questions, Qwen the three headline questions. We count external when either supervision or runtime harnesses qualifies. Among 42 missing control-tagged papers, Jev marked 18 as external, Qwen marked 30 and both marked 17. Among 39 missing training-tagged papers, each reviewer marked 32 as weight-focused and both marked 29. These 468 calls cost approximately $0.038 in total. This measures model agreement under a common definition. Human adjudication remains necessary to estimate accuracy. [All 234 IDs and source tags](results/external_radar_frame.csv) · [Paired scores](results/external_radar_ratings.csv.gz) · [Results by retrieval status](results/external_radar_check.json)

## What can alphaXiv add?

A site-restricted web search of public alphaXiv paper pages returned four distinct in-window arXiv IDs among its first five results. Two were missing even from the master. This was a targeted runtime-oversight query and measures discovery value only. The October Radar comparison also missed both among its two selected topics (one was published in July).

| Paper | In our master | Why it matters |
|---|---|---|
| [ARIA](https://www.alphaxiv.org/abs/2610.20780) | No | Learns a repair policy that intervenes in running multi-agent systems. A trained external controller and the acting model can have different weights. |
| [AgentTether](https://www.alphaxiv.org/abs/2607.06273) | No | Studies diagnosis and runtime intervention in LLM agent trajectories. |
| [Harnessing Embodied Agents](https://www.alphaxiv.org/abs/2604.07833) | Candidate only | Explicit runtime policy checking, rollback and human override. The shortlist misses it. |
| [Comparing Human Oversight Strategies for Computer-Use Agents](https://www.alphaxiv.org/abs/2604.04918) | Shortlist | A positive coverage check for human oversight. |

The exact web query was `site:alphaxiv.org/abs agent runtime oversight frozen language model monitor interventions trajectories "runtime" 2025 external oversight scaffolding before:2026-11-01`. We collapsed two versions of *Harnessing Embodied Agents* by arXiv ID. This check used the public pages. AlphaXiv separately documents an authenticated service for combining keyword and embedding retrieval with publication-date filters, and for returning query-relevant PDF pages. Page numbers can support label adjudication. Platform views and upvotes measure reader activity and should carry an observation date. Direct alphaXiv submissions may add publications outside arXiv. The paper explorer links arXiv records to their alphaXiv pages. Indexed copies of arXiv papers share their original paper ID. [Discovery and page retrieval](https://www.alphaxiv.org/docs/mcp) · [Platform views](https://www.alphaxiv.org/) · [Submission policy and authorship tracks](https://www.alphaxiv.org/docs/submission-policy)

## Other related resources

The TAI Safety Bibliographic Database also catalogs non-paper research and distinguishes technical from meta safety. QURI’s AI Safety Papers interface uses that research lineage. FLI’s AI Safety Index extends the AI Lab Watch collection of company publications. Concordia AI’s geography-specific frontier-safety database and CSET’s citation-cluster mapping are additional ways to test which institutions and research communities a paper search captures. MIT’s AI Risk Mitigation Repository classifies individual mitigations extracted from documents. These resources were considered qualitatively. [TAI bibliography](https://www.alignmentforum.org/posts/4DegbDJJiMX2b3EKm/tai-safety-bibliographic-database) · [QURI](https://ai-safety-papers.quantifieduncertainty.org/about) · [FLI index](https://futureoflife.org/wp-content/uploads/2026/07/AI-Safety-Index-Summer-2026-Digital-14-Jul.pdf) · [Concordia AI](https://concordia-ai.com/wp-content/uploads/2025/07/State-of-AI-Safety-in-China-Spring-2024-Report-public.pdf) · [CSET](https://cset.georgetown.edu/wp-content/uploads/Exploring-Clusters-of-Research-in-Three-Areas-of-AI-Safety.pdf) · [MIT](https://airisk.mit.edu/ai-risk-mitigations)

## Reproduce the comparison

The released tables and scores support offline analysis. The download command compares source hashes against the published snapshot. Mutable indexes can change. For a new snapshot, retain the outputs separately. The paired abstract collection uses the original catalog produced by the study and provider API keys.

```sh
python external_results.py
python external_sources.py /tmp/comparator-inputs
python external_comparison.py /tmp/comparator-inputs --output /tmp/comparator-rebuild
python external_blind_check.py /path/to/catalog.sqlite /tmp/radar-ratings
```

The full-paper collectors also accept `--cohort language-comparators`. This selects all **112** other core language-model alignment papers and **60** language-model papers in the general-AI audit. These 172 IDs are disjoint from the 60 explicitly worded papers already read. Preserve them as separate groups. The same two evidence types and model calls in the 60-paper pilot would cost about **$0.65** for 172 additional papers at the pilot’s mean cost. PDF lengths and provider prices affect actual usage. Coverage checks on papers outside the original frame answer a separate question.

```sh
python fulltext_rate.py /tmp/papers /tmp/ratings --cohort language-comparators --dry-run
python fulltext_sources.py /tmp/papers --cohort language-comparators
python fulltext_rate.py /tmp/papers /tmp/ratings --cohort language-comparators
python fulltext_analysis.py --export /tmp/papers /tmp/ratings --cohort language-comparators
```
