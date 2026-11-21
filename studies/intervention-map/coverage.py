"""Optional exact-title coverage check against the original local catalog, with no new downloads."""

import argparse
import gzip
import json
import sqlite3
from pathlib import Path
import pandas as pd
from snapshot import archive_path
from search import folded


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", type=Path, default=Path("data"))
    ap.add_argument("--db", default="cache/catalog.sqlite")
    ap.add_argument("--out", type=Path, default=Path("results/venue_index_check.csv"))
    args = ap.parse_args()
    venue = pd.read_json(args.data / "l4dc_catalog.json")
    venue = venue.loc[~venue.title.str.fullmatch("Preface", case=False)].copy()
    lookup = {folded(t): [] for t in venue.title}
    with sqlite3.connect(f"file:{args.db}?mode=ro", uri=True) as db:
        for source, ident, title in db.execute("SELECT source,id,title FROM papers"):
            k = folded(title)
            if k in lookup:
                lookup[k].append(source + ":" + ident)
    with gzip.open(archive_path(args.data), "rt") as f:
        candidates = {
            folded(r["title"]) for p in map(json.loads, f) for r in p["records"]
        }
    venue["catalog_ids"] = venue.title.map(
        lambda t: " | ".join(sorted(lookup[folded(t)]))
    )
    venue["in_candidates"] = venue.title.map(lambda t: folded(t) in candidates)
    venue["safety_title"] = venue.title.str.contains(
        r"\bsafe\b|\bsafety\b|shield|barrier (?:function|certificate)|constraint satisfaction",
        case=False,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    venue.to_csv(args.out, index=False)
    s = venue.loc[venue.safety_title]
    print(
        "Safety titles:",
        len(s),
        "catalog matches:",
        s.catalog_ids.ne("").sum(),
        "retrieved:",
        s.in_candidates.sum(),
    )


if __name__ == "__main__":
    main()
