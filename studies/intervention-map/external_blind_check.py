"""Blind paired abstract measurements on the complete October Radar comparison."""

import argparse
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

from attention import ROOT
from fulltext_rate import rate, payload
from fulltext_sources import digest, local_name

OUT = ROOT / "results"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("catalog", type=Path)
    p.add_argument("cache", type=Path)
    p.add_argument("--workers", type=int, default=6)
    args = p.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)
    frame = pd.read_csv(OUT / "external_radar_frame.csv")
    tasks = []
    with sqlite3.connect(args.catalog.resolve().as_uri() + "?mode=ro", uri=True) as db:
        for pid in frame.paper_id:
            rec = db.execute(
                "SELECT title,abstract FROM papers WHERE source='arxiv' AND id=?",
                (pid.split(":")[1],),
            ).fetchone()
            if not rec or not rec[1]:
                raise ValueError(f"Missing catalog abstract for {pid}")
            for reviewer in ("jev", "qwen"):
                tasks.append((pid, rec[0], "abstract", rec[1], reviewer))
    with ThreadPoolExecutor(args.workers) as pool:
        futures = [pool.submit(rate, task, args.cache) for task in tasks]
        for f in as_completed(futures):
            f.result()
    by_id = {}
    for pid, title, basis, content, reviewer in tasks:
        signature = digest(
            json.dumps(
                payload(reviewer, title, basis, content),
                sort_keys=True,
                ensure_ascii=False,
            ).encode()
        )
        file = args.cache / f"{local_name(pid)}.{reviewer}.{basis}.{signature}.json"
        item = json.loads(file.read_text())
        if item["request_sha256"] != signature or item["content_sha256"] != digest(
            content.encode()
        ):
            raise ValueError("Provenance mismatch")
        row = by_id.setdefault(
            pid, {"paper_id": pid, "abstract_sha256": item["content_sha256"]}
        )
        for k, v in item["scores"].items():
            row[f"{reviewer}_{k}"] = float(v)
        row[f"{reviewer}_request_sha256"] = signature
        row[f"{reviewer}_model"] = item["model"]
        usage = item["usage"]
        row[f"{reviewer}_input_tokens"] = usage.get(
            "input_tokens", usage.get("prompt_tokens")
        )
        row[f"{reviewer}_output_tokens"] = usage.get(
            "output_tokens", usage.get("completion_tokens")
        )
        row[f"{reviewer}_usd"] = (
            usage.get("cost")
            if reviewer == "qwen"
            else usage["input_tokens"] * 0.042 / 1e6
        )
    pd.DataFrame(by_id.values()).to_csv(
        OUT / "external_radar_ratings.csv.gz",
        index=False,
        compression={"method": "gzip", "mtime": 0},
    )


if __name__ == "__main__":
    main()
