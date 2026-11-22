"""Check full-paper counts, cross-frame estimates and the separate coverage sample."""

import json
import unittest

import numpy as np
import pandas as pd

from attention import ROOT, paper_tables
from fulltext_alphaxiv import coverage_draw


class ComparisonTest(unittest.TestCase):
    def test_domains_and_source_identity(self):
        out = ROOT / "results"
        result = json.loads((out / "fulltext_comparison.json").read_text())
        comp = pd.read_csv(out / "fulltext_comparator_measures.csv").set_index(
            "paper_id", verify_integrity=True
        )
        ledger = pd.read_csv(out / "fulltext_comparator_requests.csv")
        headline = pd.read_csv(out / "fulltext_measures.csv").set_index("paper_id")
        self.assertFalse(set(headline.index) & set(comp.index))
        for basis, group in ledger.groupby("basis"):
            hashes = group.pivot(
                index="paper_id", columns="reviewer", values="content_sha256"
            )
            self.assertTrue(hashes.jev.eq(hashes.qwen).all())
            if basis == "paper":
                self.assertTrue(
                    hashes.jev.eq(comp.loc[hashes.index, "text_sha256"]).all()
                )
        a, b = paper_tables()
        d = pd.concat([headline, comp], verify_integrity=True)
        for key, frame in [
            ("explicit", a[a.core & a.named]),
            ("other", a[a.core & ~a.named]),
            ("combined", a[a.core]),
            ("general", b),
        ]:
            sub = (
                frame.set_index("paper_id")[["N_h", "n_h"]]
                .join(d, how="inner")
                .dropna(subset=["text_sha256"])
            )
            record = result["domains"][key]
            self.assertEqual(len(sub), record["paired"])
            for reviewer in ["jev", "qwen"]:
                prefix = reviewer + "_paper_"
                w = sub[prefix + "weights"].ge(0.5)
                e = (
                    sub[[prefix + "supervision", prefix + "scaffolding"]]
                    .max(axis=1)
                    .ge(0.5)
                )
                weight = sub.N_h / sub.n_h
                est = record["ratings"][reviewer + "_paper"]
                self.assertEqual(
                    (w.sum(), e.sum()), (est["observed_W"], est["observed_E"])
                )
                self.assertAlmostEqual(weight[w].sum() / weight[e].sum(), est["ratio"])
                self.assertAlmostEqual(sum(est["shares"].values()), 1)
        for rev in ("jev", "qwen"):
            estimates = {
                k: v["ratings"][rev + "_paper"]["ratio"]
                for k, v in result["domains"].items()
            }
            for comparison in ("other", "general"):
                c = result["contrasts"][rev + "_explicit_over_" + comparison]
                self.assertTrue(
                    np.isclose(
                        c["ratio_of_ratios"],
                        estimates["explicit"] / estimates[comparison],
                    )
                )
                self.assertLessEqual(c["ci95"][0], c["ratio_of_ratios"])
                self.assertGreaterEqual(c["ci95"][1], c["ratio_of_ratios"])
        gap = pd.read_csv(out / "fulltext_coverage_cases.csv")
        self.assertEqual(set(gap.paper_id), set(coverage_draw().paper_id))
        self.assertFalse(set(d.index) & set(gap.paper_id))
        self.assertFalse(
            set(gap.paper_id)
            & set(
                pd.read_csv(out / "paper_master.csv.gz", usecols=["paper_id"]).paper_id
            )
        )
