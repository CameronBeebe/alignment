"""Recalculate the independent-frame cross-check without further model calls."""

import json

import pandas as pd

from attention import ROOT

OUT = ROOT / "results"


def summarize():
    frame = pd.read_csv(OUT / "external_radar_frame.csv").set_index(
        "paper_id", verify_integrity=True
    )
    ratings = pd.read_csv(OUT / "external_radar_ratings.csv.gz").set_index(
        "paper_id", verify_integrity=True
    )
    if set(ratings.index) != set(frame.index):
        raise ValueError("Incomplete independent-frame ratings")
    joined = frame.join(ratings, validate="one_to_one")
    result = {
        "unique_papers": len(joined),
        "in_master": int(joined.in_master.sum()),
        "topics": {},
        "model_usage": {},
    }
    for rev in ["jev", "qwen"]:
        result["model_usage"][rev] = {
            "requests": len(joined),
            "usd": float(joined[f"{rev}_usd"].sum()),
        }
    for topic in ["alignment_training", "control_monitoring"]:
        sample = joined[joined[topic]]
        entry = result["topics"][topic] = {
            "all": len(sample),
            "master": int(sample.in_master.sum()),
            "shortlist": int(sample.in_shortlist.sum()),
        }
        for group, g in [
            ("present", sample[sample.in_master]),
            ("absent", sample[~sample.in_master]),
        ]:
            entry[group] = {"n": len(g)}
            weight = {}
            external = {}
            for rev in ["jev", "qwen"]:
                weight[rev] = g[f"{rev}_weights"].ge(0.5)
                external[rev] = (
                    g[[f"{rev}_supervision", f"{rev}_scaffolding"]].ge(0.5).any(axis=1)
                )
                entry[group][rev] = {
                    "weight": int(weight[rev].sum()),
                    "external": int(external[rev].sum()),
                }
            entry[group]["both_reviewers"] = {
                "weight": int((weight["jev"] & weight["qwen"]).sum()),
                "external": int((external["jev"] & external["qwen"]).sum()),
            }
    (OUT / "external_radar_check.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    summarize()
