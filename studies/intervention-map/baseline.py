"""Reproduce the general AI baseline draw and its stratified estimates."""

import argparse
import csv
import hashlib
import json
import re
import sqlite3
from collections import Counter
from pathlib import Path

import numpy as np
from scipy.stats import t

ROOT = Path(__file__).resolve().parent
CATEGORIES = {"cs.AI", "cs.CL", "cs.CV", "cs.LG", "cs.NE", "cs.RO", "stat.ML"}
CONTROL = re.compile(
    r"guardrail|runtime|run.time|shield|supervis|controller|model predictive control|"
    r"safety filter|tool.use|tool.call|workflow|planning|planner|multi.agent|"
    r"orchestrat|retrieval.augmented|human.in.the.loop|verifier|verification|"
    r"enforc|constrained decoding|sandbox|permission",
    re.I,
)
SIZES = {"control_cue": 80, "other": 100}


def draw(db):
    con = sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True)
    pools = {h: [] for h in SIZES}
    counts = Counter()
    query = """SELECT id, venue, title, abstract FROM papers WHERE source='arxiv'
               AND month BETWEEN '2021-11' AND '2026-10'"""
    for pid, venue, title, abstract in con.execute(query):
        category = venue.split()[0]
        if category not in CATEGORIES:
            continue
        h = "control_cue" if CONTROL.search(title + " " + abstract) else "other"
        key = hashlib.sha256(("ai-baseline-v1:" + pid).encode()).hexdigest()
        counts[h] += 1
        pools[h].append((key, pid))
    with (ROOT / "data/baseline_draw.csv").open("w", newline="", encoding="utf-8") as f:
        out = csv.writer(f)
        out.writerow(
            [
                "review_id",
                "arxiv_id",
                "category",
                "stratum",
                "population",
                "sample",
                "title",
                "abstract",
            ]
        )
        idx = 0
        for h, size in SIZES.items():
            for _, pid in sorted(pools[h])[:size]:
                idx += 1
                venue, title, abstract = con.execute(
                    "SELECT venue,title,abstract FROM papers WHERE source='arxiv' AND id=?",
                    (pid,),
                ).fetchone()
                out.writerow(
                    [idx, pid, venue.split()[0], h, counts[h], size, title, abstract]
                )
    con.close()


def estimate():
    with (ROOT / "data/baseline_draw.csv").open() as f:
        rows = list(csv.DictReader(f))
    with (ROOT / "data/baseline_review.csv").open() as f:
        review = list(csv.DictReader(f))
    labels = {r["arxiv_id"]: r["codes"] for r in review}
    if (
        len(rows) != sum(SIZES.values())
        or len(review) != len(rows)
        or len(labels) != len(rows)
        or set(labels) != {r["arxiv_id"] for r in rows}
    ):
        raise ValueError("Incomplete review")
    if not set(labels.values()) <= {"W", "E", "H", "WE", "WH", "EH", "WEH", "none"}:
        raise ValueError("Unknown mechanism code")
    cells = {}
    for h, n in SIZES.items():
        group = [r for r in rows if r["stratum"] == h]
        assert len(group) == n
        cells[h] = (
            int(group[0]["population"]),
            np.array([[int(m in labels[r["arxiv_id"]]) for m in "WEH"] for r in group]),
        )
    population = sum(N for N, _ in cells.values())
    result = {
        "population": population,
        "reviewed": len(rows),
        "groups": {},
        "estimates": {},
    }
    for h, (N, x) in cells.items():
        result["groups"][h] = dict(
            population=N, reviewed=len(x), WEH=x.sum(axis=0).tolist()
        )
    for label, a, b in [
        ("weight_share", "W", None),
        ("external_control_share", "E", None),
        ("harness_share", "H", None),
        ("weight_to_control", "W", "E"),
        ("weight_to_harness", "W", "H"),
        ("either_system_share", "S", None),
        ("weight_to_either_system", "W", "S"),
    ]:

        def values(x, m):
            if m is None:
                return np.ones(len(x))
            if m == "S":
                return np.maximum(x[:, 1], x[:, 2])
            return x[:, "WEH".index(m)]

        A, B = (sum(N * values(x, m).mean() for N, x in cells.values()) for m in (a, b))
        if min(A, B) <= 0:
            raise ValueError("Cannot estimate a log interval with a zero total")
        parts = []
        for N, x in cells.values():
            z = values(x, a) / A - values(x, b) / B
            parts.append((N**2 * (1 - len(x) / N) * z.var(ddof=1) / len(x), len(x) - 1))
        variance = sum(v for v, _ in parts)
        df = variance**2 / sum(v * v / d for v, d in parts)
        delta = t.ppf(0.975, df) * np.sqrt(variance)
        result["estimates"][label] = {
            "value": A / B,
            "ci95": (A / B * np.exp([-delta, delta])).tolist(),
        }
    (ROOT / "results/general_ai_baseline.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--draw-from", type=Path, help="Regenerate sample from the frozen catalog"
    )
    args = parser.parse_args()
    if args.draw_from:
        draw(args.draw_from)
    else:
        estimate()
