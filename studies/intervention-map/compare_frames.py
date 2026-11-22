"""Exploratory contrast of separately drawn explicit-alignment and general-AI samples."""

import json
import math

from scipy.stats import t

from attention import ROOT, paper_tables
from estimate import total, variance
from jev_results import scores


def log_ratio_parts(frame, domain, reviewer, predictions):
    if reviewer == "rubric":
        weight = frame.common_codes.str.contains("W")
        external = frame.common_codes.str.contains("E|H")
    else:
        rows = predictions.reindex(frame.paper_id).set_axis(frame.index)
        if rows.loc[domain].isna().any().any():
            raise ValueError("Missing Jev scores inside the comparison domain")
        weight = rows.weights >= 0.5
        external = (rows.supervision >= 0.5) | (rows.scaffolding >= 0.5)
    weight = (weight & domain).to_numpy(dtype=float)
    external = (external & domain).to_numpy(dtype=float)
    w, e = total(frame, weight), total(frame, external)
    var, df = variance(frame, weight / w - external / e)
    return math.log(w / e), var, df


def main():
    alignment, general = paper_tables()
    predictions, _ = scores("jev_mechanisms.jsonl")
    results = {}
    for reviewer in ("rubric", "jev"):
        a, va, da = log_ratio_parts(
            alignment, alignment.core & alignment.named, reviewer, predictions
        )
        b, vb, db = log_ratio_parts(general, general.core, reviewer, predictions)
        # Independent sample draws. Preserve the within-paper covariance on each side.
        se = math.sqrt(va + vb)
        df = (va + vb) ** 2 / (va**2 / da + vb**2 / db)
        margin = t.ppf(0.975, df) * se
        results[reviewer] = {
            "ratio_of_ratios": math.exp(a - b),
            "ci95": [math.exp(a - b - margin), math.exp(a - b + margin)],
        }
    (ROOT / "results/frame_contrast.json").write_text(
        json.dumps(results, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
