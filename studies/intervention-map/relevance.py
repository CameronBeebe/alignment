"""Build a discovery shortlist. The audit-based estimates do not use model probabilities."""

import numpy as np
import pandas as pd
from scipy.sparse import hstack
from sklearn.feature_extraction import DictVectorizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold
from search import dump


def shortlist(df, data, out):
    audits = pd.read_csv(data / "audit_draw.csv").merge(
        pd.read_csv(data / "review.csv"), on="review_id", validate="one_to_one"
    )
    idx = pd.Index(df.paper_id).get_indexer(audits.paper_id)
    if (idx < 0).any():
        raise ValueError("Mismatch between corpus and review")
    y = audits.scope.eq("core").to_numpy()
    samplew = (audits.N_h / audits.n_h).to_numpy()
    # The unsupervised vocabulary sees this frozen corpus. No review labels enter these features.
    vector = TfidfVectorizer(
        ngram_range=(1, 2),
        min_df=3,
        max_features=40000,
        stop_words="english",
        sublinear_tf=True,
    )
    X = vector.fit_transform(df.title + " " + df.title + " " + df.abstract)
    tags = DictVectorizer().fit_transform(
        [
            dict.fromkeys([*lanes, *facets, group], 0.32)
            for lanes, facets, group in zip(df.lanes, df.facets, df.auto_group)
        ]
    )
    X = hstack([X, tags], format="csr")

    def fit(i):
        return LogisticRegression(C=8, max_iter=500).fit(
            X[idx[i]], y[i], sample_weight=samplew[i] / samplew[i].mean()
        )

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=72613)
    held = np.zeros(len(idx))
    for tr, test in cv.split(idx, y):
        held[test] = fit(tr).predict_proba(X[idx[test]])[:, 1]
    scores = fit(np.arange(len(idx))).predict_proba(X)[:, 1]
    cutoff = 0.80
    flagged = held >= cutoff
    tp = samplew[flagged & y].sum()
    result = dict(
        cutoff=cutoff,
        heldout_n=len(y),
        heldout_flagged=int(flagged.sum()),
        heldout_correct_among_flagged=int((flagged & y).sum()),
        weighted_heldout_precision=(
            float(tp / samplew[flagged].sum()) if flagged.any() else None
        ),
        weighted_heldout_recall=float(tp / samplew[y].sum()),
        weighted_heldout_auc=float(roc_auc_score(y, held, sample_weight=samplew)),
        weighted_average_precision=float(
            average_precision_score(y, held, sample_weight=samplew)
        ),
    )
    selected = scores >= cutoff
    selected[idx] = y
    label = np.full(len(df), "model shortlist", dtype=object)
    label[idx] = "reviewed"
    mechanisms = np.full(len(df), "", dtype=object)
    mechanisms[idx] = audits.mechanisms
    cols = [
        "paper_id",
        "title",
        "authors",
        "year",
        "url",
        "auto_group",
        "cluster",
        "lanes",
        "facets",
        "metrics",
        "sources",
    ]
    sub = df[cols].assign(
        selection=label, reviewed_mechanisms=mechanisms, core_score=scores.round(4)
    )
    for key in ["lanes", "facets", "metrics", "sources"]:
        sub[key] = sub[key].map(lambda values: " | ".join(values))
    sub.loc[selected].sort_values(["selection", "core_score"], ascending=False).to_csv(
        out / "alignment_papers.csv", index=False
    )
    result["selected_total"] = int(selected.sum())
    dump(out / "relevance_validation.json", result)
