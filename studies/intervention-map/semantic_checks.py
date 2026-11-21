"""Cross-frame harness prediction, paired comparisons and sample coverage."""

import csv
import gzip
import json
import sys
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score
from attention import ROOT, LITERAL, WORDS, paper_tables, read_csv
from semantic_map import records


def main(cache_path):
    audit, base = paper_tables()
    audit = audit.loc[audit.core].copy()
    docs = records()
    cache = np.load(cache_path)
    vec = dict(zip(cache["ids"], cache["vectors"]))
    output = {}
    for name, train, test in [
        ("general_to_alignment", base, audit),
        ("alignment_to_general", audit, base),
    ]:
        # A shared paper must never be both a training example and a test item.
        train = train.loc[~train.paper_id.isin(test.paper_id)]
        get = lambda d: np.stack([vec[i] for i in d.paper_id])
        y = test.common_codes.str.contains("H").astype(int)
        wt = test.N_h / test.n_h
        model = LogisticRegression(C=10, max_iter=500).fit(
            get(train), train.common_codes.str.contains("H")
        )
        text = [". ".join(docs[i]) for i in test.paper_id]
        output[name] = {
            "test_n": len(test),
            "reviewed_positive": int(y.sum()),
            "weighted_prevalence": float(np.average(y, weights=wt)),
            "average_precision": {
                label: float(average_precision_score(y, pred, sample_weight=wt))
                for label, pred in [
                    ("embedding", model.predict_proba(get(test))[:, 1]),
                    ("expanded", [bool(WORDS.search(s)) for s in text]),
                    ("literal", [bool(LITERAL.search(s)) for s in text]),
                ]
            },
        }
    matches = read_csv(ROOT / "data/matched_cscl.csv").merge(
        read_csv(ROOT / "data/matched_review.csv"),
        on="comparison_id",
        validate="one_to_one",
    )
    matches = matches.merge(
        audit[["paper_id", "common_codes"]],
        left_on="core_id",
        right_on="paper_id",
        suffixes=("_comparison", "_core"),
        validate="one_to_one",
    )
    if (
        len(matches) != 49
        or matches.core_id.duplicated().any()
        or matches.comparison_id.duplicated().any()
    ):
        raise ValueError("Invalid pairs")
    counts = []
    for side in ("core", "comparison"):
        codes = matches["common_codes_" + side]
        counts.append(
            np.stack(
                [codes.str.contains("W"), codes.str.contains("E|H")], axis=1
            ).astype(int)
        )
    arr = np.stack(counts, axis=1)
    sums = arr.sum(axis=0)
    idx = np.random.default_rng(17).integers(0, len(arr), (10000, len(arr)))
    reps = arr[idx].sum(axis=1)
    reps = reps[(reps > 0).all(axis=(1, 2))]

    def contrast(s):
        return (s[..., 0, 0] / s[..., 0, 1]) / (s[..., 1, 0] / s[..., 1, 1])

    output["pairs"] = {
        "n": len(arr),
        "counts_core_comparison": sums.tolist(),
        "ratio_of_ratios": contrast(sums),
        "paired_bootstrap_ci": np.quantile(contrast(reps), [0.025, 0.975]).tolist(),
        "resamples_with_nonzero_cells": len(reps),
        "median_title_cosine": float(matches.cosine.median()),
    }
    m = read_csv(ROOT / "results/control_map.csv")
    candidates = set(read_csv(ROOT / "results/papers.csv").paper_id)
    short = set(read_csv(ROOT / "results/alignment_papers.csv").paper_id)
    output["coverage"] = {
        str(g): {
            "n": len(rows),
            "candidate_id_overlap": int(rows.paper_id.isin(candidates).sum()),
            "shortlist_id_overlap": int(rows.paper_id.isin(short).sum()),
        }
        for g, rows in m.groupby("cluster")
    }
    (ROOT / "results/semantic_checks.json").write_text(
        json.dumps(output, indent=2) + "\n"
    )


if __name__ == "__main__":
    main(sys.argv[1])
