"""Regression checks for the language-model carve-out on the released data."""

import json
import unittest

import pandas as pd

from language_scope import ROOT


class LanguageScopeTest(unittest.TestCase):
    def test_catalog_is_exactly_the_model_scope_slice(self):
        results = ROOT / "results"
        master = pd.read_csv(
            results / "paper_master.csv.gz",
            usecols=["paper_id", "jev_language_model_focus"],
        ).set_index("paper_id", verify_integrity=True)
        scope = pd.read_csv(
            results / "language_model_scores.csv.gz",
            usecols=["paper_id", "jev_language_model_focus"],
        ).set_index("paper_id", verify_integrity=True)
        pd.testing.assert_frame_equal(master, scope)
        catalog = pd.read_csv(
            results / "language_model_papers.csv.gz", usecols=["paper_id"]
        )
        self.assertEqual(
            catalog.paper_id.tolist(),
            master.index[master.jev_language_model_focus >= 0.5].tolist(),
        )

    def test_audit_domains_partition_and_preserve_full_estimates(self):
        results = ROOT / "results"
        data = json.loads((results / "language_comparison.json").read_text())
        for definition in [
            "semantic_050",
            "semantic_030",
            "semantic_070",
            "literal",
            "literal_or_family",
            "all",
        ]:
            frames = data[definition]["frames"]
            core, explicit, other = [
                frames[name] for name in ("core", "explicit", "other_wording")
            ]
            self.assertEqual(
                core["selected_n"], explicit["selected_n"] + other["selected_n"]
            )
            for method in ("rubric", "jev"):
                for count in ("observed_W", "observed_E", "W", "E"):
                    self.assertAlmostEqual(
                        core[method][count],
                        explicit[method][count] + other[method][count],
                    )
        original = json.loads((results / "attention.json").read_text())
        jev = json.loads((results / "jev_validation.json").read_text())["mechanisms"]
        for key in ["core", "explicit", "general_ai"]:
            for method, target in [
                ("rubric", original[key]["full"]["W_either"]),
                ("jev", jev[key]["weight_to_external"]["0.5"]),
            ]:
                self.assertAlmostEqual(
                    data["all"]["frames"][key][method]["ratio"], target["ratio"]
                )
                self.assertEqual(
                    data["all"]["frames"][key][method]["ci95"], target["ci95"]
                )
