"""Rebuild harmonized intervention estimates and terminology checks from the frozen reviews."""

import csv
import gzip
import hashlib
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score

from estimate import ratio_stats
from snapshot import archive_path

ROOT = Path(__file__).resolve().parent
DATA, OUT = ROOT / "data", ROOT / "results"
WORDS = re.compile(
    r"\b(?:harness(?:es)?|scaffold(?:s|ing)?|orchestrat\w*|supervisory control|closed.loop|tool.use|middleware)\b",
    re.I,
)
LITERAL = re.compile(r"\bharness(?:es)?\b", re.I)
REVIEW_SALT = "map-check-1/"


def read_csv(path):
    return pd.read_csv(path, keep_default_na=False, dtype={"arxiv_id": str})


def paper_tables():
    old = read_csv(OUT / "reviewed_papers.csv")
    new = read_csv(DATA / "attention_review.csv")
    if set(new.paper_id) != set(old.loc[old.scope == "core", "paper_id"]):
        raise ValueError(
            "All originally reviewed core papers must receive a common code"
        )
    paper = read_csv(OUT / "papers.csv")[["paper_id", "named", "year"]]
    a = old.merge(
        new.drop(columns="review_id"), on="paper_id", how="left", validate="one_to_one"
    ).merge(paper, on="paper_id", validate="one_to_one")
    a["common_codes"] = a.common_codes.fillna("none")
    a["core"] = a.scope.eq("core")
    b = (
        read_csv(DATA / "baseline_draw.csv")
        .merge(
            read_csv(DATA / "baseline_review.csv")[["arxiv_id", "codes"]],
            on="arxiv_id",
            validate="one_to_one",
        )
        .rename(
            columns={
                "sample": "n_h",
                "population": "N_h",
                "codes": "common_codes",
                "category": "primary_arxiv_category",
            }
        )
    )
    b["paper_id"] = "arxiv:" + b.arxiv_id
    b["year"] = 2000 + b.arxiv_id.str[:2].astype(int)
    b["core"] = True
    b["named"] = False
    return a, b


def estimates(d, mask, code="common_codes"):
    w = d[code].str.contains("W").astype(int) * mask
    e = d[code].str.contains("E").astype(int) * mask
    h = d[code].str.contains("H").astype(int) * mask
    return {
        "domain_review_n": int(mask.sum()),
        "W_E": ratio_stats(d, w, e),
        "W_H": ratio_stats(d, w, h),
        "W_either": ratio_stats(d, w, np.maximum(e, h)),
    }


def main():
    a, b = paper_tables()
    results = {}
    for name, d in [("core", a), ("explicit", a), ("general_ai", b)]:
        keep = d.core & (d.named if name == "explicit" else True)
        group = results[name] = {"full": estimates(d, keep)}
        for era, years in [("2021_24", d.year < 2025), ("2025_26", d.year >= 2025)]:
            group[era] = estimates(d, keep & years)
            group["cs_CL_" + era] = estimates(
                d, keep & years & d.primary_arxiv_category.eq("cs.CL")
            )
    focus = set(a.loc[a.core, "paper_id"])
    with gzip.open(archive_path(DATA), "rt") as f:
        texts = {
            r["paper_id"]: r["title"] + " " + r["abstract"]
            for r in map(json.loads, f)
            if r["paper_id"] in focus
        }
    for d, strings in [
        (a, a.paper_id.map(texts).fillna("")),
        (b, b.title + " " + b.abstract),
    ]:
        ys = d.common_codes.str.contains("H")
        raw = d.loc[ys, ["paper_id", "year", "N_h", "n_h"]].copy()
        for k, rx in [("literal", LITERAL), ("expanded", WORDS)]:
            raw[k] = strings.loc[ys].map(lambda x: bool(rx.search(x)))
        out = []
        for era, r in raw.groupby(np.where(raw.year < 2025, "2021_24", "2025_26")):
            out.append(
                {
                    "period": era,
                    "reviewed_harness": len(r),
                    "literal_matches": int(r.literal.sum()),
                    "expanded_matches": int(r.expanded.sum()),
                }
            )
        results.setdefault("terminology", {})[
            "alignment" if d is a else "general_ai"
        ] = out
    m = read_csv(OUT / "control_map.csv")
    v = read_csv(DATA / "control_validation.csv").merge(
        m.rename(columns={"dynamics": "dynamics_similarity"}),
        on="paper_id",
        validate="one_to_one",
    )
    for k, g in m.groupby("cluster"):
        expected = sorted(
            g.paper_id,
            key=lambda s: hashlib.sha256((REVIEW_SALT + s).encode()).digest(),
        )[:15]
        if set(expected) != set(v.loc[v.cluster == k, "paper_id"]):
            raise ValueError("Validation draw differs from frozen sample")
    v["sample_weight"] = v.cluster.map(m.cluster.value_counts()) / 15
    y = v.feedback_loop.astype(bool) | v.dynamics.astype(bool)
    scores = {
        "cue": v.cue,
        "feedback_query": v.feedback,
        "dynamics_query": v.dynamics_similarity,
    }
    results["control_validation"] = {
        "raw_positives": int(y.sum()),
        "groups": [
            {"id": int(k), "positive": int(y.loc[g.index].sum()), "n": len(g)}
            for k, g in v.groupby("cluster")
        ],
        "average_precision": {
            k: average_precision_score(y, s, sample_weight=v.sample_weight)
            for k, s in scores.items()
        },
        "cue_missed_positive": int((y & v.cue.eq(0)).sum()),
        "cue_false_positive": int((~y & v.cue.eq(1)).sum()),
    }
    (OUT / "attention.json").write_text(json.dumps(results, indent=2) + "\n")


if __name__ == "__main__":
    main()
