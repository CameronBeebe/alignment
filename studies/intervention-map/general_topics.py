"""Group a vocabulary-independent general AI sample without injecting control-systems papers."""

import csv
import gzip
import json

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, adjusted_rand_score
from threadpoolctl import threadpool_limits

from cluster_geometry import project
from semantic_map import ROOT, encode


def main():
    with gzip.open(ROOT / "data/control_sample.csv.gz", "rt") as f:
        rows = [r for r in csv.DictReader(f) if r["frame"] == "general_ai"]
    x = encode([r["title"] + ". " + r["abstract"] for r in rows], "passage: ")
    with threadpool_limits(4):
        fits = {
            k: KMeans(n_clusters=k, random_state=17, n_init=12).fit(x)
            for k in (4, 6, 8, 12, 16)
        }
        quality = {
            k: float(silhouette_score(x, fit.labels_, metric="cosine"))
            for k, fit in fits.items()
        }
        k = max(quality, key=quality.get)
        best = fits[k]
        alt = KMeans(n_clusters=k, random_state=43, n_init=12).fit_predict(x)
        project([r["paper_id"] for r in rows], x, "general_geometry.csv")
    distance = np.linalg.norm(x - best.cluster_centers_[best.labels_], axis=1)
    examples = []
    for g in range(k):
        ix = np.flatnonzero(best.labels_ == g)
        top = sorted(ix, key=lambda i: distance[i])[:8]
        examples.append(
            {"id": g, "n": len(ix), "center_titles": [rows[i]["title"] for i in top]}
        )
    with (ROOT / "results/general_topics.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["paper_id", "cluster", "distance"])
        w.writerows(
            (r["paper_id"], int(best.labels_[i]), round(float(distance[i]), 6))
            for i, r in enumerate(rows)
        )
    (ROOT / "results/general_topics.json").write_text(
        json.dumps(
            {
                "silhouette": quality,
                "k": k,
                "alternate_seed_ARI": adjusted_rand_score(best.labels_, alt),
                "groups": examples,
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
