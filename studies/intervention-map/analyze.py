"""Offline workflow. Analyze a frozen dataset or explicitly create a new review draw."""

import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import re
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer, ENGLISH_STOP_WORDS
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import normalize
from threadpoolctl import threadpool_limits
from rules import measure, norm
from snapshot import archive_path
from search import folded, dump

SEED = 72613


def prepare(data):
    with gzip.open(archive_path(data), "rt") as f:
        rows = [json.loads(line) for line in f]
    df = pd.DataFrame(rows).sort_values("paper_id").reset_index(drop=True)
    measured = pd.DataFrame([measure(t, a) for t, a in zip(df.title, df.abstract)])
    df = pd.concat([df, measured], axis=1)
    df["year"] = df.month.str[:4].astype(int)
    df["era"] = np.where(df.year < 2025, "early", "late")
    df["stratum"] = (
        df.auto_group + "|" + np.where(df.generative, "gen", "other") + "|" + df.era
    )
    return df


def draw(df, data, budget):
    groups = df.groupby("stratum").size().sort_index()
    if budget < 2 * len(groups):
        raise ValueError("Need at least two draws per non-singleton stratum")
    n = np.minimum(groups, 2)
    # Fixed equal/proportion mixture with a two-per-cell floor.
    targets = budget * (0.80 * groups / groups.sum() + 0.20 / len(groups))
    while n.sum() < min(budget, len(df)):
        candidates = targets[n < groups] - n[n < groups]
        n[candidates.idxmax()] += 1
    random = np.random.default_rng(SEED)
    selected = []
    for h, g in df.groupby("stratum", sort=True):
        rows = g.iloc[random.choice(len(g), int(n[h]), replace=False)].copy()
        rows["N_h"] = len(g)
        rows["n_h"] = len(rows)
        selected.append(rows)
    review = (
        pd.concat(selected)
        .sort_values("paper_id")
        .sample(frac=1, random_state=SEED)
        .reset_index(drop=True)
    )
    review.insert(0, "review_id", np.arange(1, len(review) + 1))
    review[["review_id", "paper_id", "stratum", "N_h", "n_h"]].to_csv(
        data / "audit_draw.csv", index=False
    )
    dump(
        data / "audit_design.json",
        dict(
            seed=SEED,
            n=len(review),
            population=len(df),
            frame_sha256=hashlib.sha256(
                archive_path(data).read_bytes()
            ).hexdigest(),
        ),
    )
    print("Review draw", len(review), "papers")


def topics(df, out):
    stop = sorted(
        set(ENGLISH_STOP_WORDS)
        | set(
            "model models paper propose proposed method methods approach using based results demonstrate show task tasks performance existing recent work problem study framework training learning language large llm llms introduce evaluate evaluation experiments datasets dataset".split()
        )
    )
    vector = TfidfVectorizer(
        stop_words=stop,
        ngram_range=(1, 2),
        min_df=3,
        max_df=0.80,
        max_features=24000,
        sublinear_tf=True,
        strip_accents="unicode",
        dtype=np.float32,
    )
    text = (df.title + ". " + df.title + ". " + df.abstract).map(norm)
    X = vector.fit_transform(text)
    words = vector.get_feature_names_out()
    svd = TruncatedSVD(n_components=min(48, X.shape[1] - 1), random_state=SEED)
    Z = normalize(svd.fit_transform(X))
    trials = {}
    for k in (8, 12, 16):
        km = KMeans(n_clusters=k, n_init=6, random_state=SEED).fit(Z)
        score = silhouette_score(
            Z,
            km.labels_,
            sample_size=min(2500, len(df)),
            random_state=SEED,
            metric="cosine",
        )
        trials[k] = (float(score), km)
    k = max(trials, key=lambda k: trials[k][0])
    km = trials[k][1]
    summaries = []
    for c in range(k):
        idx = np.flatnonzero(km.labels_ == c)
        centroid = np.asarray(X[idx].mean(axis=0)).ravel()
        terms = words[np.argsort(-centroid)[:12]].tolist()
        nearest = idx[
            np.argsort(np.linalg.norm(Z[idx] - km.cluster_centers_[c], axis=1))[:3]
        ]
        summaries.append(
            dict(
                cluster=c,
                size=len(idx),
                terms=terms,
                examples=df.iloc[nearest].paper_id.tolist(),
            )
        )
    dump(
        out / "topics.json",
        dict(
            chosen_k=k,
            silhouette={k: s for k, (s, _) in trials.items()},
            variance_fraction=float(svd.explained_variance_ratio_.sum()),
            clusters=summaries,
        ),
    )
    return km.labels_


