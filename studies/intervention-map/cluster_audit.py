"""Draw a fixed sample per shortlist cluster and compare Jev mechanisms across topics."""

import csv
import hashlib
import json
from collections import defaultdict

import numpy as np

from semantic_map import ROOT

SAMPLE_PER_CLUSTER = 32
SALT = "alignment-cluster-audit-v1/"


def draw():
    with (ROOT / "results/alignment_papers.csv").open() as f:
        eligible = {r["paper_id"] for r in csv.DictReader(f)}
    pools = defaultdict(list)
    with (ROOT / "results/semantic_clusters.csv").open() as f:
        for row in csv.DictReader(f):
            if row["paper_id"] in eligible:
                pools[int(row["semantic_cluster"])].append(row["paper_id"])
    return {
        g: sorted(ids, key=lambda pid: hashlib.sha256((SALT + pid).encode()).digest())[
            :SAMPLE_PER_CLUSTER
        ]
        for g, ids in sorted(pools.items())
    }


def main():
    groups = draw()
    rows = [
        json.loads(s)
        for s in (ROOT / "results/jev_cluster_audit.jsonl").read_text().splitlines()
    ]
    scores = {r["paper_id"]: r["scores"] for r in rows}
    ordered = [pid for ids in groups.values() for pid in ids]
    if len(scores) != len(rows) or set(ordered) != set(scores):
        raise ValueError("Audit does not match the stratified draw")
    result = {
        "models": sorted({r["model"] for r in rows}),
        "sample_per_group": SAMPLE_PER_CLUSTER,
        "thresholds": {},
    }
    for threshold in (0.3, 0.5, 0.7):
        labels = np.array(
            [
                [
                    v["weights"] >= threshold,
                    max(v["supervision"], v["scaffolding"]) >= threshold,
                    max(v["feedback"], v["dynamics"]) >= threshold,
                ]
                for v in (scores[p] for p in ordered)
            ],
            dtype=int,
        )

        def totals(arr):
            return arr.reshape(len(groups), SAMPLE_PER_CLUSTER, 3).sum(axis=1)

        counts = totals(labels)

        def statistic(c):
            # Equal group sizes; sum of squared between-group deviations orders the permutation test.
            return ((c - counts.mean(axis=0)) ** 2).sum(axis=0)

        observed = statistic(counts)
        rng = np.random.default_rng(174)
        exceed = np.ones(3)
        for i in range(9999):
            exceed += (
                statistic(totals(rng.permutation(labels, axis=0))) >= observed - 1e-9
            )
        p = exceed / 10000
        order = np.argsort(p)
        adjusted = np.empty(3)
        adjusted[order] = np.minimum(
            1, np.maximum.accumulate(p[order] * np.arange(3, 0, -1))
        )
        result["thresholds"][str(threshold)] = {
            "dimensions": ["weights", "external", "feedback_or_dynamics"],
            "counts": counts.tolist(),
            "permutation_p": p.tolist(),
            "holm_p": adjusted.tolist(),
        }
    (ROOT / "results/cluster_audit.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
