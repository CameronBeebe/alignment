"""Stratified finite-population inference. Measurements from the review only."""

import hashlib
import json
import math
import numpy as np
import pandas as pd
from scipy.stats import t
from snapshot import archive_path
from search import dump


def total(d, x):
    return float(np.dot(d.N_h / d.n_h, np.asarray(x, dtype=float)))


def variance(d, x):
    """SRS without replacement per stratum, including covariance via linear contrasts."""
    tmp = d[["stratum", "N_h", "n_h"]].assign(x=np.asarray(x, dtype=float))
    cells = tmp.groupby("stratum").agg(
        N=("N_h", "first"), n=("n_h", "first"), s2=("x", "var")
    )
    cells = cells[cells.n < cells.N]
    if (cells.n < 2).any():
        raise ValueError("Noncertainty stratum has fewer than two reviews")
    v = cells.N**2 * (1 - cells.n / cells.N) * cells.s2 / cells.n
    vtot = float(v.sum())
    df = vtot**2 / float((v**2 / (cells.n - 1)).sum()) if vtot else math.inf
    return vtot, df


def contrast(d, x, y, ratio=1):
    diff = x - ratio * y
    v, df = variance(d, diff)
    delta = total(d, diff)
    return {
        "difference": delta,
        "p_two_sided": float(2 * t.sf(abs(delta) / math.sqrt(v), df)) if v else None,
    }


def ratio_stats(d, x, y):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    W, E = total(d, x), total(d, y)
    result = dict(W=W, E=E, observed_W=float(x.sum()), observed_E=float(y.sum()))
    if W <= 0 or E <= 0:
        return {**result, "ratio": None, "ci95": None}
    v, df = variance(d, x / W - y / E)
    margin = t.ppf(0.975, df) * math.sqrt(v)
    return {
        **result,
        "ratio": W / E,
        "ci95": [W / E * math.exp(-margin), W / E * math.exp(margin)],
        "equality": contrast(d, x, y),
        "twofold": contrast(d, x, y, 2),
    }


def estimate(frame, data, out):
    design = json.loads((data / "audit_design.json").read_text())
    if (
        design["frame_sha256"]
        != hashlib.sha256(archive_path(data).read_bytes()).hexdigest()
    ):
        raise ValueError("Frozen frame differs from the audited snapshot")
    draws = pd.read_csv(data / "audit_draw.csv")
    lab = pd.read_csv(data / "review.csv", keep_default_na=False)
    if set(draws.review_id) != set(lab.review_id):
        raise ValueError("Audit incomplete")
    d = draws.merge(lab, on="review_id", validate="one_to_one").merge(
        frame.drop(columns="stratum", errors="ignore"),
        on="paper_id",
        validate="one_to_one",
    )
    if (
        len(d) != len(draws)
        or not (d.groupby("stratum").size() == d.groupby("stratum").n_h.first()).all()
    ):
        raise ValueError("Draw and corpus disagree")
    if d.groupby("stratum").N_h.first().sum() != len(frame):
        raise ValueError("Population has changed; repeat the draw for a new study")
    if not set(d.scope) <= set(["core", "adjacent", "outside", "unclear"]):
        raise ValueError("Unknown scope")
    for f in "WEI":
        d[f] = d.mechanisms.str.contains(f)
    if not d.mechanisms.str.fullmatch(r"W?E?I?|none").all():
        raise ValueError("Unknown mechanism")
    core = d.scope.eq("core")
    broad = core | d.scope.eq("adjacent")
    W = d.W.to_numpy(float)
    E = d.E.to_numpy(float)
    I = d.I.to_numpy(float)
    tests = {}

    def add(name, domain, x=W, y=E):
        tests[name] = ratio_stats(d, domain * x, domain * y)

    add("core", core)
    add("core_plus_adjacent", broad)
    add("core_external_or_steering", core, W, np.maximum(E, I))
    add(
        "core_external_steering_or_theory_mention",
        core,
        W,
        np.maximum(
            np.maximum(E, I), d.facets.map(lambda x: "systems/control theory" in x)
        ),
    )
    add(
        "core_lexical_only",
        core & d.lanes.map(lambda x: any(not v.startswith("feedback_") for v in x)),
    )
    add("core_exclusive", core, W * (1 - E), E * (1 - W))
    add("core_split_hybrid", core, W * (1 - 0.5 * E), E * (1 - 0.5 * W))
    add("core_named", core & d.named)
    add("core_without_named", core & ~d.named)
    add("core_goal_lane", core & d.lanes.map(lambda x: "goal" in x))
    add("core_arxiv", core & d.sources.map(lambda x: "arxiv" in x))
    add("core_acl", core & d.sources.map(lambda x: "acl" in x))
    for period in ["early", "late"]:
        add("core_" + period, core & d.era.eq(period))
    for year in sorted(d.year.unique()):
        add("core_" + str(year), core & d.year.eq(year))
    # Tests of a change in the ratio use the paired influence function across both periods.
    early = core & d.era.eq("early")
    late = core & d.era.eq("late")
    a, b = tests["core_early"], tests["core_late"]
    change = None
    if a["ratio"] and b["ratio"]:
        v, df = variance(
            d, late * (W / b["W"] - E / b["E"]) - early * (W / a["W"] - E / a["E"])
        )
        delta = math.log(b["ratio"] / a["ratio"])
        m = t.ppf(0.975, df) * math.sqrt(v)
        change = dict(
            ratio_of_ratios=math.exp(delta),
            ci95=[math.exp(delta - m), math.exp(delta + m)],
            p_two_sided=float(2 * t.sf(abs(delta) / math.sqrt(v), df)) if v else None,
        )
    summary = dict(
        review_n=len(d),
        scope_raw=d.scope.value_counts().to_dict(),
        scope_est={s: total(d, d.scope.eq(s)) for s in sorted(d.scope.unique())},
        estimates=tests,
        period_change=change,
        core_overlapping_totals={f: total(d, core & d[f]) for f in "WEI"},
        core_other=total(d, core & d.mechanisms.eq("none")),
        core_hybrid_WE=total(d, core & d.W & d.E),
    )
    dump(out / "inference.json", summary)
    cols = [
        "review_id",
        "paper_id",
        "title",
        "url",
        "scope",
        "mechanisms",
        "stratum",
        "N_h",
        "n_h",
        "auto_group",
    ]
    d[cols].sort_values("review_id").to_csv(out / "reviewed_papers.csv", index=False)
    d.loc[core, cols].sort_values("paper_id").to_csv(
        out / "reviewed_alignment.csv", index=False
    )
    weights = d.N_h / d.n_h
    validation = {}
    for label, flag in [
        ("weights", d.weight_hit.ne("")),
        ("external", d.external_hit.ne("")),
        ("inference", d.inference_hit.ne("")),
    ]:
        y = core & d[{"weights": "W", "external": "E", "inference": "I"}[label]]
        tp = weights[y & flag].sum()
        validation[label] = dict(
            precision=float(tp / weights[flag].sum()) if flag.any() else None,
            recall_in_frame=float(tp / weights[y].sum()) if y.any() else None,
        )
    dump(out / "rule_validation.json", validation)
