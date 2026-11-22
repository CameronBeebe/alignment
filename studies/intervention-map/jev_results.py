"""Compare frozen, independent Jev judgments against the two review exercises."""

import json
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, confusion_matrix
from attention import ROOT, estimates, paper_tables, read_csv

OUT = ROOT / "results"


def scores(filename):
    rows = [json.loads(line) for line in (OUT / filename).read_text().splitlines()]
    frame = pd.DataFrame([dict(paper_id=r["paper_id"], **r["scores"]) for r in rows])
    if frame.paper_id.duplicated().any():
        raise ValueError(f"Duplicate paper in {filename}")
    return frame.set_index("paper_id"), sorted({r["model"] for r in rows})


def agreements(truth, probabilities, weight):
    return {
        "average_precision": float(
            average_precision_score(truth, probabilities, sample_weight=weight)
        ),
        "raw_confusion_tn_fp_fn_tp": confusion_matrix(
            truth, probabilities >= 0.5, labels=[False, True]
        )
        .ravel()
        .tolist(),
    }


def main():
    control, versions = scores("jev_checks.jsonl")
    valid = read_csv(ROOT / "data/control_validation.csv").set_index("paper_id")
    if set(valid.index) != set(control.index):
        raise ValueError("Incomplete control audit")
    groups = read_csv(OUT / "control_map.csv").set_index("paper_id").cluster
    weights = groups.loc[valid.index].map(groups.value_counts()) / 15
    c = control.loc[valid.index]
    combined = c[["feedback", "dynamics"]].max(axis=1)
    audit = {}
    for key, truth, score in [
        ("feedback", valid.feedback_loop, c.feedback),
        ("dynamics", valid.dynamics, c.dynamics),
        ("either", valid.feedback_loop | valid.dynamics, combined),
    ]:
        audit[key] = agreements(truth.astype(bool), score, weights)
    data, mechanism_versions = scores("jev_mechanisms.jsonl")
    a, b = paper_tables()
    if set(a.loc[a.core, "paper_id"]) | set(b.paper_id) != set(data.index):
        raise ValueError("Incomplete mechanism audit")
    result = {
        "control_models": versions,
        "mechanism_models": mechanism_versions,
        "n_control": len(control),
        "n_unique_mechanism": len(data),
        "control": audit,
        "mechanisms": {},
    }
    for name, df, mask in [
        ("core", a, a.core),
        ("explicit", a, a.core & a.named),
        ("general_ai", b, b.core),
    ]:
        observed = data.loc[df.loc[mask, "paper_id"]].copy()
        observed.index = df.index[mask]
        agreement = {}
        for col, label in [
            ("weights", "W"),
            ("supervision", "E"),
            ("scaffolding", "H"),
        ]:
            agreement[label] = agreements(
                df.loc[mask, "common_codes"].str.contains(label),
                observed[col],
                (df.N_h / df.n_h)[mask],
            )
        ratios = {}
        for threshold in (0.3, 0.5, 0.7):
            votes = np.where(observed.weights >= threshold, "W", "").astype(object)
            for col, label in [("supervision", "E"), ("scaffolding", "H")]:
                votes += np.where(observed[col] >= threshold, label, "")
            df["jev_codes"] = ""
            df.loc[mask, "jev_codes"] = votes
            ratios[str(threshold)] = estimates(df, mask, code="jev_codes")["W_either"]
        result["mechanisms"][name] = {
            "agreement": agreement,
            "weight_to_external": ratios,
        }
    (OUT / "jev_validation.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
