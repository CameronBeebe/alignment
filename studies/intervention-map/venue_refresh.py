"""Optional refresh of the five L4DC volume tables from the publisher's bulk bibliography."""

import argparse
import json
from pathlib import Path
import re
from urllib.request import urlopen

VOLUMES = {168: 2022, 211: 2023, 242: 2024, 283: 2025, 331: 2026}


def parse(bib, volume, year):
    fields = re.compile(
        r"^\s*([a-zA-Z]+)\s*=\s*(.*?)(?=,\s*\n\s*\w+\s*=|\s*\n\s*\}\s*$)", re.M | re.S
    )
    rows = []
    for block in re.split(r"(?im)^@inproceedings\s*\{", bib)[1:]:
        p = {
            k.lower(): " ".join(v.strip().strip(",").strip().strip('{}"').split())
            for k, v in fields.findall(block)
        }
        if not {"pages", "title", "author"} <= p.keys():
            continue
        rows.append(
            dict(
                volume=volume,
                year=year,
                pages=p["pages"].replace("--", "-"),
                title=p["title"].replace("{", "").replace("}", ""),
                authors=p["author"],
                source=f"https://proceedings.mlr.press/v{volume}/",
            )
        )
    if not rows:
        raise ValueError(f"No bibliographic records for volume {volume}")
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--out", type=Path, required=True, help="Destination for a new snapshot"
    )
    args = ap.parse_args()
    rows = []
    for volume, year in VOLUMES.items():
        url = f"https://proceedings.mlr.press/v{volume}/assets/bib/bibliography.bib"
        with urlopen(url, timeout=90) as r:
            rows.extend(parse(r.read().decode(), volume, year))
    args.out.write_text(json.dumps(rows, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
