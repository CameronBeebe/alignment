"""Design-weighted full-paper estimates across the frozen language-model audit domains."""

import json
import math

import pandas as pd
from scipy.stats import t

from attention import ROOT, paper_tables
from estimate import ratio_stats, total, variance
from fulltext_questions import GROUPS
from fulltext_sources import cohort

OUT = ROOT / "results"


def ratio_change(r1, r2, var, df):
    value = r1 / r2
    margin = t.ppf(0.975, df) * math.sqrt(var)
    return {
        "ratio_of_ratios": value,
        "ci95": [value * math.exp(-margin), value * math.exp(margin)],
    }


def summarize():
    tables = [
        pd.read_csv(OUT / n)
        for n in ["fulltext_measures.csv", "fulltext_comparator_measures.csv"]
    ]
    d = pd.concat(tables, ignore_index=True).set_index(
        "paper_id", verify_integrity=True
    )
    expected = set(cohort().paper_id) | set(cohort("language-comparators").paper_id)
    if set(d.index) != expected:
        raise ValueError("Missing eligible paper IDs")
    paired = d[d.text_sha256.notna()]
    if paired.filter(regex="^(jev|qwen)_(abstract|paper)_").isna().any().any():
        raise ValueError("Missing paired scores")
    a, b = paper_tables()
    frames = {
        "explicit": (a, a.core & a.named),
        "other": (a, a.core & ~a.named),
        "combined": (a, a.core),
        "general": (b, b.core),
    }
    result = {
        "eligible": len(d),
        "full": len(paired),
        "pages": int(paired.pages.sum()),
        "domains": {},
        "contrasts": {},
    }
    influence = {}
    for key, (frame, domain) in frames.items():
        data = paired.reindex(frame.paper_id).set_axis(frame.index)
        member = domain & data.text_sha256.notna()
        row = result["domains"][key] = {
            "selected": int((domain & frame.paper_id.isin(expected)).sum()),
            "paired": int(member.sum()),
            "ratings": {},
        }
        denom = total(frame, member)
        for basis in ("abstract", "paper"):
            for reviewer in ("jev", "qwen"):
                prefix = f"{reviewer}_{basis}_"
                w = member & data[prefix + "weights"].ge(0.5)
                e = member & data[[prefix + "supervision", prefix + "scaffolding"]].max(
                    axis=1
                ).ge(0.5)
                est = ratio_stats(frame, w, e)
                row["ratings"][reviewer + "_" + basis] = est
                influence[key, reviewer, basis] = w / est["W"] - e / est["E"]
                est["shares"] = {
                    label: total(frame, mask) / denom
                    for label, mask in [
                        ("weight_only", w & ~e),
                        ("external_only", e & ~w),
                        ("both", w & e),
                        ("neither", member & ~w & ~e),
                    ]
                }
        row["paper_reviewer_agreement"] = {}
        for label, mechanisms in [("weights", ["weights"]), ("external", ["supervision", "scaffolding"])]:
            votes = {
                rev: data[[rev + "_paper_" + q for q in mechanisms]].max(axis=1).ge(0.5)
                for rev in ("jev", "qwen")
            }
            row["paper_reviewer_agreement"][label] = {
                "agree": int((member & votes["jev"].eq(votes["qwen"])).sum()),
                "jev_only": int((member & votes["jev"] & ~votes["qwen"]).sum()),
                "qwen_only": int((member & votes["qwen"] & ~votes["jev"]).sum()),
            }
        retained = member & ~frame.paper_id.isin(
            ["arxiv:2608.01629", "arxiv:2509.01412"]
        )
        row["excluding_two_known_withdrawals"] = {}
        for rev in ("jev", "qwen"):
            prefix = rev + "_paper_"
            w = retained & data[prefix + "weights"].ge(0.5)
            e = retained & data[[prefix + "supervision", prefix + "scaffolding"]].max(
                axis=1
            ).ge(0.5)
            row["excluding_two_known_withdrawals"][rev] = ratio_stats(frame, w, e)
        row["jev_full_paper_thresholds"] = {}
        for cutoff in (0.3, 0.5, 0.7):
            w = member & data.jev_paper_weights.ge(cutoff)
            e = member & data[["jev_paper_supervision", "jev_paper_scaffolding"]].max(
                axis=1
            ).ge(cutoff)
            row["jev_full_paper_thresholds"][str(cutoff)] = ratio_stats(frame, w, e)
        row["jev_full_paper_features"] = {}
        for items in GROUPS.values():
            for q in items:
                positive = member & data["jev_paper_" + q].ge(0.5)
                row["jev_full_paper_features"][q] = {
                    "n": int(positive.sum()),
                    "weighted_share": total(frame, positive) / denom,
                }
    for rev in ("jev", "qwen"):
        r = result["domains"]
        left = r["explicit"]["ratings"][rev + "_paper"]["ratio"]
        v, df = variance(
            a, influence["explicit", rev, "paper"] - influence["other", rev, "paper"]
        )
        result["contrasts"][rev + "_explicit_over_other"] = ratio_change(
            left, r["other"]["ratings"][rev + "_paper"]["ratio"], v, df
        )
        # The audit draws used separate, independent designs.
        v1, d1 = variance(a, influence["explicit", rev, "paper"])
        v2, d2 = variance(b, influence["general", rev, "paper"])
        df = (v1 + v2) ** 2 / (v1**2 / d1 + v2**2 / d2)
        result["contrasts"][rev + "_explicit_over_general"] = ratio_change(
            left, r["general"]["ratings"][rev + "_paper"]["ratio"], v1 + v2, df
        )
    requests = pd.read_csv(OUT / "fulltext_comparator_requests.csv")
    result["new_run"] = {}
    for name, rr in requests.groupby("reviewer"):
        result["new_run"][name] = {
            "requests": len(rr),
            "input_tokens": int(rr.input_tokens.sum()),
            "long_context": int(rr.long_context.sum()),
            "usd": float(
                rr.input_tokens.sum() * 0.042 / 1e6
                if name == "jev"
                else rr.reported_cost_usd.sum()
            ),
        }
    (OUT / "fulltext_comparison.json").write_text(
        json.dumps(result, indent=2, allow_nan=False) + "\n"
    )
    return result


if __name__ == "__main__":
    summarize()
