"""Project two frozen embedding maps, retain original-space neighbors and test coauthorship."""

import argparse
import csv
import gzip
import json

import numpy as np
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from threadpoolctl import threadpool_limits

from author_network import author_names, make_graph
from semantic_map import ROOT, encode


def csv_rows(name):
    with (ROOT / name).open() as f:
        return list(csv.DictReader(f))


def project(ids, vectors, destination):
    # The 2D positions are for display. Similar papers come from exact cosine ranks in full E5 space.
    reduced = PCA(
        n_components=50, svd_solver="randomized", random_state=17
    ).fit_transform(vectors)
    points = TSNE(
        n_components=2,
        init="pca",
        perplexity=35,
        learning_rate="auto",
        max_iter=1000,
        random_state=17,
        n_jobs=4,
    ).fit_transform(reduced)
    with (ROOT / "results" / destination).open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["paper_id", "x", "y", "neighbors"])
        for start in range(0, len(ids), 128):
            sims = vectors[start : start + 128] @ vectors.T
            for k, row in enumerate(sims):
                i = start + k
                row[i] = -np.inf
                nearest = np.argsort(-row, kind="stable")[:4]
                writer.writerow(
                    [
                        ids[i],
                        round(float(points[i, 0]), 3),
                        round(float(points[i, 1]), 3),
                        " ".join(ids[j] for j in nearest),
                    ]
                )


def authors(shortlist, ids):
    metadata = {r["paper_id"]: r for r in shortlist}
    groups = {
        r["paper_id"]: int(r["semantic_cluster"])
        for r in csv_rows("results/semantic_clusters.csv")
    }
    graph = make_graph({pid: author_names(metadata[pid]) for pid in ids})
    index = {pid: i for i, pid in enumerate(ids)}
    edges = np.array([(index[a], index[b]) for a, b in graph.edges()])
    labels = np.array([groups[pid] for pid in ids])
    years = np.array([metadata[pid]["year"] for pid in ids])
    blocks = [np.flatnonzero(years == y) for y in np.unique(years)]

    def same(lab):
        return int(np.count_nonzero(lab[edges[:, 0]] == lab[edges[:, 1]]))

    observed = same(labels)
    rng = np.random.default_rng(310)
    null = []
    for _ in range(1999):
        shuffled = labels.copy()
        for block in blocks:
            shuffled[block] = rng.permutation(labels[block])
        null.append(same(shuffled))
    n = len(edges)
    result = {
        "edges": n,
        "same_topic_edges": observed,
        "observed_share": observed / n,
        "year_permuted_mean": float(np.mean(null) / n),
        "null_interval": (np.quantile(null, [0.025, 0.975]) / n).tolist(),
        "permutations": len(null),
        "p_upper": (1 + sum(v >= observed for v in null)) / (1 + len(null)),
    }
    (ROOT / "results/coauthor_topic_test.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vectors", required=True)
    args = parser.parse_args()
    shortlist = csv_rows("results/alignment_papers.csv")
    ids = sorted(r["paper_id"] for r in shortlist)
    cache = np.load(args.vectors)
    lookup = {pid: i for i, pid in enumerate(cache["ids"].tolist())}
    x = cache["vectors"][[lookup[pid] for pid in ids]]
    authors(shortlist, ids)
    with threadpool_limits(limits=4):
        project(ids, x, "shortlist_geometry.csv")
    with gzip.open(ROOT / "data/control_sample.csv.gz", "rt") as f:
        control = list(csv.DictReader(f))
    x = encode([r["title"] + ". " + r["abstract"] for r in control], "passage: ")
    with threadpool_limits(limits=4):
        project([r["paper_id"] for r in control], x, "control_geometry.csv")


if __name__ == "__main__":
    main()
