"""Build the semantic paper map with a pinned E5 encoder and deterministic clustering."""

import argparse
import csv
import gzip
import json
from pathlib import Path

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score, silhouette_score
from threadpoolctl import threadpool_limits
from snapshot import archive_path

ROOT = Path(__file__).resolve().parent
REV = "ffb93f3bd4047442299a41ebb6fa998a38507c52"
MODEL = "intfloat/e5-small-v2"


def records():
    with (ROOT / "results/alignment_papers.csv").open() as f:
        ids = {r["paper_id"] for r in csv.DictReader(f)}
    with gzip.open(archive_path(ROOT / "data"), "rt") as f:
        candidates = (json.loads(s) for s in f)
        papers = {
            r["paper_id"]: (r["title"], r["abstract"])
            for r in candidates
            if r["paper_id"] in ids
        }
    with (ROOT / "data/baseline_draw.csv").open() as f:
        for r in csv.DictReader(f):
            papers.setdefault("arxiv:" + r["arxiv_id"], (r["title"], r["abstract"]))
    return dict(sorted(papers.items()))


def encode(strings, prefix):
    import torch
    from transformers import AutoModel, AutoTokenizer

    torch.set_num_threads(4)
    tokenizer = AutoTokenizer.from_pretrained(MODEL, revision=REV)
    encoder = AutoModel.from_pretrained(MODEL, revision=REV).eval()
    vectors = []
    with torch.inference_mode():
        for offset in range(0, len(strings), 24):
            batch = tokenizer(
                [prefix + s for s in strings[offset : offset + 24]],
                padding=True,
                truncation=True,
                max_length=160,
                return_tensors="pt",
            )
            hidden = encoder(**batch).last_hidden_state
            mask = batch.attention_mask.unsqueeze(-1)
            means = (hidden * mask).sum(1) / mask.sum(1)
            vectors.extend(torch.nn.functional.normalize(means, dim=1).numpy())
            if offset % 480 == 0:
                print(
                    f"Encoded {min(offset+24,len(strings))}/{len(strings)}", flush=True
                )
    return np.asarray(vectors)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--vectors", type=Path, required=True, help="Cache of paper IDs and embeddings"
    )
    args = ap.parse_args()
    papers = records()
    ids = list(papers)
    if args.vectors.exists():
        cache = np.load(args.vectors)
        if cache["ids"].tolist() != ids:
            raise ValueError("Input paper IDs differ from embedding cache")
        vectors = cache["vectors"]
    else:
        vectors = encode([". ".join(papers[i]) for i in ids], "passage: ")
        np.savez(args.vectors, ids=ids, vectors=vectors)
    with threadpool_limits(limits=1):
        scores = {}
        for k in (8, 12, 16, 20):
            fit = KMeans(n_clusters=k, n_init=10, random_state=17).fit(vectors)
            scores[k] = float(
                silhouette_score(
                    vectors,
                    fit.labels_,
                    metric="cosine",
                    sample_size=1500,
                    random_state=17,
                )
            )
        k = max(scores, key=scores.get)
        fit = KMeans(n_clusters=k, n_init=10, random_state=17).fit(vectors)
        other = KMeans(n_clusters=k, n_init=10, random_state=43).fit_predict(vectors)
    distances = np.linalg.norm(vectors - fit.cluster_centers_[fit.labels_], axis=1)
    summary = {
        "model": MODEL,
        "revision": REV,
        "unique_papers": len(ids),
        "silhouette": scores,
        "k": k,
        "alternate_seed_ARI": adjusted_rand_score(fit.labels_, other),
        "groups": [],
    }
    for g in range(k):
        members = np.flatnonzero(fit.labels_ == g)
        examples = sorted(members, key=lambda i: distances[i])[:4]
        summary["groups"].append(
            {
                "id": g,
                "n": len(members),
                "central_papers": [papers[ids[i]][0] for i in examples],
            }
        )
    target = ROOT / "results"
    (target / "semantic_map.json").write_text(json.dumps(summary, indent=2) + "\n")
    with (target / "semantic_clusters.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["paper_id", "semantic_cluster", "distance"])
        writer.writerows(
            (pid, label, f"{dist:.6f}")
            for pid, label, dist in zip(ids, fit.labels_, distances)
        )


if __name__ == "__main__":
    main()
