"""Draw two independent-of-wording comparison samples for the cybernetics hypothesis."""

import argparse
import csv
import gzip
import hashlib
import sqlite3
from pathlib import Path

from baseline import CATEGORIES

ROOT = Path(__file__).resolve().parent
DESIGN = {"general_ai": 800, "control_and_optimization": 400}
CONTROL_CATEGORIES = {"cs.SY", "eess.SY", "math.OC"}


def draw(database):
    pools = {name: [] for name in DESIGN}
    with sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True) as con:
        for pid, cats in con.execute(
            """SELECT id,venue FROM papers WHERE source='arxiv'
                                       AND month BETWEEN '2021-11' AND '2026-10'"""
        ):
            cat = cats.split()[0]
            if cat in CATEGORIES:
                group = "general_ai"
            elif cat in CONTROL_CATEGORIES:
                group = "control_and_optimization"
            else:
                continue
            rank = hashlib.sha256(("cybernetics-map-2026-v1/" + pid).encode()).digest()
            pools[group].append((rank, pid))
        with gzip.open(ROOT / "data/control_sample.csv.gz", "wt", newline="") as f:
            out = csv.writer(f)
            out.writerow(
                [
                    "paper_id",
                    "frame",
                    "population",
                    "category",
                    "year",
                    "title",
                    "abstract",
                ]
            )
            for group, k in DESIGN.items():
                for _, pid in sorted(pools[group])[:k]:
                    cat, month, title, abstract = con.execute(
                        "SELECT venue,month,title,abstract FROM papers WHERE source='arxiv' AND id=?",
                        (pid,),
                    ).fetchone()
                    out.writerow(
                        [
                            "arxiv:" + pid,
                            group,
                            len(pools[group]),
                            cat.split()[0],
                            month[:4],
                            title,
                            abstract,
                        ]
                    )


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("database", type=Path)
    draw(ap.parse_args().database)
