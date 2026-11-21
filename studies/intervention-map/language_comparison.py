"""Design-weighted language-model subsets of the frozen intervention audits."""

import csv
import gzip
import io
import json
import hashlib
import math
from scipy.stats import t
import pandas as pd
from attention import ROOT, paper_tables
from estimate import ratio_stats, total, variance
from jev_results import scores
from language_scope import FILE

RESULTS = ROOT / "results"


def export_catalog(scope):
    fields = [
        "paper_id",
        "title",
        "year",
        "url",
        "cohorts",
        "named",
        "jev_language_model_focus",
        "literal_llm",
        "family_mention",
        "alignment_harmonized_codes",
        "baseline_review_codes",
        "jev_weights",
        "jev_supervision",
        "jev_scaffolding",
    ]
    destination = RESULTS / "language_model_papers.csv.gz"
    temp = destination.with_suffix(".tmp")
    try:
        with gzip.open(
            RESULTS / "paper_master.csv.gz", "rt", newline=""
        ) as src, temp.open("wb") as raw, gzip.GzipFile(
            fileobj=raw, filename="", mode="wb", mtime=0
        ) as gz, io.TextIOWrapper(
            gz, encoding="utf-8", newline=""
        ) as out:
            writer = csv.DictWriter(
                out, fields, extrasaction="ignore", lineterminator="\n"
            )
            writer.writeheader()
            count = 0
            for row in csv.DictReader(src):
                score = float(row["jev_language_model_focus"])
                if score != scope.at[row["paper_id"], "jev_language_model_focus"]:
                    raise ValueError("Master scope score differs from its source")
                if score >= 0.5:
                    writer.writerow(row)
                    count += 1
            if count != scope.jev_language_model_focus.ge(0.5).sum():
                raise ValueError("Incomplete language-model catalog")
        temp.replace(destination)
    finally:
        temp.unlink(missing_ok=True)


def main():
    scope = pd.read_csv(FILE).set_index("paper_id", verify_integrity=True)
    export_catalog(scope)
    mechanisms, _ = scores("jev_mechanisms.jsonl")
    a, b = paper_tables()
    selections = {
        "semantic_050": scope.jev_language_model_focus.ge(0.5),
        "semantic_030": scope.jev_language_model_focus.ge(0.3),
        "semantic_070": scope.jev_language_model_focus.ge(0.7),
        "literal": scope.literal_llm.eq(1),
        "literal_or_family": (scope.literal_llm.eq(1) | scope.family_mention.eq(1)),
        "all": pd.Series(True, index=scope.index),
    }
    result = {}
    for name, selected in selections.items():
        frames = {}
        influence = {}
        periods = {}
        for key, frame, domain in [
            ("general_ai", b, b.core),
            ("explicit", a, a.core & a.named),
            ("core", a, a.core),
            ("other_wording", a, a.core & ~a.named),
        ]:
            member = frame.paper_id.map(selected)
            if member.isna().any():
                raise ValueError("Missing scope measurement")
            include = domain & member
            jev = mechanisms.reindex(frame.paper_id).set_axis(frame.index)
            if jev.loc[include].isna().any().any():
                raise ValueError("Missing mechanism ratings")
            row = {"selected_n": int(include.sum()), "frame_n": int(domain.sum())}
            for method, w, e in [
                (
                    "rubric",
                    frame.common_codes.str.contains("W"),
                    frame.common_codes.str.contains("E|H"),
                ),
                (
                    "jev",
                    jev.weights.ge(0.5),
                    jev[["supervision", "scaffolding"]].max(axis=1).ge(0.5),
                ),
            ]:
                wx, ex = (w & include).astype(int), (e & include).astype(int)
                est = row[method] = ratio_stats(frame, wx, ex)
                if key in ("explicit", "other_wording"):
                    influence[key, method] = wx / est["W"] - ex / est["E"]
                if name == "semantic_050" and key in ("explicit", "other_wording"):
                    for era, era_mask in [
                        ("Nov 2021–Dec 2024", frame.year.lt(2025)),
                        ("Jan 2025–Oct 2026", frame.year.ge(2025)),
                    ]:
                        entry = periods.setdefault(key, {}).setdefault(
                            era, {"reviewed": int((include & era_mask).sum())}
                        )
                        entry[method] = ratio_stats(frame, wx * era_mask, ex * era_mask)
                if method == "rubric":
                    denominator = total(frame, include)
                    row["rubric_shares"] = {
                        k: total(frame, include & condition) / denominator
                        for k, condition in [
                            ("weights_only", w & ~e),
                            ("external_only", e & ~w),
                            ("both", w & e),
                            ("neither", ~w & ~e),
                        ]
                    }
            frames[key] = row
        contrast = {}
        for method in ("rubric", "jev"):
            rr = (
                frames["explicit"][method]["ratio"]
                / frames["other_wording"][method]["ratio"]
            )
            var, df = variance(
                a, influence["explicit", method] - influence["other_wording", method]
            )
            margin = t.ppf(0.975, df) * math.sqrt(var)
            contrast[method] = {
                "ratio_of_ratios": rr,
                "ci95": [rr * math.exp(-margin), rr * math.exp(margin)],
            }
        result[name] = {
            "master_n": int(selected.sum()),
            "frames": frames,
            "explicit_vs_other": contrast,
        }
        if periods:
            result[name]["periods"] = periods
    focus = selections["semantic_050"]
    result["capture"] = {
        "semantic_without_literal": int((focus & ~selections["literal"]).sum()),
        "semantic_without_literal_or_family": int(
            (focus & ~selections["literal_or_family"]).sum()
        ),
        "wording_or_family_outside_semantic": int(
            (~focus & selections["literal_or_family"]).sum()
        ),
    }
    review = pd.read_csv(ROOT / "data/language_scope_review.csv").set_index(
        "paper_id", verify_integrity=True
    )
    membership = (
        pd.read_csv(RESULTS / "paper_master.csv.gz", usecols=["paper_id", "cohorts"])
        .set_index("paper_id")
        .cohorts.str.split("|", regex=False)
    )
    for (sample, stratum), g in review.groupby(["sample", "wording_stratum"]):
        pool = membership[membership.map(lambda tags: sample in tags)].index
        match = selections["literal_or_family"].reindex(pool).eq(stratum == "mention")
        draw = sorted(
            pool[match],
            key=lambda pid: hashlib.sha256(
                ("language-review-v1/" + pid).encode()
            ).digest(),
        )[:10]
        if set(draw) != set(g.index):
            raise ValueError("Scope validation draw differs")
    definite = review[review.focus_review.ne("unclear")]
    pos = definite.focus_review.eq("1")
    result["review_check"] = {
        "reviewed": len(review),
        "unclear": len(review) - len(definite),
        "positive_reference": int(pos.sum()),
    }
    for name in ("semantic_050", "literal", "literal_or_family"):
        called = selections[name].loc[definite.index]
        result["review_check"][name] = {
            "tp": int((called & pos).sum()),
            "fp": int((called & ~pos).sum()),
            "fn": int((~called & pos).sum()),
            "tn": int((~called & ~pos).sum()),
        }
    (RESULTS / "language_comparison.json").write_text(
        json.dumps(result, indent=2, allow_nan=False) + "\n"
    )


if __name__ == "__main__":
    main()