def venue_check(df, data, out):
    catalog = pd.read_json(data / "l4dc_catalog.json")
    catalog = catalog[~catalog.title.str.fullmatch("Preface", case=False)].copy()
    candidates = {
        folded(r["title"]): i
        for i, variants in zip(df.paper_id, df.records)
        for r in variants
    }
    catalog["title_match_candidate"] = catalog.title.map(
        lambda t: candidates.get(folded(t), "")
    )
    catalog["safety_title"] = catalog.title.str.contains(
        r"\bsafe\b|\bsafety\b|shield|barrier (?:function|certificate)|constraint satisfaction",
        case=False,
    )
    catalog.to_csv(out / "l4dc_coverage.csv", index=False)
    return {
        "proceedings_titles": len(catalog),
        "safety_titles": int(catalog.safety_title.sum()),
        "safety_titles_in_candidates": int(
            (catalog.safety_title & catalog.title_match_candidate.ne("")).sum()
        ),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "mode", nargs="?", choices=["analyze", "draw", "stats"], default="analyze"
    )
    ap.add_argument("--data", type=Path, default=Path("data"))
    ap.add_argument("--out", type=Path, default=Path("results"))
    ap.add_argument("--budget", default=360, type=int)
    args = ap.parse_args()
    if args.mode == "stats":
        from estimate import estimate

        df = pd.read_csv(args.out / "papers.csv", keep_default_na=False)
        for key in ("sources", "lanes", "facets"):
            df[key] = df[key].map(lambda value: value.split(" | ") if value else [])
        df["era"] = np.where(df.year < 2025, "early", "late")
        estimate(df, args.data, args.out)
        return
    df = prepare(args.data)
    if args.mode == "draw":
        if (args.data / "audit_draw.csv").exists():
            raise SystemExit(
                "Draw exists. Choose a new --data directory for a new audit."
            )
        draw(df, args.data, args.budget)
        return
    args.out.mkdir(parents=True, exist_ok=True)
    with threadpool_limits(limits=2):
        df["cluster"] = topics(df, args.out)
    venue = (
        venue_check(df, args.data, args.out)
        if (args.data / "l4dc_catalog.json").exists()
        else None
    )
    cols = [
        "paper_id",
        "title",
        "authors",
        "year",
        "month",
        "url",
        "doi",
        "sources",
        "lanes",
        "auto_group",
        "named",
        "generative",
        "weight_hit",
        "external_hit",
        "inference_hit",
        "facets",
        "metrics",
        "cluster",
    ]
    flat = df[cols].copy()
    for c in ["sources", "lanes", "facets", "metrics"]:
        flat[c] = flat[c].map(lambda x: " | ".join(x))
    flat.to_csv(args.out / "papers.csv", index=False)
    df.groupby(["year", "auto_group"]).size().unstack(fill_value=0).to_csv(
        args.out / "year_by_rule.csv"
    )
    dump(
        args.out / "descriptive.json",
        dict(
            n=len(df),
            source_combinations=dict(Counter("+".join(x) for x in df.sources)),
            methods=dict(Counter(df.auto_group)),
            metrics=dict(Counter(k for lst in df.metrics for k in lst)),
            l4dc=venue,
        ),
    )
    if (args.data / "review.csv").exists():
        from estimate import estimate

        estimate(df, args.data, args.out)
        from relevance import shortlist

        with threadpool_limits(limits=2):
            shortlist(df, args.data, args.out)
    print(args.out, len(df), "papers")


if __name__ == "__main__":
    main()
