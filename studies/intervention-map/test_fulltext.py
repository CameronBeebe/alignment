"""Check that paired estimates use identical documents and keep the sampling design."""

import json
import unittest

import pandas as pd

from attention import ROOT, paper_tables
from fulltext_questions import QUESTIONS


class FullPaperTest(unittest.TestCase):
    def test_paired_inputs_and_results(self):
        out = ROOT / "results"
        data = pd.read_csv(out / "fulltext_measures.csv").set_index(
            "paper_id", verify_integrity=True
        )
        ledger = pd.read_csv(out / "fulltext_requests.csv")
        report = json.loads((out / "fulltext_summary.json").read_text())
        design, _ = paper_tables()
        scope = pd.read_csv(out / "language_model_scores.csv.gz").set_index("paper_id")
        selected = design[
            design.core
            & design.named
            & design.paper_id.map(scope.jev_language_model_focus).ge(0.5)
        ]
        self.assertEqual(set(data.index), set(selected.paper_id))
        self.assertEqual(len(QUESTIONS), 67)
        self.assertEqual(report["paired"], data.text_sha256.notna().sum())
        self.assertFalse(ledger.duplicated(["paper_id", "basis", "reviewer"]).any())
        for basis in ("abstract", "paper"):
            both = ledger[ledger.basis == basis].pivot(
                index="paper_id", columns="reviewer", values="content_sha256"
            )
            self.assertTrue(both.jev.eq(both.qwen).all())
            if basis == "paper":
                self.assertTrue(both.jev.eq(data.loc[both.index, "text_sha256"]).all())
            for k in QUESTIONS:
                self.assertTrue(
                    data.loc[both.index, f"jev_{basis}_{k}"].between(0, 1).all()
                )
        paired = data[data.text_sha256.notna()].join(
            selected.set_index("paper_id")[["N_h", "n_h"]]
        )
        for reviewer in ("jev", "qwen"):
            for basis in ("abstract", "paper"):
                prefix = f"{reviewer}_{basis}_"
                w = paired[prefix + "weights"].ge(0.5)
                e = (
                    paired[[prefix + "scaffolding", prefix + "supervision"]]
                    .ge(0.5)
                    .any(axis=1)
                )
                weight = paired.N_h / paired.n_h
                r = report["ratios"][f"{reviewer}_{basis}"]
                self.assertEqual((r["observed_W"], r["observed_E"]), (w.sum(), e.sum()))
                self.assertAlmostEqual(r["ratio"], weight[w].sum() / weight[e].sum())
