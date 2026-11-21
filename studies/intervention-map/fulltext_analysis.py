"""Release matched ratings and reproduce comparisons from paper-level measurements."""

import argparse
import json
import math
import re
from pathlib import Path

import pandas as pd
from scipy.stats import t

from attention import ROOT, paper_tables
from estimate import ratio_stats, variance
from fulltext_questions import GROUPS, QUESTIONS
from fulltext_sources import cohort, digest, local_name
from fulltext_rate import PRIMARY, payload
from semantic_map import records

OUT = ROOT / "results"
MEASURES = OUT / "fulltext_measures.csv"
LEDGER = OUT / "fulltext_requests.csv"


def export(sources, cache):
    metadata = records()
    measures = []
    ledger = []
    for row in cohort().itertuples():
        pid = row.paper_id
        title, abstract = metadata[pid]
        meta = json.loads((sources / (local_name(pid) + ".json")).read_text())
        record = {
            "paper_id": pid,
            "title": title,
            "source_url": meta["url"],
            "pdf_sha256": meta.get("pdf_sha256"),
            "text_sha256": meta.get("text_sha256"),
            "pages": meta.get("pages"),
            "characters": meta.get("characters"),
            "pages_under_40_chars": meta.get("pages_under_40_chars"),
            "extraction": meta.get("extractor"),
            "source_error": meta.get("error"),
        }
        inputs = {"abstract": abstract}
        if meta.get("text_sha256"):
            text = (sources / (local_name(pid) + ".txt")).read_bytes()
            if digest(text) != meta["text_sha256"]:
                raise ValueError(pid + " PDF text mismatch")
            inputs["paper"] = text.decode()
            version = re.search(
                r"arXiv:\s*(" + re.escape(pid.split(":")[-1]) + r"v\d+)",
                inputs["paper"][:20000],
                re.I,
            )
            if version:
                record["versioned_pdf_url"] = "https://arxiv.org/pdf/" + version.group(
                    1
                )

        for basis, content in inputs.items():
            for reviewer in ("jev", "qwen"):
                body = json.dumps(
                    payload(reviewer, title, basis, content),
                    sort_keys=True,
                    ensure_ascii=False,
                ).encode()
                signature = digest(body)
                src = cache / f"{local_name(pid)}.{reviewer}.{basis}.{signature}.json"
                rating = json.loads(src.read_text())
                if (
                    rating["paper_id"],
                    rating["basis"],
                    rating["reviewer"],
                    rating["content_sha256"],
                    rating["request_sha256"],
                ) != (pid, basis, reviewer, digest(content.encode()), signature):
                    raise ValueError("Provenance mismatch")
                usage = rating["usage"]
                ledger.append(
                    {
                        **{
                            k: rating[k]
                            for k in [
                                "paper_id",
                                "basis",
                                "reviewer",
                                "model",
                                "provider",
                                "long_context",
                                "request_sha256",
                                "content_sha256",
                            ]
                        },
                        "input_tokens": usage.get(
                            "input_tokens", usage.get("prompt_tokens")
                        ),
                        "output_tokens": usage.get(
                            "output_tokens", usage.get("completion_tokens")
                        ),
                        "reported_cost_usd": usage.get("cost"),
                    }
                )
                keys = QUESTIONS if reviewer == "jev" else PRIMARY
                if set(keys) != set(rating["scores"]):
                    raise ValueError("Incomplete instrument")
                for key in keys:
                    record[f"{reviewer}_{basis}_{key}"] = float(rating["scores"][key])
        measures.append(record)
    pd.DataFrame(measures).to_csv(MEASURES, index=False)
    pd.DataFrame(ledger).to_csv(LEDGER, index=False)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--export", nargs=2, type=Path, metavar=("SOURCES", "CACHE"))
    args = p.parse_args()
    if args.export:
        export(*args.export)
    data = pd.read_csv(MEASURES).set_index("paper_id", verify_integrity=True)
    ledger = pd.read_csv(LEDGER)
    if set(cohort().paper_id) != set(data.index):
        raise ValueError("Cohort differs")
    matched = data.dropna(subset=["text_sha256"])
    if matched.isna().filter(regex="^(jev|qwen)_").any().any():
        raise ValueError("Missing paired ratings")
    a, _ = paper_tables()
    aligned = matched.reindex(a.paper_id).set_axis(a.index)
    ratios = {}
    changes = {}
    flags = {}
    for reviewer in ("jev", "qwen"):
        influence = {}
        for basis in ("abstract", "paper"):
            prefix = f"{reviewer}_{basis}_"
            w = aligned[prefix + "weights"].ge(0.5)
            e = (
                aligned[[prefix + "supervision", prefix + "scaffolding"]]
                .max(axis=1)
                .ge(0.5)
            )
            stats = ratio_stats(a, w, e)
            ratios[reviewer, basis] = stats
            influence[basis] = w / stats["W"] - e / stats["E"]
            flags[reviewer, basis] = w, e
        rr = ratios[reviewer, "paper"]["ratio"] / ratios[reviewer, "abstract"]["ratio"]
        v, df = variance(a, influence["paper"] - influence["abstract"])
        margin = t.ppf(0.975, df) * math.sqrt(v)
        flips = []
        for abstract, paper in zip(
            flags[reviewer, "abstract"], flags[reviewer, "paper"]
        ):
            flips.append(
                {
                    "gained": int((~abstract & paper).sum()),
                    "lost": int((abstract & ~paper).sum()),
                }
            )
        changes[reviewer] = {
            "full_over_abstract": rr,
            "ci95": [rr * math.exp(-margin), rr * math.exp(margin)],
            "weights": flips[0],
            "external": flips[1],
        }
    detail = {}
    for group, questions in GROUPS.items():
        detail[group] = {}
        for key, question in questions.items():
            abstract = matched["jev_abstract_" + key].ge(0.5)
            paper = matched["jev_paper_" + key].ge(0.5)
            detail[group][key] = {
                "question": question,
                "abstract": int(abstract.sum()),
                "paper": int(paper.sum()),
                "gained": int((paper & ~abstract).sum()),
                "lost": int((abstract & ~paper).sum()),
            }
    result = {
        "eligible": len(data),
        "paired": len(matched),
        "pages": int(matched.pages.sum()),
        "thin_pages": int(matched.pages_under_40_chars.sum()),
        "ratios": {f"{rev}_{basis}": r for (rev, basis), r in ratios.items()},
        "changes": changes,
        "questions": detail,
        "accounting": {},
    }
    result["jev_paper_cutoffs"] = {}
    for cutoff in (0.3, 0.5, 0.7):
        w = aligned.jev_paper_weights.ge(cutoff)
        e = (
            aligned[["jev_paper_supervision", "jev_paper_scaffolding"]]
            .max(axis=1)
            .ge(cutoff)
        )
        result["jev_paper_cutoffs"][str(cutoff)] = ratio_stats(a, w, e)
    retained = a.paper_id.ne("arxiv:2608.01629")
    result["excluding_known_withdrawal"] = {
        rev: ratio_stats(
            a, flags[rev, "paper"][0] & retained, flags[rev, "paper"][1] & retained
        )
        for rev in ("jev", "qwen")
    }
    result["agreement"] = {}
    for basis in ("abstract", "paper"):
        result["agreement"][basis] = {
            label: int((a.paper_id.isin(matched.index) & left.eq(right)).sum())
            for label, left, right in zip(
                ("weights", "external"), flags["jev", basis], flags["qwen", basis]
            )
        }
    for rev, entries in ledger.groupby("reviewer"):
        result["accounting"][rev] = {
            "requests": len(entries),
            "long_context": int(entries.long_context.sum()),
            "input_tokens": int(entries.input_tokens.sum()),
            "output_tokens": int(entries.output_tokens.sum()),
            "usd": float(
                entries.input_tokens.sum() * 0.042 / 1e6
                if rev == "jev"
                else entries.reported_cost_usd.sum()
            ),
        }
    (OUT / "fulltext_summary.json").write_text(
        json.dumps(result, indent=2, allow_nan=False) + "\n"
    )


if __name__ == "__main__":
    main()
