"""Measure author vocabulary each year in the seven-category arXiv frame."""

import csv
import re
import sqlite3
import sys
from collections import Counter
from baseline import CATEGORIES, ROOT


def main(path):
    counts = Counter()
    with sqlite3.connect(path) as con:
        for date, venue in con.execute(
            "SELECT month,venue FROM papers WHERE source='arxiv' AND month BETWEEN '2021-11' AND '2026-10'"
        ):
            if venue.split()[0] in CATEGORIES:
                counts[date[:4], "papers"] += 1
        for name, query, pattern in [
            ("harness", "harness OR harnesses", r"\bharness(?:es)?\b"),
            (
                "scaffold",
                "scaffold OR scaffolds OR scaffolding",
                r"\bscaffold(?:s|ing)?\b",
            ),
            ("cybernetics", "cybernetics OR cybernetic", r"\bcybernetic(?:s)?\b"),
            ("closed_loop", '"closed loop"', r"\bclosed[\s-]+loop\b"),
        ]:
            rx = re.compile(pattern, re.I)
            sql = """SELECT p.month,p.venue,p.title,p.abstract FROM ft JOIN papers p ON ft.rowid=p.rowid
                   WHERE ft MATCH ? AND source='arxiv' AND month BETWEEN '2021-11' AND '2026-10'"""
            for date, venue, title, abstract in con.execute(sql, (query,)):
                if venue.split()[0] in CATEGORIES and rx.search(title + " " + abstract):
                    counts[date[:4], name] += 1
    with (ROOT / "results/vocabulary_by_year.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            ["year", "papers", "harness", "scaffold", "cybernetics", "closed_loop"]
        )
        for year in range(2021, 2027):
            w.writerow(
                [year]
                + [
                    counts[str(year), k]
                    for k in (
                        "papers",
                        "harness",
                        "scaffold",
                        "cybernetics",
                        "closed_loop",
                    )
                ]
            )


if __name__ == "__main__":
    main(sys.argv[1])
