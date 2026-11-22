"""Check the full-table Jev instrument against separate, frozen abstract reviews."""

import hashlib
import json

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score

from master_records import ROOT


def agreement(y, scores, weights):
    y = np.asarray(y, dtype=bool)
    scores = np.asarray(scores, dtype=float)
    weights = np.asarray(weights, dtype=float)
    if not np.isfinite(scores).all():
        raise ValueError("Missing reviewed score")
    calls = scores >= 0.5

    def count(mask):
        return int(mask.sum())

    def share(mask, base):
        return float(weights[mask].sum() / weights[base].sum()) if base.any() else None

    return {
        "n": len(y),
        "positive_reference": count(y),
        "tn": count(~calls & ~y),
        "fp": count(calls & ~y),
        "fn": count(~calls & y),
        "tp": count(calls & y),
        "precision_050": share(calls & y, calls),
        "recall_050": share(calls & y, y),
        "specificity_050": share(~calls & ~y, ~y),
        "average_precision": (
            float(average_precision_score(y, scores, sample_weight=weights))
            if y.any()
            else None
        ),
    }


def main():
    d = pd.read_csv(ROOT / "results/paper_master.csv.gz", keep_default_na=False)
    result = {}
    a = d[d.alignment_review_scope.ne("")]
    wa = a.alignment_N_h.astype(float) / a.alignment_n_h.astype(float)
    result["alignment_scope"] = agreement(
        a.alignment_review_scope.eq("core"), a.jev_alignment_relevance, wa
    )
    for frame, codes, N, n in [
        ("core", "alignment_harmonized_codes", "alignment_N_h", "alignment_n_h"),
        ("general_ai_audit", "baseline_review_codes", "baseline_N_h", "baseline_n_h"),
    ]:
        t = d[d[codes].ne("")]
        w = t[N].astype(float) / t[n].astype(float)
        result[frame] = {
            k: agreement(t[codes].str.contains(letter), t["jev_" + k], w)
            for k, letter in [
                ("weights", "W"),
                ("supervision", "E"),
                ("scaffolding", "H"),
            ]
        }
    t = d[d.control_review_feedback.ne("")]
    lens = d[d.control_map_topic.ne("")].groupby("control_map_topic").size()
    w = t.control_map_topic.map(lens) / 15
    result["control_review"] = {
        k: agreement(t[v].astype(int), t["jev_" + k], w)
        for k, v in [
            ("feedback", "control_review_feedback"),
            ("dynamics", "control_review_dynamics"),
        ]
    }
    # Labels below come from a separate read of public metadata with the Jev scores hidden.
    r = pd.read_csv(ROOT / "data/master_role_review.csv").set_index("paper_id")
    groups = d.cohorts.str.split("|", regex=False)
    for frame, mask in [
        ("general_ai", groups.map(lambda g: "general_ai" in g)),
        ("candidate", groups.map(lambda g: "candidate" in g and "general_ai" not in g)),
    ]:
        expected = sorted(
            d.loc[mask, "paper_id"],
            key=lambda pid: hashlib.sha256(
                ("descriptive-roles-audit-01/" + pid).encode()
            ).digest(),
        )[:16]
        if set(expected) != set(r[r.frame == frame].index):
            raise ValueError("Role audit IDs differ from the fixed hash draw")
    t = d.set_index("paper_id").loc[r.index]
    result["descriptive_roles_32"] = {
        k: agreement(r[k], t["jev_" + k], np.ones(len(t)))
        for k in ["evaluation", "theory", "data_resources", "governance"]
    }
    # Compare all papers common to the two instruments, preserving the frozen audits separately.
    audits = {}
    for file in ["jev_mechanisms.jsonl", "jev_checks.jsonl", "jev_cluster_audit.jsonl"]:
        for line in (ROOT / "results" / file).read_text().splitlines():
            row = json.loads(line)
            audits.setdefault(row["paper_id"], row["scores"])
    old = pd.DataFrame.from_dict(audits, orient="index")
    current = d.set_index("paper_id").loc[old.index]
    result["five_vs_ten_question_instruments"] = {
        k: {
            "n": len(old),
            "mean_absolute_change": float((old[k] - current["jev_" + k]).abs().mean()),
            "threshold_flips": int(
                (old[k].ge(0.5) != current["jev_" + k].ge(0.5)).sum()
            ),
        }
        for k in old.columns
    }
    (ROOT / "results/master_validation.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
