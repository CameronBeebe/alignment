"""Compute globally comparable semantic features for every work in the master."""

import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score, silhouette_score
from threadpoolctl import threadpool_limits

from cybernetics_map import QUERIES
from master_records import ROOT, master_records
from semantic_map import MODEL, REV, encode, records as alignment_records


def vectors_for(records, cache, seed):
    ids = list(records)
    checksum = hashlib.sha256(
        json.dumps(
            [MODEL, REV, 160, "passage: ", list(records.items())], ensure_ascii=False
        ).encode()
    ).hexdigest()
    if cache.exists():
        with np.load(cache) as arrays:
            if str(arrays["signature"]) != checksum or arrays["ids"].tolist() != ids:
                raise ValueError("Embedding cache signature mismatch")
            return arrays["x"]
    saved = {}
    if seed:
        original = alignment_records()
        with np.load(seed) as arrays:
            if arrays["ids"].tolist() != list(original):
                raise ValueError("Invalid shortlist seed")
            saved = {
                pid: v
                for pid, v in zip(arrays["ids"].tolist(), arrays["vectors"])
                if records.get(pid) == original[pid]
            }
    missing = [pid for pid in ids if pid not in saved]
    print(f"Encoding {len(missing)} additional papers", flush=True)
    if missing:
        saved.update(
            zip(missing, encode([". ".join(records[i]) for i in missing], "passage: "))
        )
    x = np.stack([saved[i] for i in ids])
    np.savez(cache, signature=checksum, ids=ids, x=x)
    return x


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vectors", type=Path, required=True)
    parser.add_argument("--seed-vectors", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    records, roles = master_records()
    ids = list(records)
    x = vectors_for(records, args.vectors, args.seed_vectors)
    if not np.allclose(np.linalg.norm(x, axis=1), 1, atol=1e-4):
        raise ValueError("Expected unit embeddings")
    fit_ids = np.array([i for i, pid in enumerate(ids) if "candidate" in roles[pid]])
    queries = encode(list(QUERIES.values()), "query: ")
    with threadpool_limits(4):
        quality = {}
        fits = {}
        for k in (6, 10, 16, 24):
            fit = KMeans(n_clusters=k, n_init=5, random_state=17).fit(x[fit_ids])
            quality[k] = float(
                silhouette_score(
                    x[fit_ids],
                    fit.labels_,
                    metric="cosine",
                    sample_size=2000,
                    random_state=17,
                )
            )
            fits[k] = fit
        k = max(quality, key=quality.get)
        best = fits[k]
        alternate = KMeans(n_clusters=k, n_init=5, random_state=43).fit_predict(
            x[fit_ids]
        )
        dist = best.transform(x)
        order = np.argsort(dist, axis=1, kind="stable")
        scores = x @ queries.T
        nearest = []
        for start in range(0, len(ids), 128):
            similarities = x[start : start + 128] @ x.T
            ri = np.arange(len(similarities))
            similarities[ri, start + ri] = -np.inf
            neighbor = np.argmax(similarities, axis=1)
            nearest.extend(zip(neighbor, np.clip(similarities[ri, neighbor], -1, 1)))
    groups = []
    for g in range(k):
        members = fit_ids[order[fit_ids, 0] == g]
        medoids = members[np.argsort(dist[members, g])[:5]]
        groups.append(
            {
                "id": g,
                "candidate_members": len(members),
                "central_papers": [
                    {"paper_id": ids[i], "title": records[ids[i]][0]} for i in medoids
                ],
            }
        )
    (ROOT / "results/master_topics.json").write_text(
        json.dumps(
            {
                "model": MODEL,
                "revision": REV,
                "k": k,
                "silhouettes": quality,
                "candidate_fit_n": len(fit_ids),
                "assigned_n": len(ids),
                "seed_ari": adjusted_rand_score(best.labels_, alternate),
                "queries": QUERIES,
                "topics": groups,
            },
            indent=2,
        )
        + "\n"
    )
    with args.output.open("w", newline="") as f:
        out = csv.writer(f)
        out.writerow(
            [
                "paper_id",
                "candidate_topic",
                "topic_distance_l2",
                "runner_up_topic",
                "runner_up_distance_l2",
                "topic_distance_margin",
                "nearest_paper_id",
                "nearest_cosine",
                "nearest_cosine_distance",
                *["e5_cosine_" + k for k in QUERIES],
            ]
        )
        for i, (pid, (near, cos)) in enumerate(zip(ids, nearest)):
            a, b = order[i, :2]
            u, v = dist[i, [a, b]]
            out.writerow(
                [
                    pid,
                    int(a),
                    f"{u:.6f}",
                    int(b),
                    f"{v:.6f}",
                    f"{v-u:.6f}",
                    ids[near],
                    f"{cos:.6f}",
                    f"{1-cos:.6f}",
                    *[f"{s:.6f}" for s in scores[i]],
                ]
            )


if __name__ == "__main__":
    main()
