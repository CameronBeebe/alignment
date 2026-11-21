"""Retrieve and fingerprint the complete PDF text for the frozen headline cohort."""

import argparse
import csv
import hashlib
import json
import re
import time
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd
import pymupdf
import requests

from attention import ROOT, paper_tables

# The proceedings PDF and frozen catalog share the ACL ID and author list.
PDF_TITLES = {
    "acl:2026.emnlp-main.688": "Ideation Arena: Evaluating LLM Generated Research Ideas with Battle-style Human Expert Assessment",
}


def cohort():
    a, _ = paper_tables()
    scope = (
        pd.read_csv(ROOT / "results/language_model_scores.csv.gz")
        .set_index("paper_id")
        .jev_language_model_focus
    )
    return a[a.core & a.named & a.paper_id.map(scope).ge(0.5)].sort_values("paper_id")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def local_name(pid):
    return pid.replace(":", "_")


def retrieve(folder, only=None):
    folder.mkdir(parents=True, exist_ok=True)
    release = ROOT / "results/fulltext_measures.csv"
    # This paper's current arXiv record is a withdrawal notice. The original
    # article was public during the study window and is still available as v1.
    versions = {"arxiv:2608.01629": "https://arxiv.org/pdf/2608.01629v1"}
    if release.exists():
        with release.open(newline="") as f:
            versions.update(
                {
                    r["paper_id"]: r["versioned_pdf_url"]
                    for r in csv.DictReader(f)
                    if r.get("versioned_pdf_url")
                }
            )
    for row in cohort().itertuples():
        pid = row.paper_id
        if only and pid != only:
            continue
        key = local_name(pid)
        meta = folder / (key + ".json")
        body = folder / (key + ".txt")
        if meta.exists() and body.exists():
            if digest(body.read_bytes()) == json.loads(meta.read_text()).get(
                "text_sha256"
            ):
                continue
        source, ident = pid.split(":", 1)
        url = (
            f"https://arxiv.org/pdf/{ident}"
            if source == "arxiv"
            else f"https://aclanthology.org/{ident}.pdf"
        )
        url = versions.get(pid, url)
        for attempt in range(3):
            try:
                resp = requests.get(url, timeout=(10, 45))
                resp.raise_for_status()
                with pymupdf.open(stream=resp.content, filetype="pdf") as pdf:
                    pages = [p.get_text("text", sort=True).strip() for p in pdf]
                text = "\n\n".join(f"[Page {i}]\n{s}" for i, s in enumerate(pages, 1))
                normalize = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())
                first = normalize(" ".join(pages[:2]))
                title = normalize(PDF_TITLES.get(pid, row.title))

                # Require either the title or a near-identical run of title characters.
                matched = (
                    SequenceMatcher(None, title, first, autojunk=False)
                    .find_longest_match()
                    .size
                )
                if len(text) < 2000 or matched < min(len(title) * 0.45, 35):
                    raise ValueError("Insufficient text or unverified title")
                body.write_bytes(text.encode())
                record = dict(
                    paper_id=pid,
                    url=url,
                    final_url=resp.url,
                    pdf_sha256=digest(resp.content),
                    text_sha256=digest(body.read_bytes()),
                    pages=len(pages),
                    characters=len(text),
                    pages_under_40_chars=sum(len(s) < 40 for s in pages),
                    extractor="PyMuPDF " + pymupdf.VersionBind,
                    verified_title=PDF_TITLES.get(pid, row.title),
                )
                break
            except (requests.RequestException, ValueError, pymupdf.FileDataError) as e:
                record = dict(paper_id=pid, url=url, error=str(e)[:240])
                if attempt < 2:
                    time.sleep(3 * (attempt + 1))
        meta.write_text(json.dumps(record) + "\n")
        print(pid, record.get("pages", record.get("error")), flush=True)
        if source == "arxiv":
            time.sleep(3)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("cache", type=Path)
    p.add_argument("--only")
    args = p.parse_args()
    retrieve(args.cache, args.only)
