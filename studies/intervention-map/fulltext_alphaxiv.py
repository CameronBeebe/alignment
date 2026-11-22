"""Retrieve versioned PDF links published on alphaXiv for the coverage and language audits."""

import argparse
import hashlib
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

from fulltext_sources import ROOT, cohort, digest, extract_pdf, local_name, retrieve


def coverage_draw():
    frame = pd.read_csv(ROOT / "results/external_radar_frame.csv")
    missing = frame[frame.control_monitoring & ~frame.in_master].copy()
    missing["draw_order"] = missing.paper_id.map(
        lambda p: hashlib.sha256(("radar-full-paper-check-v1/" + p).encode()).digest()
    )
    drawn = (
        missing.sort_values("draw_order")
        .head(10)[["paper_id", "title"]]
        .assign(selection="radar_hash_draw")
    )
    examples = pd.DataFrame(
        [
            (
                "arxiv:2610.20780",
                "ARIA: Runtime Inspection and Amendment for Multi-Agent Systems",
                "alphaxiv_case",
            ),
            (
                "arxiv:2607.06273",
                "AgentTether: Graph-Guided Diagnosis and Runtime Intervention for Reliable LLM Agent Operation",
                "alphaxiv_case",
            ),
        ],
        columns=drawn.columns,
    )
    return pd.concat([drawn, examples], ignore_index=True)


def fetch(row, folder):
    pid = row.paper_id
    ident = pid.removeprefix("arxiv:")
    name = local_name(pid)
    meta = folder / (name + ".json")
    body = folder / (name + ".txt")
    if (
        meta.exists()
        and body.exists()
        and digest(body.read_bytes()) == json.loads(meta.read_text()).get("text_sha256")
    ):
        return
    url = "https://www.alphaxiv.org/abs/" + ident
    page = requests.get(url, timeout=(12, 30))
    page.raise_for_status()
    soup = BeautifulSoup(page.content, "html.parser")
    pattern = re.compile(
        r"https://pdfs\.assets\.alphaxiv\.org/" + re.escape(ident) + r"v\d+\.pdf"
    )
    link = next(
        (a["href"] for a in soup.select("a[href]") if pattern.fullmatch(a["href"])),
        None,
    )
    if not link:
        raise ValueError("No versioned PDF link")
    response = requests.get(link, timeout=(12, 60))
    response.raise_for_status()
    record = extract_pdf(response, link, pid, row.title, body)
    record["listing_url"] = url
    tmp = meta.with_suffix(".part.json")
    tmp.write_text(json.dumps(record) + "\n")
    tmp.replace(meta)
    print(pid, record["pages"], flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("cache", type=Path)
    p.add_argument(
        "--cohort", choices=["coverage", "language-comparators"], default="coverage"
    )
    p.add_argument("--workers", type=int, default=2)
    p.add_argument("--origin", choices=["alphaxiv", "arxiv"], default="alphaxiv")
    p.add_argument("--last", type=int, help="Use the last N arXiv IDs in sorted order")
    args = p.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)
    rows = coverage_draw() if args.cohort == "coverage" else cohort(args.cohort)
    rows = rows[rows.paper_id.str.startswith("arxiv:")].sort_values(
        "paper_id", ascending=False
    )
    if args.last is not None:
        rows = rows.head(args.last)

    if args.origin == "arxiv":
        retrieve(args.cache, rows=rows)
        return

    def collect(row):
        for attempt in range(2):
            try:
                fetch(row, args.cache)
                return
            except (requests.RequestException, ValueError, RuntimeError) as e:
                if attempt:
                    print(row.paper_id, type(e).__name__, str(e)[:160], flush=True)
                    return row.paper_id
                else:
                    time.sleep(2)

    with ThreadPoolExecutor(args.workers) as executor:
        missing = [pid for pid in executor.map(collect, rows.itertuples()) if pid]
    if missing:
        raise SystemExit(f"{len(missing)} PDF(s) unavailable from alphaXiv. Retry with --origin arxiv.")


if __name__ == "__main__":
    main()
