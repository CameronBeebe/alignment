import unittest

import numpy as np
import pandas as pd

from estimate import ratio_stats, variance
from rules import screen
from search import merge


class StudyChecks(unittest.TestCase):
    def test_aliases_link_without_requiring_title_equality(self):
        arxiv = dict(
            source="arxiv",
            id="2401.00001",
            title="A working title",
            month="2024-01",
            url="arxiv",
            doi="10.1234/demo",
            venue="cs.AI",
            abstract="abstract",
        )
        acl = dict(
            arxiv,
            source="acl",
            id="published",
            title="A different published title",
            month="2024-07",
            url="acl",
        )
        pool = {
            ("arxiv", arxiv["id"]): (arxiv, {"goal"}),
            ("acl", acl["id"]): (acl, {"system"}),
        }
        (paper,) = merge(pool)
        self.assertEqual(paper["month"], "2024-01")
        self.assertEqual(paper["lanes"], ["goal", "system"])
        self.assertEqual(len(paper["records"]), 2)

    def test_independent_retrieval_lanes(self):
        self.assertIn(
            "system",
            screen(
                "Tool permissions for LLM agents", "Runtime enforcement for tool calls."
            ),
        )
        self.assertIn(
            "training",
            screen(
                "Using human feedback",
                "Direct preference optimization of a language model.",
            ),
        )
        self.assertEqual(
            screen("Beam alignment in mobile radio", "Signal recovery at the antenna."),
            [],
        )

    def test_paired_stratified_variance_and_hybrid_credit(self):
        design = pd.DataFrame(
            dict(
                stratum=["a"] * 3 + ["b"] * 4,
                N_h=[30] * 3 + [10] * 4,
                n_h=[3] * 3 + [4] * 4,
            )
        )
        w = np.array([1, 1, 0, 1, 0, 0, 0], float)
        e = np.array([0, 1, 0, 1, 1, 0, 0], float)
        report = ratio_stats(design, w, e)
        self.assertEqual((report["W"], report["E"], report["ratio"]), (22.5, 15, 1.5))
        expected = (
            30**2 * 0.9 * np.var((w - e)[:3], ddof=1) / 3
            + 10**2 * 0.6 * np.var((w - e)[3:], ddof=1) / 4
        )
        self.assertAlmostEqual(variance(design, w - e)[0], expected)


if __name__ == "__main__":
    unittest.main()
