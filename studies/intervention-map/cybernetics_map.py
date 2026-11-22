"""Test whether a separate category sample yields feedback/control neighborhoods."""

import csv
import gzip
import json
import re
from pathlib import Path

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score, silhouette_score
from threadpoolctl import threadpool_limits

from semantic_map import ROOT, encode

# The queries name functions independently of author terminology. They do not enter clustering.
QUERIES = {
    "feedback": "Systems that observe their own or the environment's state and change subsequent actions to regulate error, maintain stability, or adapt behavior in a closed loop.",
    "dynamics": "A mathematical study of how an interacting system evolves through time, its equilibria, trajectories, stability, observability or controllability.",
    "scaffold": "A runtime architecture around an AI model that coordinates external tools, memory, retrieval, planning, verification or multiple agents for a task.",
    "weight": "Learning new parameters of a predictive model or policy by training on data, fine tuning neural weights, or optimizing its training loss.",
}
PATTERN = re.compile(
    r"\b(?:cybernetic\w*|control theor\w*|dynamical systems?|closed.loop|feedback control\w*|stabili[tz]\w*|lyapunov|model predictive control|control barrier)\b",
    re.I,
)


def main():
    with gzip.open(ROOT / "data/control_sample.csv.gz", "rt") as f:
        rows = list(csv.DictReader(f))
    x = encode([r["title"] + ". " + r["abstract"] for r in rows], "passage: ")
    q = encode(list(QUERIES.values()), "query: ")
    sims = x @ q.T
    for i, r in enumerate(rows):
        r["cue"] = int(bool(PATTERN.search(r["title"] + " " + r["abstract"])))
        for j, key in enumerate(QUERIES):
            r[key] = round(float(sims[i, j]), 5)
    with threadpool_limits(limits=1):
        tests = {}
        fits = {}
        for k in (6, 10, 14, 18):
            fit = KMeans(n_clusters=k, n_init=12, random_state=17).fit(x)
            fits[k] = fit
            tests[k] = float(silhouette_score(x, fit.labels_, metric="cosine"))
        k = max(tests, key=tests.get)
        model = fits[k]
        alt = KMeans(n_clusters=k, n_init=12, random_state=43).fit_predict(x)
    distances = np.linalg.norm(x - model.cluster_centers_[model.labels_], axis=1)
    groups = []
    for g in range(k):
        ix = np.where(model.labels_ == g)[0]
        examples = sorted(ix, key=lambda i: distances[i])[:5]
        groups.append(
            {
                "id": g,
                "n": len(ix),
                "general_ai": sum(rows[i]["frame"] == "general_ai" for i in ix),
                "cue": sum(rows[i]["cue"] for i in ix),
                "mean_feedback_similarity": float(sims[ix, 0].mean()),
                "mean_dynamics_similarity": float(sims[ix, 1].mean()),
                "titles": [rows[i]["title"] for i in examples],
            }
        )
    for i, r in enumerate(rows):
        r["cluster"] = int(model.labels_[i])
        r["distance"] = round(float(distances[i]), 6)
        del r["abstract"]
    with (ROOT / "results/control_map.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    (ROOT / "results/control_map.json").write_text(
        json.dumps(
            {
                "queries": QUERIES,
                "silhouettes": tests,
                "k": k,
                "alternate_seed_ARI": adjusted_rand_score(model.labels_, alt),
                "groups": groups,
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
