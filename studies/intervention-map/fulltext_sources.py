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

# These PDF editions share the catalog IDs and author lists.
PDF_TITLES = {
    "arxiv:2409.17458": "Red Queen: Exposing Latent Multi-Turn Risks in Large Language Models",
    "acl:2026.emnlp-main.688": "Ideation Arena: Evaluating LLM Generated Research Ideas with Battle-style Human Expert Assessment",
}


def cohort(selection="headline"):
    if selection == "language-comparators":
        return language_comparators()
    if selection != "headline":
        raise ValueError("Unknown cohort")

    a, _ = paper_tables()
    scope = (
        pd.read_csv(ROOT / "results/language_model_scores.csv.gz")
        .set_index("paper_id")
        .jev_language_model_focus
    )
    return a[a.core & a.named & a.paper_id.map(scope).ge(0.5)].sort_values("paper_id")


def language_comparators():
    """All remaining language-model core audit papers plus the language-model baseline."""
    master = pd.read_csv(ROOT / "results/paper_master.csv.gz", keep_default_na=False)
    selected = master.jev_language_model_focus.ge(0.5)
    core = master.alignment_review_scope.eq("core")
    general = master.cohorts.str.split("|", regex=False).map(
        lambda tags: "general_ai_audit" in tags
    )
    completed = pd.read_csv(ROOT / "results/fulltext_measures.csv")
    remaining = selected & (core | general) & ~master.paper_id.isin(completed.paper_id)
    return master.loc[remaining, ["paper_id", "title"]].sort_values("paper_id")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def local_name(pid):
    return pid.replace(":", "_")


def extract_pdf(resp, url, pid, catalog_title, body):
    with pymupdf.open(stream=resp.content, filetype="pdf") as pdf:
        pages = [p.get_text("text", sort=True).strip() for p in pdf]
        title_page_text = " ".join(
            page.get_text("text") for page in (pdf[j] for j in range(min(2, len(pdf))))
        )
    text = "\n\n".join(f"[Page {i}]\n{s}" for i, s in enumerate(pages, 1))
    normalize = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())
    first = normalize(" ".join(pages[:2]) + " " + title_page_text)
    title = normalize(PDF_TITLES.get(pid, catalog_title))

    # Require either the title or a near-identical run of title characters.
    matched = (
        SequenceMatcher(None, title, first, autojunk=False).find_longest_match().size
    )
    if len(text) < 2000 or matched < min(len(title) * 0.45, 35):
        raise ValueError("Insufficient text or unverified title")
    content = text.encode()
    temporary = body.with_suffix(".part")
    temporary.write_bytes(content)
    temporary.replace(body)
    record = dict(
        paper_id=pid,
        url=url,
        final_url=resp.url,
        pdf_sha256=digest(resp.content),
        text_sha256=digest(content),
        pages=len(pages),
        characters=len(text),
        pages_under_40_chars=sum(len(s) < 40 for s in pages),
        extractor="PyMuPDF " + pymupdf.VersionBind,
        verified_title=PDF_TITLES.get(pid, catalog_title),
    )
    return record


def retrieve(folder, only=None, selection="headline", rows=None):
    folder.mkdir(parents=True, exist_ok=True)
    # The headline archive includes a withdrawal whose originally posted v1 was audited.
    versions = {
        "arxiv:2608.01629": "https://arxiv.org/pdf/2608.01629v1",
        "arxiv:2509.01412": "https://arxiv.org/pdf/2509.01412v1",
    }
    for filename in [
        "fulltext_measures.csv",
        "fulltext_comparator_measures.csv",
        "fulltext_coverage_cases.csv",
    ]:
        release = ROOT / "results" / filename
        if release.exists():
            with release.open(newline="") as f:
                for row in csv.DictReader(f):
                    source = row.get("source_url", "")
                    if source.startswith(
                        "https://pdfs.assets.alphaxiv.org/"
                    ) or re.search(r"v\d+$", source):
                        versions[row["paper_id"]] = source
                    elif row.get("versioned_pdf_url"):
                        versions[row["paper_id"]] = row["versioned_pdf_url"]
    selected = cohort(selection) if rows is None else rows
    for row in selected.itertuples():
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
                record = extract_pdf(resp, url, pid, row.title, body)
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
    p.add_argument(
        "--cohort", choices=["headline", "language-comparators"], default="headline"
    )
    args = p.parse_args()
    retrieve(args.cache, args.only, args.cohort)
