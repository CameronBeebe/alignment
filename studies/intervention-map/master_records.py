"""Identity, source text and cohort memberships for the study-wide paper table."""

import csv
import gzip
import json
from collections import defaultdict
from pathlib import Path
from snapshot import archive_path

ROOT = Path(__file__).resolve().parent


def rows(path):
    reader = gzip.open if str(path).endswith(".gz") else open
    with reader(ROOT / path, "rt", newline="") as stream:
        yield from csv.DictReader(stream)


def master_records():
    with gzip.open(archive_path(ROOT / "data"), "rt") as stream:
        records = {
            r["paper_id"]: (r["title"], r["abstract"]) for r in map(json.loads, stream)
        }
    roles = defaultdict(set)
    for pid in records:
        roles[pid].add("candidate")
    for r in rows("results/alignment_papers.csv"):
        roles[r["paper_id"]].add("alignment_shortlist")
    for source, id_key, role in [
        ("data/baseline_draw.csv", "arxiv_id", "general_ai_audit"),
        ("data/control_sample.csv.gz", "paper_id", "topic_sample"),
        ("data/matched_cscl.csv", "comparison_id", "matched_comparison"),
    ]:
        for r in rows(source):
            pid = ("arxiv:" if id_key == "arxiv_id" else "") + r[id_key]
            records.setdefault(pid, (r["title"], r["abstract"]))
            roles[pid].add(r["frame"] if role == "topic_sample" else role)
    return dict(sorted(records.items())), roles


def freeze_comparison_metadata(catalog):
    """Capture bibliographic fields omitted in the small probability draws."""
    import sqlite3

    records, roles = master_records()
    comparison = [pid for pid in records if "candidate" not in roles[pid]]
    with sqlite3.connect(catalog.resolve().as_uri() + "?mode=ro", uri=True) as db, (
        ROOT / "data/comparison_bibliography.csv"
    ).open("w", newline="") as dest:
        writer = csv.writer(dest, lineterminator="\n")
        writer.writerow(["paper_id", "authors", "doi", "venue", "month", "url"])
        for pid in comparison:
            result = db.execute(
                "SELECT authors,doi,venue,month,url FROM papers WHERE source=? AND id=?",
                pid.split(":", 1),
            ).fetchone()
            if result is None:
                raise ValueError(f"Missing comparison metadata for {pid}")
            writer.writerow([pid, *result])


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Freeze metadata for comparison-only works."
    )
    parser.add_argument("catalog", type=Path)
    freeze_comparison_metadata(parser.parse_args().catalog)
