"""Verify the paired independent frame, topic denominators and release joins."""

import json
import unittest

import pandas as pd

from attention import ROOT
from fulltext_sources import cohort


class ExternalComparisonTest(unittest.TestCase):
    def test_frame_and_blind_scores(self):
        out = ROOT / "results"
        frame = pd.read_csv(out / "external_radar_frame.csv").set_index(
            "paper_id", verify_integrity=True
        )
        ratings = pd.read_csv(out / "external_radar_ratings.csv.gz").set_index(
            "paper_id", verify_integrity=True
        )
        master = pd.read_csv(out / "paper_master.csv.gz", usecols=["paper_id"])
        self.assertEqual(set(frame.index), set(ratings.index))
        self.assertTrue(frame.index.str.startswith("arxiv:2610.").all())
        self.assertTrue((frame.in_master == frame.index.isin(master.paper_id)).all())
        check = json.loads((out / "external_radar_check.json").read_text())
        for topic in ["alignment_training", "control_monitoring"]:
            selected = frame[frame[topic] & ~frame.in_master]
            g = ratings.loc[selected.index]
            votes = [
                g[[rev + "_scaffolding", rev + "_supervision"]].ge(0.5).any(axis=1)
                for rev in ["jev", "qwen"]
            ]
            self.assertEqual(
                int((votes[0] & votes[1]).sum()),
                check["topics"][topic]["absent"]["both_reviewers"]["external"],
            )
        self.assertEqual(len(cohort("language-comparators")), 172)
        self.assertFalse(
            set(cohort().paper_id) & set(cohort("language-comparators").paper_id)
        )
