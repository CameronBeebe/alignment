"""Select one unique arXiv cs.CL comparison paper per reviewed cs.CL core paper."""

import csv
import gzip
import hashlib
import json
import sqlite3
import sys

import numpy as np
from scipy.optimize import linear_sum_assignment
from semantic_map import ROOT, encode, records


def main(db):
    with (ROOT / "data/attention_review.csv").open() as f:
        ids = sorted(
            r["paper_id"]
            for r in csv.DictReader(f)
            if r["primary_arxiv_category"] == "cs.CL"
        )
    reviewed = records()
    with (ROOT / "results/reviewed_papers.csv").open() as f:
        excluded = {r["paper_id"] for r in csv.DictReader(f)}
    groups = {}
    with sqlite3.connect(db) as con:
        for pid, month in con.execute(
            """SELECT id,month FROM papers WHERE source='arxiv'
                              AND (venue='cs.CL' OR venue LIKE 'cs.CL %')
                              AND month BETWEEN '2021-11' AND '2026-10'"""
        ):
            if "arxiv:" + pid in excluded:
                continue
            groups.setdefault(month[:4], []).append(pid)
        pool = {}
        for year, options in sorted(groups.items()):
            ranked = sorted(
                options,
                key=lambda x: hashlib.sha256(("cl-match-v1/" + x).encode()).digest(),
            )
            for pid in ranked[:300]:
                title, abstract = con.execute(
                    "SELECT title,abstract FROM papers WHERE source='arxiv' AND id=?",
                    (pid,),
                ).fetchone()
                pool["arxiv:" + pid] = (title, abstract)
    poolids = sorted(pool)
    keys = ids + poolids
    texts = [reviewed[p] if p in ids else pool[p] for p in keys]
    # Match on titles to limit matching on the method descriptions contained in abstracts.
    vectors = encode([v[0] for v in texts], "passage: ")
    sim = vectors[: len(ids)] @ vectors[len(ids) :].T
    for i, p in enumerate(ids):
        for j, q in enumerate(poolids):
            if p[6:8] != q[6:8]:
                sim[i, j] = -2
    left, right = linear_sum_assignment(-sim)
    with (ROOT / "data/matched_cscl.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            ["core_id", "core_title", "comparison_id", "title", "abstract", "cosine"]
        )
        for i, j in zip(left, right):
            assert sim[i, j] > 0 and ids[i][6:8] == poolids[j][6:8]
            w.writerow(
                [
                    ids[i],
                    reviewed[ids[i]][0],
                    poolids[j],
                    *pool[poolids[j]],
                    round(float(sim[i, j]), 6),
                ]
            )


if __name__ == "__main__":
    main(sys.argv[1])
